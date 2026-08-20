from router.cmd_response.response import setup as setup_text_response
from router.cmd_response.voice_channel_cmds import setup as setup_voice_channel_cmds
from router.cmd_response.music_cmd import setup as setup_music_cmd
from router.cmd_response.soundboard_cmd import setup as setup_soundboard_cmd


async def setup(bot):
    await setup_text_response(bot)
    await setup_voice_channel_cmds(bot)
    await setup_music_cmd(bot)
    await setup_soundboard_cmd(bot)
