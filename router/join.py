async def join_vc(ctx):
    """Join the voice channel that the user is currently in."""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        await channel.connect()
    else:
        await ctx.send("You are not connected to a voice channel.")
