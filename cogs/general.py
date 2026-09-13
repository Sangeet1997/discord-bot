from pathlib import Path
import logging
import discord
from discord.ext import commands

from database.crud import get_user, add_user, increment_user_points

logger = logging.getLogger(__name__)

ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets" / "images"
BLESSING_IMAGE = ASSETS_DIR / "Screenshot 2026-09-06 001130.png"
DEFAULT_ERROR_MESSAGE = "⚠️ An unexpected error occurred while processing your request. Please try again later."


class GeneralCog(commands.Cog, name="General"):
    """General utility and fun commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="ping", description="Check whether the bot is responding.")
    async def ping(self, ctx: commands.Context):
        try:
            logger.info(f"Ping invoked by {ctx.author} (ID: {ctx.author.id})")
            await ctx.send("Pong!")
        except Exception as e:
            logger.error(f"Error in ping command: {e}", exc_info=True)
            await ctx.send(DEFAULT_ERROR_MESSAGE)

    @commands.command(name="ding", description="Check bot responsiveness.")
    async def ding(self, ctx: commands.Context):
        try:
            await ctx.send("Dong!")
        except Exception as e:
            logger.error(f"Error in ding command: {e}", exc_info=True)
            await ctx.send(DEFAULT_ERROR_MESSAGE)

    @commands.command(name="ching", description="Check bot responsiveness.")
    async def ching(self, ctx: commands.Context):
        try:
            await ctx.send("Chong!")
        except Exception as e:
            logger.error(f"Error in ching command: {e}", exc_info=True)
            await ctx.send(DEFAULT_ERROR_MESSAGE)

    @commands.command(name="info", description="Display all available commands and their descriptions.")
    async def info(self, ctx: commands.Context):
        try:
            embed = discord.Embed(
                title="ℹ️ Available Commands",
                description="Command prefix: `+` (or slash commands where supported)",
                color=discord.Color.blue(),
            )
            embed.add_field(name="+balance", value="Check your coin balance.", inline=False)
            embed.add_field(name="+leaderboard [page]", value="View points leaderboard (aliases: +top, +lb).", inline=False)
            embed.add_field(name="+slots", value="Spin the slot machine for 25c to win the pot.", inline=False)
            embed.add_field(name="+bully @member", value="Move a member between random VCs (costs 100c).", inline=False)
            embed.add_field(name="+pray", value="Receive a daily blessing of 5c and an image.", inline=False)
            embed.add_field(name="+ping", value="Check bot responsiveness (Pong!).", inline=False)
            embed.add_field(name="+info", value="Show this commands list.", inline=False)
            embed.add_field(name="🎙️ VC Rewards", value="Stay in voice channels to passively earn coins & XP.", inline=False)
            await ctx.send(embed=embed)
        except Exception as e:
            logger.error(f"Error sending info embed: {e}", exc_info=True)
            await ctx.send(DEFAULT_ERROR_MESSAGE)

    @commands.command(name="pray", description="Bless the user with 5 points and an image.")
    async def pray(self, ctx: commands.Context):
        logger.info(f"Pray command invoked by user: {ctx.author.id}")

        # Database transaction
        try:
            user = await get_user(ctx.author.id)
            if not user:
                await add_user(ctx.author.id, ctx.author.display_name)
            await increment_user_points(ctx.author.id, 5)
        except Exception as e:
            logger.error(f"Failed to give pray points to {ctx.author.id}: {e}", exc_info=True)
            await ctx.send("⚠️ Database error while processing your blessing. Please try again later.")
            return

        # Image resolution and delivery
        try:
            target_image = BLESSING_IMAGE
            if not target_image.exists() and ASSETS_DIR.exists():
                fallback_images = list(ASSETS_DIR.glob("*.*"))
                if fallback_images:
                    target_image = fallback_images[0]

            if target_image.exists():
                file = discord.File(target_image)
                await ctx.send("You have been blessed 5c.", file=file)
            else:
                logger.warning(f"Blessing image not found at {BLESSING_IMAGE}")
                await ctx.send("You have been blessed 5c.")
        except Exception as e:
            logger.error(f"Failed to send pray response for user {ctx.author.id}: {e}", exc_info=True)
            await ctx.send("You have been blessed 5c.")


async def setup(bot: commands.Bot):
    await bot.add_cog(GeneralCog(bot))

