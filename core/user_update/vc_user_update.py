from config.settings import settings
import discord
from discord.ext import commands, tasks

import logging

logger = logging.getLogger(__name__)

class VcUserUpdateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_server_data.start()

    def cog_unload(self) -> None:
        self.check_server_data.cancel()

    @tasks.loop(seconds=5)
    async def check_server_data(self):

        guild = self.bot.get_guild(settings.GUILD_ID)

        if not guild:
            raise ValueError(f"Guild not found; Guild id:{settings.GUILD_ID}")
            logger.error(f"Guild not found; Guild id:{settings.GUILD_ID}")

        print(f"[{guild.name}] Members: {len(guild.members)}, Channels: {len(guild.channels)}")

    @check_server_data.before_loop
    async def before_check(self):

        # Wait until the bot is ready before executing the loop
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(VcUserUpdateCog(bot))
