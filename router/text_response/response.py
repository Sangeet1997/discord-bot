import discord
from discord.ext import commands

import logging

from database.crud import get_user

logger = logging.getLogger(__name__)

@commands.command()
async def ping(ctx):
    """Check whether the bot is responding."""
    logger.info(f"Sending response for ping with pong user: {ctx.author.id}")
    await ctx.send("Pong2!")

@commands.command()
async def ding(ctx):
    """Check whether the bot is responding."""
    await ctx.send("Dong!")

@commands.command()
async def ching(ctx):
    """Check whether the bot is responding."""
    await ctx.send("Chong!")

@commands.command()
async def balance(ctx):
    try:
        user = await get_user(user_id=ctx.author.id)
        if not user:
            await ctx.send("You do not have an entry yet, stay in any vc for sometime")
        else:
            await ctx.send(f"Balance: {user.points}c")
    except Exception as e:
        logger.error("Error on getting balance: ", e)
        await ctx.send("Error getting balance")

@commands.command()
async def info(ctx):
    """Display all available commands and their descriptions."""
    embed = discord.Embed(
        title="ℹ️ Available Commands",
        description="Command prefix: `+` (or slash commands where supported)",
        color=discord.Color.blue(),
    )
    embed.add_field(name="+balance", value="Check your coin balance.", inline=False)
    embed.add_field(name="/slots", value="Spin the slot machine for 25c to win the pot.", inline=False)
    embed.add_field(name="+bully @member", value="Move a member between random VCs (costs 100c).", inline=False)
    embed.add_field(name="+ping", value="Check bot responsiveness (Pong!).", inline=False)
    embed.add_field(name="+info", value="Show this commands list.", inline=False)
    embed.add_field(name="🎙️ VC Rewards", value="Stay in voice channels to passively earn coins & XP.", inline=False)
    await ctx.send(embed=embed)


async def setup(bot):
    bot.add_command(ping)
    bot.add_command(ding)
    bot.add_command(ching)
    bot.add_command(balance)
    bot.add_command(info)
