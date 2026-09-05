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

        self.USER_POINTS_INTERVAL = 5
        self.INTERVAL_POINT_AMOUNT = 25
        self.INTERVAL_XP_AMOUNT = 25

settings = Settings()