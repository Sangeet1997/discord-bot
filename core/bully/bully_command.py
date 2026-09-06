import asyncio
import logging
import random
import discord
from discord import app_commands
from discord.ext import commands

from config.settings import settings

logger = logging.getLogger(__name__)

class BullyCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.hybrid_command(name="bully", description="Move a member between random voice channels.")
    async def bully(self, ctx: commands.Context, member: discord.Member):
        """Trigger handler for the bully command."""
        logger.info(f"Bully command triggered by {ctx.author} (ID: {ctx.author.id}) on target {member} (ID: {member.id})")

        # edge cases
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


        await ctx.send(f"Bullying {member.mention}")

        num_moves = settings.NUMBER_OF_MOVES

        for _ in range(num_moves):
            if not member.voice or not member.voice.channel:
                logger.info(f"{member} is no longer connected to a voice channel.")
                break

            available_channels = [vc for vc in voice_channels if vc.id != member.voice.channel.id]
            if not available_channels:
                break

            target_channel = random.choice(available_channels)
            try:
                await member.move_to(target_channel)
            except discord.Forbidden:
                await ctx.send("I do not have permission to move members.")
                return
            except discord.HTTPException as e:
                logger.error(f"Failed to move {member} to {target_channel.name}: {e}")
                break

            await asyncio.sleep(settings.MOVE_INTERVAL)

async def setup(bot: commands.Bot):
    await bot.add_cog(BullyCog(bot))
