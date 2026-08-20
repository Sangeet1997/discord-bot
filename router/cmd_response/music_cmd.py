import asyncio
import os
import shutil

import discord
from discord.ext import commands
import yt_dlp


YTDL_OPTIONS = {
    "format": "bestaudio/best",
    "noplaylist": True,
    "quiet": True,
    "default_search": "auto",
}


def find_executable(name: str) -> str | None:
    configured_path = os.getenv(f"{name.upper()}_PATH")
    if configured_path and os.path.isfile(configured_path):
        return configured_path

    return shutil.which(name)


for runtime in ("deno", "node"):
    runtime_path = find_executable(runtime)
    if runtime_path:
        YTDL_OPTIONS["js_runtimes"] = {runtime: {"path": runtime_path}}
        break

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}
FFMPEG_EXECUTABLE = find_executable("ffmpeg") or "ffmpeg"


def extract_audio_url(url: str) -> tuple[str, str]:
    with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:  # type: ignore[arg-type]
        info = ydl.extract_info(url, download=False)
    if not isinstance(info, dict):
        raise ValueError("The URL did not resolve to a playable track.")

    audio_url = info.get("url")
    if not isinstance(audio_url, str):
        raise ValueError("The URL did not provide a playable audio stream.")

    title = info.get("title", "the requested track")
    return audio_url, title if isinstance(title, str) else "the requested track"


@commands.command()
async def play(ctx, url: str | None = None):
    """Join the author's voice channel and play audio from a URL."""
    if not ctx.author.voice:
        await ctx.send("You are not connected to a voice channel.")
        return

    channel = ctx.author.voice.channel
    voice_client = ctx.voice_client
    if voice_client is None:
        voice_client = await channel.connect()
    elif voice_client.channel != channel:
        await voice_client.move_to(channel)

    if not url:
        await ctx.send("Usage: +play <url>")
        return

    try:
        audio_url, title = await asyncio.to_thread(extract_audio_url, url)
    except Exception:
        await ctx.send("I could not find playable audio at that URL.")
        return

    if voice_client.is_playing():
        voice_client.stop()

    try:
        source = discord.FFmpegPCMAudio(
            audio_url,
            executable=FFMPEG_EXECUTABLE,
            before_options=FFMPEG_OPTIONS["before_options"],
            options=FFMPEG_OPTIONS["options"],
        )
        voice_client.play(source)
    except discord.ClientException:
        await ctx.send(
            "FFmpeg was not found. Install the FFmpeg executable and add it to PATH, "
            "or set the FFMPEG_PATH environment variable."
        )
        return

    await ctx.send(f"Now playing: {title}")

@commands.command()
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Audio paused.")
    else:
        await ctx.send("No audio is currently playing.")

@commands.command()
async def resume(ctx):
    if ctx.voice_client and ctx.voice_client.is_paused():
        ctx.voice_client.resume()
        await ctx.send("Audio resumed.")
    else:
        await ctx.send("No audio is currently paused.")

@commands.command()
async def stop(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("Audio stopped.")
    else:
        await ctx.send("No audio is currently playing.")

async def setup(bot):
    bot.add_command(play)
    bot.add_command(pause)
    bot.add_command(resume)
    bot.add_command(stop)