import asyncio
import logging
import math
import uuid
from pathlib import Path
from typing import Optional

import discord
from discord.ext import commands

from core.soundboard.validator import (
    MAX_DURATION_SECONDS,
    MAX_FILE_SIZE,
    probe_audio,
    validate_attachment_size,
    validate_sound_name,
)
from database.crud import (
    add_sound,
    get_all_sounds,
    get_sound,
    increment_sound_times_played,
)

logger = logging.getLogger(__name__)

SOUNDBOARD_DIR = Path(__file__).resolve().parents[1] / "assets" / "soundboard_files"
DEFAULT_ERROR_MESSAGE = "⚠️ An unexpected error occurred while processing your request. Please try again later."
VC_INACTIVITY_TIMEOUT = 180  # Disconnect after 3 minutes of idle inactivity


class SoundboardCog(commands.Cog, name="Soundboard"):
    """Soundboard system for uploading and playing audio clips in voice channels."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._disconnect_tasks: dict[int, asyncio.Task] = {}  # guild_id -> task
        SOUNDBOARD_DIR.mkdir(parents=True, exist_ok=True)

    def cog_unload(self):
        for task in self._disconnect_tasks.values():
            task.cancel()

    def _cancel_disconnect_timer(self, guild_id: int):
        task = self._disconnect_tasks.pop(guild_id, None)
        if task and not task.done():
            task.cancel()

    def _start_disconnect_timer(self, guild: discord.Guild):
        self._cancel_disconnect_timer(guild.id)

        async def _disconnect_later():
            try:
                await asyncio.sleep(VC_INACTIVITY_TIMEOUT)
                voice_client = guild.voice_client
                if voice_client and voice_client.is_connected() and not voice_client.is_playing():
                    await voice_client.disconnect()
                    logger.info(f"Disconnected from voice in guild {guild.id} due to inactivity.")
            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"Error in voice disconnect timer: {e}", exc_info=True)

        # Safely schedule the coroutine onto the bot's event loop from the audio thread
        self._disconnect_tasks[guild.id] = asyncio.run_coroutine_threadsafe(
            _disconnect_later(), self.bot.loop
        )

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Automatically disconnect if all other members leave the voice channel."""
        try:
            guild = member.guild
            voice_client: Optional[discord.VoiceClient] = guild.voice_client
            if not voice_client or not voice_client.channel:
                return

            # If the bot is the only member left in the voice channel, disconnect immediately
            non_bot_members = [m for m in voice_client.channel.members if not m.bot]
            if len(non_bot_members) == 0:
                self._cancel_disconnect_timer(guild.id)
                await voice_client.disconnect()
                logger.info(f"Disconnected from empty voice channel {voice_client.channel.name} in guild {guild.id}.")
        except Exception as e:
            logger.error(f"Error handling voice state update in soundboard cog: {e}", exc_info=True)

    async def _play_sound_helper(self, ctx: commands.Context, sound_name: str):
        """Internal helper to connect to VC and play a sound."""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("⚠️ You must be connected to a voice channel to play a sound!")
            return

        sound = await get_sound(sound_name)
        if not sound:
            await ctx.send(f"⚠️ Sound `{sound_name}` not found. Use `+sb list` to view available sounds.")
            return

        sound_path = SOUNDBOARD_DIR / sound.local_file_name
        if not sound_path.exists():
            logger.error(f"Sound file missing on disk: {sound_path} for sound '{sound.name}'")
            await ctx.send("⚠️ Audio file is missing from local storage. Please notify an administrator.")
            return

        target_channel = ctx.author.voice.channel
        voice_client: Optional[discord.VoiceClient] = ctx.voice_client

        try:
            if not voice_client or not voice_client.is_connected():
                voice_client = await target_channel.connect(timeout=10.0)
            elif voice_client.channel != target_channel:
                await voice_client.move_to(target_channel)
        except discord.Forbidden:
            await ctx.send("⚠️ Bot lacks permission to join or speak in that voice channel.")
            return
        except asyncio.TimeoutError:
            await ctx.send("⚠️ Failed to connect to the voice channel (connection timed out).")
            return
        except Exception as e:
            logger.error(f"Error connecting to voice channel: {e}", exc_info=True)
            await ctx.send(DEFAULT_ERROR_MESSAGE)
            return

        if voice_client.is_playing():
            await ctx.send("⚠️ Another sound is currently playing. Please wait a moment.")
            return

        self._cancel_disconnect_timer(ctx.guild.id)

        def after_playing(error):
            if error:
                logger.error(f"Error during audio playback for '{sound.name}': {error}", exc_info=error)
            self._start_disconnect_timer(ctx.guild)

        try:
            audio_source = discord.FFmpegPCMAudio(str(sound_path))
            voice_client.play(audio_source, after=after_playing)
            await increment_sound_times_played(sound.id)

            try:
                await ctx.message.add_reaction("🔊")
            except Exception:
                await ctx.send(f"🔊 Playing **{sound.name}**")
        except Exception as e:
            logger.error(f"Failed to play audio source '{sound_path}': {e}", exc_info=True)
            self._start_disconnect_timer(ctx.guild)
            await ctx.send(DEFAULT_ERROR_MESSAGE)

    @commands.group(name="soundboard", aliases=["sb"], invoke_without_command=True)
    async def soundboard(self, ctx: commands.Context, *, sound_name: Optional[str] = None):
        """Soundboard commands: +sb <name> to play, or +sb add/list."""
        if sound_name:
            await self._play_sound_helper(ctx, sound_name)
        else:
            embed = discord.Embed(
                title="🔊 Soundboard System",
                description="Play fun audio clips directly in your voice channel!",
                color=discord.Color.blue(),
            )
            embed.add_field(name="Play a sound", value="`+sb <name>` or `+sb play <name>`", inline=False)
            embed.add_field(name="Add a sound", value="`+sb add <name>` *(attach audio file, max 6s, max 5MB)*", inline=False)
            embed.add_field(name="List sounds", value="`+sb list [page]`", inline=False)
            embed.add_field(name="Sound details", value="`+sb info <name>`", inline=False)
            await ctx.send(embed=embed)

    @soundboard.command(name="play", description="Play a sound in your current voice channel.")
    async def play(self, ctx: commands.Context, name: str):
        """Explicit command to play a sound: +sb play <name>"""
        await self._play_sound_helper(ctx, name)

    @soundboard.command(name="add", description="Add a new sound file (attach audio, max 6s, max 5MB).")
    async def add(self, ctx: commands.Context, name: str):
        """Upload a new sound clip with a custom name."""
        try:
            # 1. Validate sound name format
            is_valid_name, err = validate_sound_name(name)
            if not is_valid_name:
                await ctx.send(f"⚠️ {err}")
                return

            clean_name = name.strip().lower()

            # 2. Check if name is already taken in the database
            existing_sound = await get_sound(clean_name)
            if existing_sound:
                await ctx.send(f"⚠️ A sound with the name `{clean_name}` already exists. Please choose a different name.")
                return

            # 3. Check for attachment
            if not ctx.message.attachments:
                await ctx.send("⚠️ Please attach an audio file to your message when running this command.")
                return

            attachment = ctx.message.attachments[0]

            # 4. Check attachment size
            is_valid_size, size_err = validate_attachment_size(attachment.size)
            if not is_valid_size:
                await ctx.send(f"⚠️ {size_err}")
                return

            # Determine file extension
            original_ext = Path(attachment.filename).suffix.lower()
            if not original_ext:
                original_ext = ".mp3"

            # 5. Download attachment to temporary file for validation
            temp_filename = f"_temp_{uuid.uuid4().hex}_{attachment.filename}"
            temp_path = SOUNDBOARD_DIR / temp_filename

            try:
                await attachment.save(temp_path)
            except Exception as e:
                logger.error(f"Failed to save attachment to {temp_path}: {e}", exc_info=True)
                await ctx.send("⚠️ Failed to download the attachment. Please try again.")
                return

            # 6. Probe audio for playable format & duration <= 6.0s
            is_valid_audio, duration, probe_err = await probe_audio(temp_path)
            if not is_valid_audio:
                if temp_path.exists():
                    temp_path.unlink()
                await ctx.send(f"⚠️ {probe_err}")
                return

            # 7. Move temporary file to permanent location
            permanent_filename = f"{uuid.uuid4().hex[:12]}_{clean_name}{original_ext}"
            permanent_path = SOUNDBOARD_DIR / permanent_filename

            try:
                temp_path.replace(permanent_path)
            except Exception as e:
                logger.error(f"Failed to move temp sound file to {permanent_path}: {e}", exc_info=True)
                if temp_path.exists():
                    temp_path.unlink()
                await ctx.send("⚠️ Failed to store the sound file on the server. Please try again.")
                return

            # 8. Insert into Database
            try:
                sound_record = await add_sound(
                    name=clean_name,
                    uploader=ctx.author.id,
                    uploader_name=ctx.author.display_name,
                    local_file_name=permanent_filename,
                    duration=duration,
                    file_size=attachment.size,
                )
            except Exception as e:
                logger.error(f"Database error saving sound record: {e}", exc_info=True)
                if permanent_path.exists():
                    permanent_path.unlink()
                await ctx.send("⚠️ Database error occurred while saving the sound. Please try again.")
                return

            # 9. Success Embed
            embed = discord.Embed(
                title="✅ Sound Added Successfully!",
                description=f"Sound `{sound_record.name}` is now available on the soundboard.",
                color=discord.Color.green(),
            )
            embed.add_field(name="Trigger Command", value=f"`+sb {sound_record.name}`", inline=True)
            embed.add_field(name="Duration", value=f"{sound_record.duration:.2f}s", inline=True)
            embed.add_field(name="Uploader", value=ctx.author.display_name, inline=True)
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Unexpected error in soundboard add command: {e}", exc_info=True)
            await ctx.send(DEFAULT_ERROR_MESSAGE)

    @soundboard.command(name="list", aliases=["all"], description="List all available sounds on the soundboard.")
    async def list_sounds(self, ctx: commands.Context, page: int = 1):
        """List sounds with pagination."""
        try:
            PAGE_SIZE = 10
            page = max(1, page)
            sounds, total_count = await get_all_sounds(page=page, page_size=PAGE_SIZE)

            if total_count == 0:
                await ctx.send("The soundboard is currently empty! Use `+sb add <name>` with an attached audio file to add one.")
                return

            total_pages = max(1, math.ceil(total_count / PAGE_SIZE))
            if page > total_pages:
                await ctx.send(f"⚠️ Page {page} does not exist. Total pages: {total_pages}.")
                return

            embed = discord.Embed(
                title="🔊 Soundboard Library",
                description=f"Use `+sb <name>` in any text channel while connected to voice to play a sound.\nTotal sounds: **{total_count}**",
                color=discord.Color.blue(),
            )

            for s in sounds:
                embed.add_field(
                    name=f"🎵 {s.name}",
                    value=f"⏱️ `{s.duration:.2f}s` | 🎧 Played `{s.times_played}` times | By `{s.uploader_name}`",
                    inline=False,
                )

            embed.set_footer(text=f"Page {page} of {total_pages} • Use +sb list <page> to view more")
            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in soundboard list command: {e}", exc_info=True)
            await ctx.send(DEFAULT_ERROR_MESSAGE)

    @soundboard.command(name="info", description="Get detailed info about a specific sound.")
    async def info(self, ctx: commands.Context, name: str):
        """View sound details: uploader, duration, plays, date added."""
        try:
            sound = await get_sound(name)
            if not sound:
                await ctx.send(f"⚠️ Sound `{name}` was not found.")
                return

            size_kb = sound.file_size / 1024
            date_str = sound.created_at.strftime("%Y-%m-%d %H:%M UTC") if sound.created_at else "Unknown"

            embed = discord.Embed(
                title=f"🔊 Sound: {sound.name}",
                color=discord.Color.gold(),
            )
            embed.add_field(name="Play Command", value=f"`+sb {sound.name}`", inline=True)
            embed.add_field(name="Duration", value=f"{sound.duration:.2f}s", inline=True)
            embed.add_field(name="Times Played", value=f"{sound.times_played}", inline=True)
            embed.add_field(name="Uploader", value=sound.uploader_name, inline=True)
            embed.add_field(name="File Size", value=f"{size_kb:.1f} KB", inline=True)
            embed.add_field(name="Added On", value=date_str, inline=True)

            await ctx.send(embed=embed)

        except Exception as e:
            logger.error(f"Error in soundboard info command: {e}", exc_info=True)
            await ctx.send(DEFAULT_ERROR_MESSAGE)

    @commands.command(name="sound", aliases=["sbplay"], description="Play a sound clip by name.")
    async def sound_shortcut(self, ctx: commands.Context, name: str):
        """Direct shortcut command: +sound <name>"""
        await self._play_sound_helper(ctx, name)


async def setup(bot: commands.Bot):
    await bot.add_cog(SoundboardCog(bot))

