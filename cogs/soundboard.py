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
from core.soundboard.formatter import ITEMS_PER_PAGE, build_soundboard_embed

logger = logging.getLogger(__name__)

SOUNDBOARD_DIR = Path(__file__).resolve().parents[1] / "assets" / "soundboard_files"
DEFAULT_ERROR_MESSAGE = "⚠️ An unexpected error occurred while processing your request. Please try again later."
VC_INACTIVITY_TIMEOUT = 180  # Disconnect after 3 minutes of idle inactivity


class SoundSelect(discord.ui.Select):
    """Dropdown menu enabling users to play any sound on the current page directly."""

    def __init__(self, sounds: list):
        options = [
            discord.SelectOption(
                label=s.name,
                value=s.name,
            )
            for s in sounds
        ]
        super().__init__(
            placeholder="Select a sound to play in your voice channel...",
            min_values=1,
            max_values=1,
            options=options,
            row=0,
            custom_id="sb_play_select",
        )

    async def callback(self, interaction: discord.Interaction):
        voice_state = getattr(interaction.user, "voice", None)
        if not voice_state or not voice_state.channel:
            await interaction.response.send_message(
                "You must be connected to a voice channel to play a sound.", ephemeral=True
            )
            return

        selected_sound = self.values[0]
        view: "SoundboardPaginationView" = self.view
        success, err_msg, sound = await view.cog._execute_play(
            guild=interaction.guild,
            voice_channel=voice_state.channel,
            sound_name=selected_sound,
        )
        if not success:
            await interaction.response.send_message(f"⚠️ {err_msg}", ephemeral=True)
            return

        # Spawn the small embed with the Replay button
        embed = discord.Embed(
            description=f"Playing `{sound.name}` ({sound.duration:.2f}s)",
            color=discord.Color.blue(),
        )
        replay_view = SoundReplayView(view.cog, sound.name)
        await interaction.response.send_message(embed=embed, view=replay_view)
        replay_view.message = await interaction.original_response()


class SoundboardPaginationView(discord.ui.View):
    """Interactive pagination controls and play dropdown for browsing the soundboard table."""

    def __init__(
        self,
        cog: "SoundboardCog",
        author_id: int,
        current_page: int,
        total_pages: int,
        total_count: int,
        current_sounds: list,
    ):
        super().__init__(timeout=180.0)
        self.cog = cog
        self.author_id = author_id
        self.current_page = current_page
        self.total_pages = total_pages
        self.total_count = total_count
        self.message: Optional[discord.Message] = None

        # Add select menu on top row to play sounds directly
        self.sound_select = SoundSelect(current_sounds)
        self.add_item(self.sound_select)

        self._sync_buttons()

    def _sync_buttons(self):
        """Enable or disable Previous/Next buttons based on current page position."""
        self.prev_button.disabled = self.current_page <= 1
        self.next_button.disabled = self.current_page >= self.total_pages

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.primary, custom_id="sb_prev", row=1)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the person who ran this command can change pages.", ephemeral=True
            )
            return

        if self.current_page > 1:
            self.current_page -= 1
            await self._change_page(interaction)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.primary, custom_id="sb_next", row=1)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the person who ran this command can change pages.", ephemeral=True
            )
            return

        if self.current_page < self.total_pages:
            self.current_page += 1
            await self._change_page(interaction)
        else:
            await interaction.response.defer()

    async def _change_page(self, interaction: discord.Interaction):
        try:
            sounds, total_count = await get_all_sounds(
                page=self.current_page, page_size=ITEMS_PER_PAGE
            )
            self.total_count = total_count
            self.total_pages = max(1, math.ceil(total_count / ITEMS_PER_PAGE))
            self._sync_buttons()

            # Update dropdown menu options to match the new page's sounds
            self.sound_select.options = [
                discord.SelectOption(
                    label=s.name,
                    value=s.name,
                )
                for s in sounds
            ]

            embed = build_soundboard_embed(
                sounds=sounds,
                page=self.current_page,
                total_pages=self.total_pages,
                total_count=self.total_count,
            )
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e:
            logger.error(f"Error during soundboard page change: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.defer()

    async def on_timeout(self) -> None:
        """Disable buttons and dropdown when the view times out."""
        for item in self.children:
            if isinstance(item, (discord.ui.Button, discord.ui.Select)):
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except (discord.NotFound, discord.HTTPException):
                pass


class SoundReplayView(discord.ui.View):
    """Interactive view providing a Replay button for a played sound."""

    def __init__(self, cog: "SoundboardCog", sound_name: str, timeout: float = 300.0):
        super().__init__(timeout=timeout)
        self.cog = cog
        self.sound_name = sound_name
        self.message: Optional[discord.Message] = None

    @discord.ui.button(label="Replay", style=discord.ButtonStyle.secondary, custom_id="sb_replay_btn")
    async def replay(self, interaction: discord.Interaction, button: discord.ui.Button):
        voice_state = getattr(interaction.user, "voice", None)
        if not voice_state or not voice_state.channel:
            await interaction.response.send_message(
                "You must be connected to a voice channel to replay this sound.", ephemeral=True
            )
            return

        # Silently acknowledge so no new embed or message is created
        await interaction.response.defer()

        success, err_msg, _ = await self.cog._execute_play(
            guild=interaction.guild,
            voice_channel=voice_state.channel,
            sound_name=self.sound_name,
        )
        if not success:
            await interaction.followup.send(f"⚠️ {err_msg}", ephemeral=True)

    async def on_timeout(self) -> None:
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except (discord.NotFound, discord.HTTPException):
                pass


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

    async def _execute_play(
        self,
        guild: discord.Guild,
        voice_channel: discord.VoiceChannel | discord.StageChannel,
        sound_name: str,
    ) -> tuple[bool, str, Optional[Any]]:
        """Core audio execution worker used by commands and interaction buttons."""
        sound = await get_sound(sound_name)
        if not sound:
            return False, f"Sound `{sound_name}` not found. Use `+sb list` to view available sounds.", None

        sound_path = SOUNDBOARD_DIR / sound.local_file_name
        if not sound_path.exists():
            logger.error(f"Sound file missing on disk: {sound_path} for sound '{sound.name}'")
            return False, "Audio file is missing from local storage. Please notify an administrator.", None

        voice_client: Optional[discord.VoiceClient] = guild.voice_client

        try:
            if not voice_client or not voice_client.is_connected():
                voice_client = await voice_channel.connect(timeout=10.0)
            elif voice_client.channel != voice_channel:
                await voice_client.move_to(voice_channel)
        except discord.Forbidden:
            return False, "Bot lacks permission to join or speak in that voice channel.", None
        except asyncio.TimeoutError:
            return False, "Failed to connect to the voice channel (connection timed out).", None
        except Exception as e:
            logger.error(f"Error connecting to voice channel: {e}", exc_info=True)
            return False, DEFAULT_ERROR_MESSAGE, None

        # If a sound is already playing, cut it off and play the new sound immediately
        if voice_client.is_playing():
            voice_client.stop()

        self._cancel_disconnect_timer(guild.id)

        def after_playing(error):
            if error:
                logger.error(f"Error during audio playback for '{sound.name}': {error}", exc_info=error)
            # Only start disconnect timer if a new sound hasn't already started playing
            vc = guild.voice_client
            if vc and not vc.is_playing():
                self._start_disconnect_timer(guild)

        try:
            audio_source = discord.FFmpegPCMAudio(str(sound_path))
            voice_client.play(audio_source, after=after_playing)
            await increment_sound_times_played(sound.id)
            return True, "", sound
        except Exception as e:
            logger.error(f"Failed to play audio source '{sound_path}': {e}", exc_info=True)
            self._start_disconnect_timer(guild)
            return False, DEFAULT_ERROR_MESSAGE, None

    async def _play_sound_helper(self, ctx: commands.Context, sound_name: str):
        """Internal helper to connect to VC, play a sound, and attach a Replay button."""
        if not ctx.author.voice or not ctx.author.voice.channel:
            await ctx.send("⚠️ You must be connected to a voice channel to play a sound!")
            return

        success, err_msg, sound = await self._execute_play(
            guild=ctx.guild,
            voice_channel=ctx.author.voice.channel,
            sound_name=sound_name,
        )
        if not success:
            await ctx.send(f"⚠️ {err_msg}")
            return

        embed = discord.Embed(
            description=f"Playing `{sound.name}` ({sound.duration:.2f}s)",
            color=discord.Color.blue(),
        )
        view = SoundReplayView(self, sound.name)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

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
            embed.add_field(
                name="Add a sound",
                value="`+sb add <name>` *(attach audio, max 10s, max 5MB; no spaces, use `-` or `_`)*",
                inline=False,
            )
            embed.add_field(name="List sounds", value="`+sb list [page]`", inline=False)
            embed.add_field(name="Sound details", value="`+sb info <name>`", inline=False)
            await ctx.send(embed=embed)

    @soundboard.command(name="play", description="Play a sound in your current voice channel.")
    async def play(self, ctx: commands.Context, name: str):
        """Explicit command to play a sound: +sb play <name>"""
        await self._play_sound_helper(ctx, name)

    @soundboard.command(name="add", description="Add a new sound file (attach audio, max 10s, max 5MB).")
    async def add(self, ctx: commands.Context, *, name: str):
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

            # 6. Probe audio for playable format & duration <= 10.0s
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
        """List sounds in table format with pagination and forward/backward buttons."""
        try:
            page = max(1, page)
            sounds, total_count = await get_all_sounds(page=page, page_size=ITEMS_PER_PAGE)

            if total_count == 0:
                await ctx.send("The soundboard is currently empty. Use `+sb add <name>` with an attached audio file to add one.")
                return

            total_pages = max(1, math.ceil(total_count / ITEMS_PER_PAGE))
            if page > total_pages:
                page = total_pages
                sounds, total_count = await get_all_sounds(page=page, page_size=ITEMS_PER_PAGE)

            embed = build_soundboard_embed(
                sounds=sounds,
                page=page,
                total_pages=total_pages,
                total_count=total_count,
            )

            view = SoundboardPaginationView(
                cog=self,
                author_id=ctx.author.id,
                current_page=page,
                total_pages=total_pages,
                total_count=total_count,
                current_sounds=sounds,
            )
            message = await ctx.send(embed=embed, view=view)
            view.message = message

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

