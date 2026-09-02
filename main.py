import os
import dotenv

import discord
from discord.ext import commands

from router.join import join_vc
from router.router import setup as setup_router

dotenv.load_dotenv()

class myBot(commands.Bot):
	def __init__(self):
		intents = discord.Intents.default()
		intents.message_content = True
		intents.voice_states = True

		super().__init__(command_prefix = "+", intents=intents)

	async def setup_hook(self):
		# add db connection
		await setup_router(bot)
		pass

	async def close(self):
		# teardown
		# db.close()
		await super().close()

bot = myBot()

@bot.event
async def on_ready():
	print(f"Logged in as {bot.user} (ID: {bot.user.id})")
	

@bot.command()
async def join(ctx):
	await join_vc(ctx)
	
token = os.getenv("DISCORD_TOKEN")
if not token:
	raise RuntimeError("Set the DISCORD_TOKEN environment variable before starting the bot.")

bot.run(token)