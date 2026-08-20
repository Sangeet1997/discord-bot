import os
import dotenv

import discord
from discord.ext import commands

from router.join import join_vc
from router.router import setup as setup_router

dotenv.load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="+", intents=intents)

@bot.event
async def on_ready():
	print(f"Logged in as {bot.user} (ID: {bot.user.id})")
	await setup_router(bot)

"""@bot.command()
async def join(ctx):
	await join_vc(ctx)"""
	
token = os.getenv("DISCORD_TOKEN")
if not token:
	raise RuntimeError("Set the DISCORD_TOKEN environment variable before starting the bot.")

bot.run(token)