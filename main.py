import os

import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="+", intents=intents)


@bot.event
async def on_ready():
	print(f"Logged in as {bot.user} (ID: {bot.user.id})")

@bot.command()
async def ping(ctx):
	"""Check whether the bot is responding."""
	await ctx.send("Pong!")


token = os.getenv("DISCORD_TOKEN")
if not token:
	raise RuntimeError("Set the DISCORD_TOKEN environment variable before starting the bot.")

bot.run(token)