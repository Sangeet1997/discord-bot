import discord
from discord.ext import commands

import logging

logger = logging.getLogger(__name__)

@commands.command()
async def pray(ctx):
	"""Check whether the bot is responding."""
	logger.info(f"Sending response for ping with pong user: {ctx.author.id}")
	await ctx.send("Pong2!")



async def setup(bot):
    bot.add_command(pray)
