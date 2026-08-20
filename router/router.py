from router.text_response.response import setup as setup_text_response
from router.text_response.voice_channel_cmds import setup as setup_voice_channel_cmds

async def setup(bot):
    await setup_text_response(bot)
    await setup_voice_channel_cmds(bot)