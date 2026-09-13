import logging
from typing import List, Dict, Any, Optional
import discord

from config.settings import settings

logger = logging.getLogger(__name__)


def evaluate_vc_members(guild: Optional[discord.Guild]) -> List[Dict[str, Any]]:
    """
    Scans all voice channels in the guild and calculates points and XP for active, non-bot members.
    Protects against missing voice states or disconnected members.
    """
    if not guild:
        return []

    try:
        vc_members = {
            member
            for vc in guild.voice_channels
            for member in vc.members
            if member and not member.bot
        }
    except Exception as e:
        logger.error(f"Error reading voice channels from guild {guild.id}: {e}", exc_info=True)
        return []

    if not vc_members:
        return []

    half_points = settings.INTERVAL_POINT_AMOUNT // 2
    users_data: List[Dict[str, Any]] = []

    for member in vc_members:
        try:
            voice = getattr(member, "voice", None)
            points = settings.INTERVAL_POINT_AMOUNT
            xp = settings.INTERVAL_XP_AMOUNT

            if voice:
                is_deaf_or_mute = any([
                    getattr(voice, "self_deaf", False),
                    getattr(voice, "deaf", False),
                    getattr(voice, "self_mute", False),
                    getattr(voice, "mute", False),
                ])
                is_streaming = any([
                    getattr(voice, "self_stream", False),
                    getattr(voice, "self_video", False),
                ])

                if is_deaf_or_mute:
                    points = settings.DEAFENED_INTERVAL_POINT_AMOUNT
                elif is_streaming:
                    points += half_points

            users_data.append({
                "id": member.id,
                "name": getattr(member, "name", "Unknown"),
                "points": points,
                "xp": xp,
            })
        except Exception as e:
            logger.error(f"Error evaluating rewards for member {getattr(member, 'id', 'unknown')}: {e}", exc_info=True)
            continue

    return users_data

