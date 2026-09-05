import logging
import discord
from discord.ext import commands, tasks
from config.settings import settings
from database.crud import bulk_add_vc_points

logger = logging.getLogger(__name__)

class VcUserUpdateCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_server_data.start()

    def cog_unload(self) -> None:
        self.check_server_data.cancel()

    @tasks.loop(seconds=settings.USER_POINTS_INTERVAL)
    async def check_server_data(self):
        guild = self.bot.get_guild(settings.GUILD_ID)

        if not guild:
            logger.warning(f"Guild not found in cache; Guild id: {settings.GUILD_ID}")
            return

        # Collect unique non-bot members across all voice channels
        vc_members = {
            member
            for vc in guild.voice_channels
            for member in vc.members
            if not member.bot
        }

        if not vc_members:
            return

        half_points = settings.INTERVAL_POINT_AMOUNT // 2
        users_data = []

        for member in vc_members:
            voice = member.voice
            points = settings.INTERVAL_POINT_AMOUNT
            xp = settings.INTERVAL_XP_AMOUNT

            if voice:
                if voice.self_deaf or voice.deaf:
                    points -= half_points
                elif voice.self_stream or voice.self_video:
                    points += half_points

            users_data.append({
                "id": member.id,
                "name": member.name,
                "points": points,
                "xp": xp,
            })

        try:
            await bulk_add_vc_points(users_data)
        except Exception as e:
            logger.error(f"Failed to update VC points for members: {e}", exc_info=True)


    @check_server_data.before_loop
    async def before_check(self):
        # Wait until the bot is ready before executing the loop
        await self.bot.wait_until_ready()

    @check_server_data.error
    async def on_check_error(self, error: Exception):
        logger.error(f"Unhandled error in check_server_data task loop: {error}", exc_info=True)

async def setup(bot):
    await bot.add_cog(VcUserUpdateCog(bot))
