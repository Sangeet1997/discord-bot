from router.text_response.response import setup as setup_text_response
from router.image_response.pray import setup as setup_pray

async def setup(bot):
    await setup_text_response(bot)
    await setup_pray(bot)