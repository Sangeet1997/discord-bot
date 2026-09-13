import logging
import discord
from discord.ext import commands, tasks

from config.settings import settings
from database.crud import bulk_add_vc_points
from core.user_update.evaluator import evaluate_vc_members

logger = logging.getLogger(__name__)


class VcUserUpdateCog(commands.Cog, name="Tasks"):
    """Background tasks for periodic voice activity and user progression."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.check_server_data.start()

    def cog_unload(self) -> None:
        self.check_server_data.cancel()

    @tasks.loop(seconds=settings.USER_POINTS_INTERVAL)
    async def check_server_data(self):
        try:
            guild = self.bot.get_guild(settings.GUILD_ID)
            if not guild:
                logger.warning(f"Guild not found in cache; Guild id: {settings.GUILD_ID}")
                return

            users_data = evaluate_vc_members(guild)
            if not users_data:
                return

            await bulk_add_vc_points(users_data)
            logger.debug(f"Successfully awarded VC points to {len(users_data)} members.")
        except Exception as e:
            logger.error(f"Failed to update VC points for members: {e}", exc_info=True)

    @check_server_data.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

    @check_server_data.error
    async def on_check_error(self, error: Exception):
        logger.error(f"Unhandled error in check_server_data task loop: {error}", exc_info=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(VcUserUpdateCog(bot))

