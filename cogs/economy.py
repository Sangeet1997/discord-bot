import math
import logging
from typing import Optional
import discord
from discord import app_commands
from discord.ext import commands

from database.crud import get_user, get_all_users_by_point, get_total_users_count
from core.leaderboard.formatter import build_leaderboard_embed, ITEMS_PER_PAGE

logger = logging.getLogger(__name__)

DEFAULT_ERROR_MESSAGE = "⚠️ An unexpected error occurred while processing your request. Please try again later."


class LeaderboardView(discord.ui.View):
    def __init__(
        self,
        author_id: int,
        current_page: int,
        total_pages: int,
        total_users: int,
        timeout: float = 120.0,
    ):
        super().__init__(timeout=timeout)
        self.author_id = author_id
        self.current_page = current_page
        self.total_pages = total_pages
        self.total_users = total_users
        self.message: Optional[discord.Message] = None
        self._sync_buttons()

    def _sync_buttons(self):
        """Enable or disable Previous/Next buttons based on current page position."""
        self.prev_button.disabled = self.current_page <= 1
        self.next_button.disabled = self.current_page >= self.total_pages

    @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.primary, custom_id="lb_prev")
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the person who used this command can change pages.", ephemeral=True
            )
            return

        if self.current_page > 1:
            self.current_page -= 1
            await self._change_page(interaction)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.primary, custom_id="lb_next")
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message(
                "Only the person who used this command can change pages.", ephemeral=True
            )
            return

        if self.current_page < self.total_pages:
            self.current_page += 1
            await self._change_page(interaction)
        else:
            await interaction.response.defer()

    async def _change_page(self, interaction: discord.Interaction):
        try:
            users = await get_all_users_by_point(page_number=self.current_page)
            self._sync_buttons()
            embed = build_leaderboard_embed(
                users=users,
                page=self.current_page,
                total_pages=self.total_pages,
                total_count=self.total_users,
            )
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception as e:
            logger.error(f"Error changing leaderboard page to {self.current_page}: {e}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "⚠️ Failed to load page. Please try again later.", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "⚠️ Failed to load page. Please try again later.", ephemeral=True
                )

    async def on_timeout(self):
        """Disable buttons once interaction window expires."""
        for item in self.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except (discord.NotFound, discord.HTTPException) as e:
                logger.debug(f"Could not edit timed-out leaderboard message: {e}")


class EconomyCog(commands.Cog, name="Economy"):
    """Economy commands including balance checks and leaderboards."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="balance", description="Check your current coin balance.")
    async def balance(self, ctx: commands.Context):
        try:
            user = await get_user(user_id=ctx.author.id)
            if not user:
                await ctx.send("You do not have an entry yet, stay in any vc for sometime")
            else:
                await ctx.send(f"Balance: {user.points}c")
        except Exception as e:
            logger.error(f"Error fetching balance for user {ctx.author.id}: {e}", exc_info=True)
            await ctx.send("⚠️ Error getting balance. Please try again later.")

    @commands.hybrid_command(
        name="leaderboard",
        aliases=["top", "lb"],
        description="Show top members ranked by points.",
    )
    @app_commands.describe(page="The page number to view (defaults to 1)")
    async def leaderboard(self, ctx: commands.Context, page: int = 1):
        logger.info(f"Leaderboard command invoked by {ctx.author} (ID: {ctx.author.id}) for page {page}")

        try:
            total_users = await get_total_users_count()
            total_pages = max(1, math.ceil(total_users / ITEMS_PER_PAGE))

            # Clamp requested page within valid bounds
            page = min(max(1, page), total_pages)

            users = await get_all_users_by_point(page_number=page)
            embed = build_leaderboard_embed(
                users=users,
                page=page,
                total_pages=total_pages,
                total_count=total_users,
            )
            view = LeaderboardView(
                author_id=ctx.author.id,
                current_page=page,
                total_pages=total_pages,
                total_users=total_users,
            )
            msg = await ctx.send(embed=embed, view=view)
            view.message = msg
        except Exception as e:
            logger.error(f"Failed to fetch leaderboard: {e}", exc_info=True)
            await ctx.send("⚠️ Database error while fetching leaderboard. Please try again later.")


async def setup(bot: commands.Bot):
    await bot.add_cog(EconomyCog(bot))

