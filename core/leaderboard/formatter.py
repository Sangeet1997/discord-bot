import logging
from typing import List, Any
import discord

logger = logging.getLogger(__name__)

ITEMS_PER_PAGE = 10


def build_leaderboard_embed(
    users: List[Any],
    page: int,
    total_pages: int,
    total_count: int,
) -> discord.Embed:
    """Constructs a formatted Discord Embed displaying the top users for the given page as a table."""
    embed = discord.Embed(
        title="🏆 Points Leaderboard",
        color=discord.Color.gold(),
    )

    if not users:
        embed.description = "```\nNo users found on the leaderboard.\n```"
    else:
        start_rank = (page - 1) * ITEMS_PER_PAGE + 1
        header = f"{'#':<4} {'User':<16} {'Points':>9} {'XP':>9}"
        separator = "-" * len(header)
        rows = [header, separator]

        for idx, user in enumerate(users):
            rank = start_rank + idx
            name = getattr(user, "name", None) or "Unknown"
            if len(name) > 16:
                name = name[:14] + ".."
            points = getattr(user, "points", 0) or 0
            xp = getattr(user, "xp", 0) or 0
            rows.append(f"{rank:<4} {name:<16} {points:>9,} {xp:>9,}")

        embed.description = f"```\n{'\n'.join(rows)}\n```"

    embed.set_footer(text=f"Page {page} of {total_pages} • {total_count} total members")
    return embed

