import math
import discord

ITEMS_PER_PAGE = 20


def build_soundboard_embed(
    sounds: list,
    page: int,
    total_pages: int,
    total_count: int,
) -> discord.Embed:
    """Constructs a clean, emoji-free monospace table embed for soundboard sounds."""
    embed = discord.Embed(
        title="Soundboard Library",
        color=discord.Color.blue(),
    )

    description_intro = (
        f"Use `+sb <name>` while in a voice channel to play a sound.\n"
        f"Total sounds: {total_count}\n\n"
    )

    if not sounds:
        embed.description = description_intro + "```text\nNo sounds found.\n```"
    else:
        start_idx = (page - 1) * ITEMS_PER_PAGE + 1
        header = f"{'#':<3} {'Name':<18} {'Duration':>8} {'Plays':>6} {'By':<10}"
        separator = "-" * len(header)
        rows = [header, separator]

        for idx, sound in enumerate(sounds):
            num = start_idx + idx
            name = sound.name
            if len(name) > 18:
                name = name[:16] + ".."

            duration_str = f"{sound.duration:.2f}s"
            plays_str = f"{sound.times_played}"
            uploader = sound.uploader_name or "System"
            if len(uploader) > 10:
                uploader = uploader[:8] + ".."

            rows.append(f"{num:<3} {name:<18} {duration_str:>8} {plays_str:>6} {uploader:<10}")

        table_text = "\n".join(rows)
        embed.description = description_intro + f"```text\n{table_text}\n```"

    embed.set_footer(text=f"Page {page} of {total_pages} • {total_count} total sounds")
    return embed

