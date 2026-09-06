import discord
from discord.ext import commands

import logging

from database.crud import get_user

logger = logging.getLogger(__name__)

@commands.command()
async def ping(ctx):
	"""Check whether the bot is responding."""
	logger.info(f"Sending response for ping with pong user: {ctx.author.id}")
	await ctx.send("Pong2!")

@commands.command()
async def ding(ctx):
	"""Check whether the bot is responding."""
	await ctx.send("Dong!")

@commands.command()
async def ching(ctx):
	"""Check whether the bot is responding."""
	await ctx.send("Chong!")

@commands.command()
async def balance(ctx):
	try:
		user = await get_user(user_id=ctx.author.id)
		if not user:
			await ctx.send("You do not have an entry yet, stay in any vc for sometime")
		else:
			await ctx.send(f"Balance: {user.points}c")
	except Exception as e:
		logger.error("Error on getting balance: ", e)
		await ctx.send("Error getting balance")

async def setup(bot):
    bot.add_command(ping)
    bot.add_command(ding)
    bot.add_command(ching)
    bot.add_command(balance)

