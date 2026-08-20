import os
import dotenv

import discord
from discord.ext import commands

from router.router import setup as setup_router

dotenv.load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="+", intents=intents)

@bot.event
async def on_ready():
	if bot.user is None:
		return

	print(f"Logged in as {bot.user} (ID: {bot.user.id})")
	await setup_router(bot)

token = os.getenv("DISCORD_TOKEN")
if not token:
	raise RuntimeError("Set the DISCORD_TOKEN environment variable before starting the bot.")

bot.run(token)