import asyncio
import logging
import random
from typing import List, Optional
import discord

from config.settings import settings
from database.crud import (
    get_user,
    add_user,
    decrement_user_points,
    increment_user_points,
    get_or_create_vault,
    update_vault,
)

logger = logging.getLogger(__name__)


async def process_bully_payment(author_id: int, target_id: int, target_name: str) -> None:
    """
    Deducts the bully cost from the author, awards 50% to the target,
    and deposits 25% into the slot machine vault.
    """
    cost = settings.BULLY_POINTS_COST
    half_share = cost // 2
    vault_share = cost // 4

    try:
        await decrement_user_points(author_id, cost)

        target_user = await get_user(target_id)
        if not target_user:
            await add_user(target_id, target_name)
        await increment_user_points(target_id, half_share)

        await get_or_create_vault(settings.SLOT_MACHINE_VAULT)
        await update_vault(settings.SLOT_MACHINE_VAULT, vault_share)
    except Exception as e:
        logger.error(f"Failed processing bully points (author: {author_id}, target: {target_id}): {e}", exc_info=True)
        raise


async def execute_member_moves(
    member: discord.Member,
    voice_channels: List[discord.VoiceChannel],
    num_moves: Optional[int] = None,
    move_interval: Optional[float] = None,
) -> None:
    """
    Moves a member between random voice channels, then attempts to return them
    to their original channel. Handles disconnects and permissions gracefully.
    """
    if not member.voice or not member.voice.channel:
        logger.info(f"{member.display_name} is not connected to a voice channel.")
        return

    moves = num_moves if num_moves is not None else settings.NUMBER_OF_MOVES
    interval = move_interval if move_interval is not None else settings.MOVE_INTERVAL

    starting_channel = member.voice.channel
    current_channel = starting_channel

    for step in range(moves):
        # Verify voice state at each step
        if not member.voice or not member.voice.channel:
            logger.info(f"{member.display_name} disconnected during move {step + 1}/{moves}.")
            break

        available_channels = [vc for vc in voice_channels if vc.id != current_channel.id]
        if not available_channels:
            break

        target_channel = random.choice(available_channels)
        try:
            await member.move_to(target_channel)
            current_channel = target_channel
        except discord.Forbidden:
            logger.warning("Bot lacks permission to move members.")
            raise
        except discord.HTTPException as e:
            logger.error(f"Failed to move {member.display_name} to {target_channel.name}: {e}")
            break

        await asyncio.sleep(interval)

    # Return user to starting channel
    try:
        if member.voice and member.voice.channel and current_channel.id != starting_channel.id:
            await member.move_to(starting_channel)
    except (discord.HTTPException, discord.Forbidden) as e:
        logger.warning(f"Could not return {member.display_name} to {starting_channel.name}: {e}")

