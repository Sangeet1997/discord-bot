"""TODO: Decide how to store soundboard audio files. For now, they will be stored in the repository's soundboard directory.
         Change command input so that bot offers a list that is clickable, instead of requiring the user to type the filename. 
         This will require a more complex command structure, possibly using a menu or reaction-based selection."""


from pathlib import Path

import discord
from discord.ext import commands

from router.cmd_response.music_cmd import FFMPEG_EXECUTABLE


SOUNDBOARD_DIR = Path(__file__).resolve().parents[2] / "soundboard"
AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".m4a"}


def get_soundboard_files() -> list[str]:
    if not SOUNDBOARD_DIR.is_dir():
        return []

    return sorted(
        file.name
        for file in SOUNDBOARD_DIR.iterdir()
        if file.is_file() and file.suffix.lower() in AUDIO_EXTENSIONS
    )


@commands.command()
async def soundboard(ctx, filename: str | None = None):
    """Play an audio file from the repository's soundboard directory."""
    if filename == "list":
        files = get_soundboard_files()
        if files:
            await ctx.send("Available soundboard files:\n" + "\n".join(files))
        else:
            await ctx.send("No soundboard audio files are currently stored.")
        return

    if not ctx.author.voice:
        await ctx.send("You are not connected to a voice channel.")
        return

    if not filename:
        await ctx.send("Usage: +soundboard <audio file name> or +soundboard list")
        return

    soundboard_dir = SOUNDBOARD_DIR.resolve()
    audio_path = (soundboard_dir / filename).resolve()
    try:
        audio_path.relative_to(soundboard_dir)
    except ValueError:
        await ctx.send("That audio file is not in the soundboard directory.")
        return

    if not audio_path.is_file():
        await ctx.send("That soundboard audio file was not found.")
        return

    channel = ctx.author.voice.channel
    voice_client = ctx.voice_client
    if voice_client is None:
        voice_client = await channel.connect()
    elif voice_client.channel != channel:
        await voice_client.move_to(channel)

    if voice_client.is_playing():
        voice_client.stop()

    try:
        source = discord.FFmpegPCMAudio(
            str(audio_path),
            executable=FFMPEG_EXECUTABLE,
            options="-vn",
        )
        voice_client.play(source)
    except discord.ClientException:
        await ctx.send(
            "FFmpeg was not found. Install the FFmpeg executable and add it to PATH, "
            "or set the FFMPEG_PATH environment variable."
        )
        return

    await ctx.send(f"Now playing: {audio_path.name}")


async def setup(bot):
    bot.add_command(soundboard)