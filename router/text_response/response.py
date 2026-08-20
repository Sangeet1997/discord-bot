import discord
from discord.ext import commands

@commands.command()
async def ping(ctx):
	"""Check whether the bot is responding."""
	await ctx.send("Pong!")

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

