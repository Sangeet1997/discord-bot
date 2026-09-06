import os
import dotenv

dotenv.load_dotenv()

def get_env_vars(key: str):
    val = os.getenv(key)
    if not val:
        raise ValueError(f"Application cannot start without {key} in env variables")
    return val

class Settings:
    def __init__(self):
        self.MYSQL_USER = get_env_vars("MYSQL_USER")
        self.MYSQL_PASSWORD = get_env_vars("MYSQL_PASSWORD")
        self.MYSQL_HOST = get_env_vars("MYSQL_HOST")
        self.MYSQL_DB = get_env_vars("MYSQL_DB")
        self.DISCORD_TOKEN = get_env_vars("DISCORD_TOKEN")
        self.GUILD_ID = int(get_env_vars("GUILD_ID"))

        # Periodic xp and points
        self.USER_POINTS_INTERVAL = 5 # seconds
        self.INTERVAL_POINT_AMOUNT = 25
        self.INTERVAL_XP_AMOUNT = 25

        # Slot machine emojis
        self.EMOJIS = ["🖕", "😸", "🍆", "🍒", "💦"]
        self.WIN_EMOJI = "🖕" # three of these is a win
        self.EMPTY_SLOT = "➖"

        # slot machine vault name
        self.SLOT_MACHINE_VAULT = "slot_machine_vault"

        # bully settings
        self.NUMBER_OF_MOVES = 10
        self.MOVE_INTERVAL = 0.7 # in seconds
        self.BULLY_POINTS_COST = 100
        

settings = Settings()