import asyncio
import logging
import random
import discord
from discord.ext import commands

from config.settings import settings
from database.crud import get_user, get_or_create_vault, update_vault, increment_user_points

logger = logging.getLogger(__name__)

class SlotMachineView(discord.ui.View):
    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    @discord.ui.button(label="Spin (25c)", style=discord.ButtonStyle.primary)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.cog.is_spinning:
            embed = discord.Embed(title="🎰 Slot Machine", description="A spin is already in progress!")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        try:
            user = await get_user(interaction.user.id)
        except Exception as e:
            logger.error(f"Failed to fetch user {interaction.user.id}: {e}", exc_info=True)
            embed = discord.Embed(title="🎰 Slot Machine", description="Database error. Please try again later.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not user or user.points < 25:
            embed = discord.Embed(title="🎰 Slot Machine", description="# 🖕 off, you are poor.\nStay in any VC to get coins(c).")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        self.cog.is_spinning = True
        button.disabled = True
        results = random.choices(settings.EMOJIS, k=3)

        outcome = ""
        points_before = user.points

        try:
            vault = await get_or_create_vault(settings.SLOT_MACHINE_VAULT)
            current_pot = vault.points + 25
            await increment_user_points(interaction.user.id, -25)
            await update_vault(settings.SLOT_MACHINE_VAULT, 25)

            result_set = set(results)
            if len(result_set) == 1:
                if settings.WIN_EMOJI in result_set:
                    winnings = current_pot
                    outcome = f"You won the whole pot ({winnings} points)!!"
                else:
                    winnings = current_pot // 4
                    outcome = f"(3 match) You won 25% of the pot ({winnings} points)!!"
                await increment_user_points(interaction.user.id, winnings)
                await update_vault(settings.SLOT_MACHINE_VAULT, -winnings)
            elif results[0] == results[1] or results[1] == results[2]:
                winnings = 25
                outcome = "(2 match) Free spin! You got 25 points back"
                await increment_user_points(interaction.user.id, winnings)
                await update_vault(settings.SLOT_MACHINE_VAULT, -winnings)
            else:
                winnings = 0
                outcome = "No match"
        except Exception as e:
            logger.error(f"Error during spin processing for user {interaction.user.id}: {e}", exc_info=True)
            self.cog.is_spinning = False
            self.cog.active_message = None
            embed = discord.Embed(title="🎰 Slot Machine", description="Database error. Please try again later.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        points_after = points_before - 25 + winnings
        pot_after = current_pot - winnings

        reels = [settings.EMPTY_SLOT, settings.EMPTY_SLOT, settings.EMPTY_SLOT]

        try:
            for i in range(3):
                reels[i] = results[i]
                embed = discord.Embed(title="🎰 Slot Machine", description=f"# [ {' | '.join(reels)} ]")
                embed.add_field(name="Spinner", value=interaction.user.display_name, inline=True)
                embed.add_field(name="Balance", value=points_after if i == 2 else points_before, inline=True)
                embed.add_field(name="Pot", value=pot_after if i == 2 else current_pot, inline=True)
                embed.add_field(name="Result", value=outcome if i == 2 else "Spinning...", inline=False)

                if i == 0:
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    await interaction.message.edit(embed=embed, view=self)

                if i < 2:
                    await asyncio.sleep(0.2)
        finally:
            self.cog.is_spinning = False
            self.cog.active_message = None

class SlotMachine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_message = None
        self.is_spinning = False

    @commands.command(name="slots", description="Play slot machine")
    async def slots(self, ctx: commands.Context):
        if self.is_spinning:
            await ctx.send("A slot machine is currently spinning!")
            return

        if self.active_message:
            try:
                await self.active_message.delete()
            except discord.HTTPException as e:
                logger.warning(f"Failed to delete previous slot machine message: {e}")

        try:
            vault = await get_or_create_vault(settings.SLOT_MACHINE_VAULT)
            pot_points = vault.points
        except Exception as e:
            logger.error(f"Failed to fetch vault: {e}", exc_info=True)
            pot_points = 0

        placeholder = settings.EMPTY_SLOT
        embed = discord.Embed(title="🎰 Slot Machine", description=f"# [ {placeholder} | {placeholder} | {placeholder} ]")
        embed.add_field(name="Pot", value=pot_points, inline=True)
        self.active_message = await ctx.send(embed=embed, view=SlotMachineView(self))

async def setup(bot):
    await bot.add_cog(SlotMachine(bot))
