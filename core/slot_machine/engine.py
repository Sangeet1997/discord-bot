from dataclasses import dataclass
import logging
import random
from typing import List

from config.settings import settings
from database.crud import get_user, get_or_create_vault, update_vault, increment_user_points

logger = logging.getLogger(__name__)

SPIN_COST = 25

@dataclass
class SpinResult:
    reels: List[str]
    outcome: str
    winnings: int
    points_before: int
    points_after: int
    pot_before: int
    pot_after: int


async def get_slot_pot() -> int:
    """Fetch the current pot balance from the vault."""
    try:
        vault = await get_or_create_vault(settings.SLOT_MACHINE_VAULT)
        return vault.points if vault else 0
    except Exception as e:
        logger.error(f"Failed to fetch slot vault pot: {e}", exc_info=True)
        raise


async def process_spin(user_id: int) -> SpinResult:
    """
    Executes a single spin for a user:
    - Validates points
    - Generates 3 random reel symbols
    - Calculates winnings and adjusts vault/user points
    """
    user = await get_user(user_id)
    if not user:
        raise ValueError("User not found in database.")
    if user.points < SPIN_COST:
        raise ValueError(f"Insufficient points. Required: {SPIN_COST}c, current: {user.points}c.")

    points_before = user.points

    # 1. Fetch pot and deduct entry fee
    vault = await get_or_create_vault(settings.SLOT_MACHINE_VAULT)
    current_pot = vault.points + SPIN_COST
    await increment_user_points(user_id, -SPIN_COST)
    await update_vault(settings.SLOT_MACHINE_VAULT, SPIN_COST)

    # 2. Spin reels
    reels = random.choices(settings.EMOJIS, k=3)
    result_set = set(reels)

    # 3. Calculate winnings
    if len(result_set) == 1:
        if settings.WIN_EMOJI in result_set:
            winnings = current_pot
            outcome = f"You won the whole pot ({winnings} points)!!"
        else:
            winnings = current_pot // 4
            outcome = f"(3 match) You won 25% of the pot ({winnings} points)!!"
        await increment_user_points(user_id, winnings)
        await update_vault(settings.SLOT_MACHINE_VAULT, -winnings)
    elif reels[0] == reels[1] or reels[1] == reels[2]:
        winnings = SPIN_COST
        outcome = "(2 match) Free spin! You got 25 points back"
        await increment_user_points(user_id, winnings)
        await update_vault(settings.SLOT_MACHINE_VAULT, -winnings)
    else:
        winnings = 0
        outcome = "No match"

    points_after = points_before - SPIN_COST + winnings
    pot_after = current_pot - winnings

    return SpinResult(
        reels=reels,
        outcome=outcome,
        winnings=winnings,
        points_before=points_before,
        points_after=points_after,
        pot_before=current_pot,
        pot_after=pot_after,
    )

