from pathlib import Path
import logging
import discord
from discord.ext import commands

from config.settings import settings
from database.db import engine
from logger.logger import setup_logging

setup_logging()

logger = logging.getLogger(__name__)


class myBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.members = True

        super().__init__(command_prefix="+", intents=intents)

    async def setup_hook(self):
        # Dynamically discover and load all cogs from the cogs directory
        cogs_dir = Path(__file__).resolve().parent / "cogs"
        for file in sorted(cogs_dir.glob("*.py")):
            if not file.name.startswith("__"):
                extension_name = f"cogs.{file.stem}"
                try:
                    await self.load_extension(extension_name)
                    logger.info(f"Successfully loaded extension: {extension_name}")
                except Exception as e:
                    logger.error(f"Failed to load extension {extension_name}: {e}", exc_info=True)

    async def close(self):
        # Teardown database connections on bot shutdown
        await engine.dispose()
        await super().close()


bot = myBot()


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")


@bot.event
async def on_command_error(ctx: commands.Context, error: commands.CommandError):
    """Global error handler to ensure uncaught command errors never crash the bot or go unlogged."""
    # Ignore unknown commands to avoid spam
    if isinstance(error, commands.CommandNotFound):
        return

    # Helpful feedback for common user input mistakes
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"⚠️ Missing required argument: `{error.param.name}`. Check `+info` for usage.")
        return

    if isinstance(error, commands.BadArgument):
        await ctx.send("⚠️ Invalid argument provided. Please check command format.")
        return

    # Log full traceback for any unexpected exception
    logger.error(f"Unhandled command error in '{ctx.command}': {error}", exc_info=error)
    try:
        await ctx.send("⚠️ An unexpected error occurred while executing this command. Please try again later.")
    except Exception as send_err:
        logger.error(f"Failed to send error message to channel: {send_err}")


if __name__ == "__main__":
    bot.run(settings.DISCORD_TOKEN)