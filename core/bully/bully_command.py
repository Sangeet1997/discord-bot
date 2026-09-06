import asyncio
import logging
import random
import discord
from discord import app_commands
from discord.ext import commands

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

class BullyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="bully", description="Move a member between random voice channels.")
    async def bully(self, ctx: commands.Context, member: discord.Member):
        """Trigger handler for the bully command."""
        logger.info(f"Bully command triggered by {ctx.author} (ID: {ctx.author.id}) on target {member} (ID: {member.id})")

        # Edge cases
        guild = self.bot.get_guild(settings.GUILD_ID) or ctx.guild
        if not guild:
            await ctx.send("Guild not found.")
            return

        if not member.voice or not member.voice.channel:
            await ctx.send(f"{member.mention} is not in a voice channel.")
            return

        voice_channels = guild.voice_channels
        if len(voice_channels) < 2:
            await ctx.send("Need at least 2 voice channels in the guild to move the member.")
            return

        # Check author points
        cost = settings.BULLY_POINTS_COST
        try:
            author_user = await get_user(ctx.author.id)
        except Exception as e:
            logger.error(f"Failed to fetch user {ctx.author.id}: {e}", exc_info=True)
            await ctx.send("Database error. Please try again later.")
            return

        if not author_user or author_user.points < cost:
            await ctx.send(
                f"🖕 off, you are poor.! You need {cost}c.\n"
                "Stay in any VC to get coins(c), or play slot_machine (with `/slots`) to try your luck!"
            )
            return

        # Deduct cost from author, reward bullied member (half), and add 1/4 to slot machine vault
        half_share = cost // 2
        vault_share = cost // 4

        try:
            await decrement_user_points(ctx.author.id, cost)

            target_user = await get_user(member.id)
            if not target_user:
                await add_user(member.id, member.display_name)
            await increment_user_points(member.id, half_share)

            await get_or_create_vault(settings.SLOT_MACHINE_VAULT)
            await update_vault(settings.SLOT_MACHINE_VAULT, vault_share)
        except Exception as e:
            logger.error(f"Failed to process points for bully command: {e}", exc_info=True)
            await ctx.send("Database error while processing points. Please try again later.")
            return

        await ctx.send(f"Bullying {member.mention}!")

        starting_channel = member.voice.channel
        current_channel = starting_channel
        num_moves = settings.NUMBER_OF_MOVES

        for _ in range(num_moves):
            if not member.voice or not member.voice.channel:
                logger.info(f"{member} is no longer connected to a voice channel.")
                break

            available_channels = [vc for vc in voice_channels if vc.id != current_channel.id]
            if not available_channels:
                break

            target_channel = random.choice(available_channels)
            try:
                await member.move_to(target_channel)
                current_channel = target_channel
            except discord.Forbidden:
                await ctx.send("I do not have permission to move members.")
                return
            except discord.HTTPException as e:
                logger.error(f"Failed to move {member} to {target_channel.name}: {e}")
                break

            await asyncio.sleep(settings.MOVE_INTERVAL)

        # Move user back to the channel they started in
        if member.voice and member.voice.channel and current_channel.id != starting_channel.id:
            try:
                await member.move_to(starting_channel)
            except discord.HTTPException as e:
                logger.error(f"Failed to move {member} back to starting channel {starting_channel.name}: {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(BullyCog(bot))
