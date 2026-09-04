import discord
from discord.ext import commands

import logging

logger = logging.getLogger(__name__)

@commands.command()
async def ping(ctx):
	"""Check whether the bot is responding."""
	logger.info(f"Sending response for ping with pong user: {ctx}")
	await ctx.send("Pong2!")

@commands.command()
async def ding(ctx):
	"""Check whether the bot is responding."""
	await ctx.send("Dong!")

@commands.command()
async def ching(ctx):
	"""Check whether the bot is responding."""
	await ctx.send("Chong!")

async def setup(bot):
    bot.add_command(ping)
    bot.add_command(ding)
    bot.add_command(ching)

