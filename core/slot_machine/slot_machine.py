import asyncio

import random
import discord
from discord import app_commands
from discord.ext import commands

from config.settings import settings
from database.crud import get_user

class SlotMachineView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Spin (25c)", style=discord.ButtonStyle.primary)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):

        button.disabled = True
        results = random.choices(settings.EMOJIS, k=3)
        outcome = ""
        
        user = await get_user(interaction.user.id)
        if not user or user.points < 25:
            embed = discord.Embed(title="🎰 Slot Machine", description=f"# 🖕 off, you are poor.")
            # message: stay in any vc to get points.
            return
        
        points_before = user.points


        #slot machine logic
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

        # TODO: later add the points logic
        points_after = user.points
            
        



        reels = [settings.EMPTY_SLOT, settings.EMPTY_SLOT, settings.EMPTY_SLOT]

        for i in range(3):
            reels[i] = results[i]
            embed = discord.Embed(title="🎰 Slot Machine", description=f"# [ {' | '.join(reels)} ]")
            embed.add_field(name="Spinner", value=interaction.user.display_name, inline=True)
            embed.add_field(name="Balance", value=points_after if i == 2 else points_before, inline=True)
            embed.add_field(name="Result", value=outcome if i == 2 else "Spinning...", inline=False)

            if i == 0:
                await interaction.response.edit_message(embed=embed, view=self)
            else:
                if i == 2:
                await interaction.message.edit(embed=embed, view=self)

            if i < 2:
                await asyncio.sleep(1)

class SlotMachine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="slots", description="Play slot machine")
    async def slots(self, interaction: discord.Interaction):
        placeholder = settings.EMPTY_SLOT
        embed = discord.Embed(title="🎰 Slot Machine", description=f"# [ {placeholder} | {placeholder} | {placeholder} ]")
        await interaction.response.send_message(embed=embed, view=SlotMachineView())

async def setup(bot):
    await bot.add_cog(SlotMachine(bot))
