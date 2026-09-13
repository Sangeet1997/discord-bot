import asyncio
import logging
from typing import Optional
import discord
from discord.ext import commands

from config.settings import settings
from core.slot_machine.engine import process_spin, get_slot_pot, SPIN_COST

logger = logging.getLogger(__name__)


class SlotMachineView(discord.ui.View):
    def __init__(self, cog: "CasinoCog"):
        super().__init__(timeout=180.0)
        self.cog = cog

    @discord.ui.button(label=f"Spin ({SPIN_COST}c)", style=discord.ButtonStyle.primary)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.cog.is_spinning:
            embed = discord.Embed(title="🎰 Slot Machine", description="A spin is already in progress!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        self.cog.is_spinning = True
        button.disabled = True

        try:
            spin_result = await process_spin(interaction.user.id)
        except ValueError as ve:
            self.cog.is_spinning = False
            button.disabled = False
            embed = discord.Embed(
                title="🎰 Slot Machine",
                description=f"# 🖕 off, you are poor.\nStay in any VC to get coins(c).",
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        except Exception as e:
            self.cog.is_spinning = False
            button.disabled = False
            logger.error(f"Error during slot spin for user {interaction.user.id}: {e}", exc_info=True)
            embed = discord.Embed(title="🎰 Slot Machine", description="⚠️ Database error. Please try again later.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        reels = [settings.EMPTY_SLOT, settings.EMPTY_SLOT, settings.EMPTY_SLOT]

        try:
            for i in range(3):
                reels[i] = spin_result.reels[i]
                embed = discord.Embed(title="🎰 Slot Machine", description=f"# [ {' | '.join(reels)} ]")
                embed.add_field(name="Spinner", value=interaction.user.display_name, inline=True)
                embed.add_field(name="Balance", value=spin_result.points_after if i == 2 else spin_result.points_before, inline=True)
                embed.add_field(name="Pot", value=spin_result.pot_after if i == 2 else spin_result.pot_before, inline=True)
                embed.add_field(name="Result", value=spin_result.outcome if i == 2 else "Spinning...", inline=False)

                if i == 0:
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    await interaction.message.edit(embed=embed, view=self)

                if i < 2:
                    await asyncio.sleep(0.2)
        except Exception as e:
            logger.error(f"Error updating slot machine animation: {e}", exc_info=True)
        finally:
            self.cog.is_spinning = False
            button.disabled = False


class CasinoCog(commands.Cog, name="Casino"):
    """Casino games including slot machines."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.active_message: Optional[discord.Message] = None
        self.is_spinning: bool = False

    @commands.command(name="slots", description="Play slot machine")
    async def slots(self, ctx: commands.Context):
        if self.is_spinning:
            await ctx.send("A slot machine is currently spinning!")
            return

        if self.active_message:
            try:
                await self.active_message.delete()
            except (discord.HTTPException, discord.NotFound) as e:
                logger.debug(f"Failed to delete previous slot machine message: {e}")

        try:
            pot_points = await get_slot_pot()
        except Exception as e:
            logger.error(f"Failed to fetch slot pot: {e}", exc_info=True)
            pot_points = 0

        try:
            placeholder = settings.EMPTY_SLOT
            embed = discord.Embed(title="🎰 Slot Machine", description=f"# [ {placeholder} | {placeholder} | {placeholder} ]")
            embed.add_field(name="Pot", value=pot_points, inline=True)
            self.active_message = await ctx.send(embed=embed, view=SlotMachineView(self))
        except Exception as e:
            logger.error(f"Failed to send slot machine message: {e}", exc_info=True)
            await ctx.send("⚠️ An error occurred while opening the slot machine. Please try again later.")


async def setup(bot: commands.Bot):
    await bot.add_cog(CasinoCog(bot))

