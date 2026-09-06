import asyncio

import random
import discord
from discord import app_commands
from discord.ext import commands

from config.settings import settings
from database.crud import get_user

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
        except Exception:
            embed = discord.Embed(title="🎰 Slot Machine", description="Database error. Please try again later.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not user or user.points < 25:
            embed = discord.Embed(title="🎰 Slot Machine", description="# 🖕 off, you are poor.\nStay in any VC to get points.")
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        self.cog.is_spinning = True
        button.disabled = True
        results = random.choices(settings.EMOJIS, k=3)
        outcome = ""
        points_before = user.points

        result_set = set(results)
        if len(result_set) == 1:
            if settings.WIN_EMOJI in result_set:
                outcome = "You won the whole pot!!"
            else:
                outcome = "(3 match) You won 25% of the whole pot!!"
        elif len(result_set) == 2:
            outcome = "(2 match) Free spin you get 25c"
        else:
            outcome = "No match"

        points_after = user.points

        reels = [settings.EMPTY_SLOT, settings.EMPTY_SLOT, settings.EMPTY_SLOT]

        try:
            for i in range(3):
                reels[i] = results[i]
                embed = discord.Embed(title="🎰 Slot Machine", description=f"# [ {' | '.join(reels)} ]")
                embed.add_field(name="Spinner", value=interaction.user.display_name, inline=True)
                embed.add_field(name="Balance", value=points_after if i == 2 else points_before, inline=True)
                embed.add_field(name="Result", value=outcome if i == 2 else "Spinning...", inline=False)

                if i == 0:
                    await interaction.response.edit_message(embed=embed, view=self)
                else:
                    await interaction.message.edit(embed=embed, view=self)

                if i < 2:
                    await asyncio.sleep(1)
        finally:
            self.cog.is_spinning = False
            self.cog.active_message = None

class SlotMachine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_message = None
        self.is_spinning = False

    @app_commands.command(name="slots", description="Play slot machine")
    async def slots(self, interaction: discord.Interaction):
        if self.is_spinning:
            await interaction.response.send_message("A slot machine is currently spinning!", ephemeral=True)
            return

        if self.active_message:
            try:
                await self.active_message.delete()
            except discord.HTTPException:
                pass

        placeholder = settings.EMPTY_SLOT
        embed = discord.Embed(title="🎰 Slot Machine", description=f"# [ {placeholder} | {placeholder} | {placeholder} ]")
        await interaction.response.send_message(embed=embed, view=SlotMachineView(self))
        self.active_message = await interaction.original_response()

async def setup(bot):
    await bot.add_cog(SlotMachine(bot))
