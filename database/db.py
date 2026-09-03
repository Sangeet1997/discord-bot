
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from config.settings import settings


# If MYSQL_PASSWORD or MYSQL_USER contains special characters (e.g. @, :, #, %, /), 
# raw string interpolation will produce a broken connection string.

DATABASE_URL = (
    "mysql+asyncmy://"
    f"{settings.MYSQL_USER}:{settings.MYSQL_PASSWORD}@"
    f"{settings.MYSQL_HOST}/{settings.MYSQL_DB}"
)

engine = create_async_engine(DATABASE_URL)

async_session_factory = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
    autoflush=False,
)