from pathlib import Path
import logging
import discord
from discord.ext import commands

from database.crud import get_user, add_user, increment_user_points

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).resolve().parents[2] / "assets" / "images"
IMAGE_PATH = ASSETS_DIR / "Screenshot 2026-09-06 001130.png"

@commands.command()
async def pray(ctx):
	"""Bless the user with 5 points and an image."""
	logger.info(f"Pray command invoked by user: {ctx.author.id}")

	try:
		user = await get_user(ctx.author.id)
		if not user:
			await add_user(ctx.author.id, ctx.author.display_name)
		await increment_user_points(ctx.author.id, 5)
	except Exception as e:
		logger.error(f"Failed to give pray points to {ctx.author.id}: {e}", exc_info=True)
		await ctx.send("Database error while processing your blessing. Please try again later.")
		return

	target_image = IMAGE_PATH
	if not target_image.exists() and ASSETS_DIR.exists():
		fallback_images = list(ASSETS_DIR.glob("*.*"))
		if fallback_images:
			target_image = fallback_images[0]

	if target_image.exists():
		file = discord.File(target_image)
		await ctx.send("You have been blessed 5c.", file=file)
	else:
		logger.warning(f"Blessing image not found at {IMAGE_PATH}")
		await ctx.send("You have been blessed 5c.")


async def setup(bot):
    bot.add_command(pray)

