import random
import discord
from discord import app_commands
from discord.ext import commands

from config.settings import settings

class SlotMachineView(discord.ui.View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Spin", style=discord.ButtonStyle.primary)
    async def spin(self, interaction: discord.Interaction, button: discord.ui.Button):
        result = " | ".join(random.choices(settings.EMOJIS, k=3))
        embed = discord.Embed(title="🎰 Slot Machine")
        embed.add_field(name="Reels", value=f"[ {result} ]", inline=False)
        await interaction.response.edit_message(embed=embed, view=self)

class SlotMachine(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="slots", description="Play slot machine")
    async def slots(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🎰 Slot Machine")
        embed.add_field(name="Reels", value="[ spin | spin | spin ]", inline=False)
        await interaction.response.send_message(embed=embed, view=SlotMachineView())

async def setup(bot):
    await bot.add_cog(SlotMachine(bot))
