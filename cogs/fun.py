import logging
import discord
from discord import app_commands
from discord.ext import commands

from config.settings import settings
from database.crud import get_user
from core.bully.coordinator import process_bully_payment, execute_member_moves

logger = logging.getLogger(__name__)

DEFAULT_ERROR_MESSAGE = "⚠️ An unexpected error occurred while processing your request. Please try again later."


class FunCog(commands.Cog, name="Fun"):
    """Fun and interactive server commands."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="bully", description="Move a member between random voice channels.")
    @app_commands.describe(member="The guild member to move between voice channels")
    async def bully(self, ctx: commands.Context, member: discord.Member):
        logger.info(f"Bully triggered by {ctx.author} (ID: {ctx.author.id}) on {member} (ID: {member.id})")

        # 1. Guild & Voice channel checks
        guild = self.bot.get_guild(settings.GUILD_ID) or ctx.guild
        if not guild:
            await ctx.send("Guild not found.")
            return

        voice_state = getattr(member, "voice", None)
        if not voice_state or not voice_state.channel:
            await ctx.send(f"{member.mention} is not in a voice channel.")
            return

        voice_channels = guild.voice_channels
        if len(voice_channels) < 2:
            await ctx.send("Need at least 2 voice channels in the guild to move the member.")
            return

        # 2. Check author points
        cost = settings.BULLY_POINTS_COST
        try:
            author_user = await get_user(ctx.author.id)
        except Exception as e:
            logger.error(f"Failed to fetch user {ctx.author.id}: {e}", exc_info=True)
            await ctx.send("⚠️ Database error. Please try again later.")
            return

        if not author_user or author_user.points < cost:
            await ctx.send(
                f"🖕 off, you are poor.! You need {cost}c.\n"
                "Stay in any VC to get coins(c), or play slot_machine (with `+slots`) to try your luck!"
            )
            return

        # 3. Process payment
        try:
            await process_bully_payment(
                author_id=ctx.author.id,
                target_id=member.id,
                target_name=member.display_name,
            )
        except Exception as e:
            logger.error(f"Failed to process bully points transaction: {e}", exc_info=True)
            await ctx.send("⚠️ Database error while processing points. Please try again later.")
            return

        await ctx.send(f"Bullying {member.mention}!")

        # 4. Execute moves
        try:
            await execute_member_moves(
                member=member,
                voice_channels=voice_channels,
            )
        except discord.Forbidden:
            await ctx.send("⚠️ I do not have permission to move members.")
        except Exception as e:
            logger.error(f"Unexpected error while executing bully moves: {e}", exc_info=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(FunCog(bot))

