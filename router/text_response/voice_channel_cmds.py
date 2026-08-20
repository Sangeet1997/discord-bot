import discord
from discord.ext import commands

@commands.command()
async def join(ctx):
    """Join the voice channel that the user is currently in."""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
    else:
        await ctx.send("You are not connected to a voice channel.")
    

@commands.command()
async def leave(ctx):
    """Leave the voice channel that the bot is currently in."""
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
    else:
        await ctx.send("I am not connected to a voice channel.")

async def setup(bot):
    bot.add_command(join)
    bot.add_command(leave)
