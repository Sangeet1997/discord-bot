
import discord
from discord.ext import commands

from router.join import join_vc
from router.router import setup as setup_router
from config.settings import settings

from database.db import engine

from logger.logger import setup_logging
import logging

setup_logging()

logger = logging.getLogger(__name__)

class myBot(commands.Bot):
	def __init__(self):
		intents = discord.Intents.default()
		intents.message_content = True
		intents.voice_states = True

		super().__init__(command_prefix = "+", intents=intents)

	async def setup_hook(self):
		# setup
		await setup_router(self)

	async def close(self):
		# teardown
		await engine.dispose()
		await super().close()

bot = myBot()

@bot.event
async def on_ready():
	logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")
	

@bot.command()
async def join(ctx):
	await join_vc(ctx)
	

if __name__ == "__main__":
	bot.run(settings.DISCORD_TOKEN)