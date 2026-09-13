from sqlalchemy import select, update, delete, desc, func
from sqlalchemy.dialects.mysql import insert
from database.db import async_session_factory
from database.models import User, Point_Vault, Soundboard


async def get_all_users_by_point(page_number: int = 1):
    async with async_session_factory() as session:
        ITEMS_PER_PAGE = 10
        page = max(1, page_number)
        page_offset = (page - 1) * ITEMS_PER_PAGE

        stmt = (
            select(User)
            .order_by(desc(User.points))
            .limit(ITEMS_PER_PAGE)
            .offset(page_offset)
        )

        result = await session.execute(stmt)
        return result.scalars().all()


async def get_total_users_count() -> int:
    async with async_session_factory() as session:
        stmt = select(func.count(User.id))
        result = await session.execute(stmt)
        return result.scalar() or 0

async def get_user(user_id: int):
    async with async_session_factory() as session:
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def add_user(user_id: int, name: str):
    async with async_session_factory() as session:
        async with session.begin():
            new_user = User(id=user_id, name=name)
            session.add(new_user)
        await session.refresh(new_user)
        return new_user


async def update_user(user_id: int, points: int):
    async with async_session_factory() as session:
        async with session.begin():
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(points=points)
            )
            await session.execute(stmt)


async def increment_user_points(user_id: int, points: int):
    """Atomically increments points for an existing user."""
    async with async_session_factory() as session:
        async with session.begin():
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(points=User.points + points)
            )
            await session.execute(stmt)


async def decrement_user_points(user_id: int, points: int):
    """Atomically decrements points for an existing user."""
    async with async_session_factory() as session:
        async with session.begin():
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(points=User.points - points)
            )
            await session.execute(stmt)


async def increment_user_xp(user_id: int, xp: int):
    """Atomically increments xp for an existing user."""
    async with async_session_factory() as session:
        async with session.begin():
            stmt = (
                update(User)
                .where(User.id == user_id)
                .values(xp=User.xp + xp)
            )
            await session.execute(stmt)


async def bulk_add_vc_points(user_data: list[dict]):
    """
    Inserts users if they do not exist with initial points (default 300 + given amount) and xp,
    or atomically increments points/xp if they already exist in a single query.
    user_data format: [{'id': member_id, 'name': member_name, 'points': int, 'xp': int}, ...]
    """
    if not user_data:
        return

    default_points = User.__table__.c.points.default.arg if User.__table__.c.points.default is not None else 300

    # Ensure new users receive the base default points + the earned amount
    formatted_data = [
        {
            **data,
            "points": data["points"] + default_points,
        }
        for data in user_data
    ]

    stmt = insert(User).values(formatted_data)
    stmt = stmt.on_duplicate_key_update(
        points=User.points + stmt.inserted.points - default_points,
        xp=User.xp + stmt.inserted.xp,
        name=stmt.inserted.name,
    )

    async with async_session_factory() as session:
        async with session.begin():
            await session.execute(stmt)


async def get_or_create_vault(vault_name: str):
    async with async_session_factory() as session:
        async with session.begin():
            stmt = select(Point_Vault).where(Point_Vault.vault_name == vault_name)
            result = await session.execute(stmt)
            vault = result.scalar_one_or_none()
            if not vault:
                vault = Point_Vault(vault_name=vault_name)
                session.add(vault)
        return vault


async def update_vault(vault_name:str, points: int):
    async with async_session_factory() as session:
        async with session.begin():
            stmt = (
                update(Point_Vault)
                .where(Point_Vault.vault_name == vault_name)
                .values(points= Point_Vault.points + points)
            )
            await session.execute(stmt)


async def delete_user():
    pass


async def get_sound(name: str):
    """Retrieve a sound record by unique name."""
    async with async_session_factory() as session:
        stmt = select(Soundboard).where(Soundboard.name == name.strip().lower())
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def get_all_sounds(page: int = 1, page_size: int = 10):
    """Retrieve paginated soundboard items along with total count."""
    async with async_session_factory() as session:
        count_stmt = select(func.count(Soundboard.id))
        total_result = await session.execute(count_stmt)
        total_count = total_result.scalar() or 0

        offset = max(0, (page - 1) * page_size)
        stmt = (
            select(Soundboard)
            .order_by(Soundboard.name.asc())
            .limit(page_size)
            .offset(offset)
        )
        result = await session.execute(stmt)
        return list(result.scalars().all()), total_count


async def add_sound(
    name: str,
    uploader: int,
    uploader_name: str,
    local_file_name: str,
    duration: float,
    file_size: int,
):
    """Create a new soundboard entry."""
    async with async_session_factory() as session:
        async with session.begin():
            sound = Soundboard(
                name=name.strip().lower(),
                uploader=uploader,
                uploader_name=uploader_name,
                local_file_name=local_file_name,
                duration=round(duration, 2),
                file_size=file_size,
                times_played=0,
            )
            session.add(sound)
        await session.refresh(sound)
        return sound


async def increment_sound_times_played(sound_id: int):
    """Atomically increment times_played for a sound."""
    async with async_session_factory() as session:
        async with session.begin():
            stmt = (
                update(Soundboard)
                .where(Soundboard.id == sound_id)
                .values(times_played=Soundboard.times_played + 1)
            )
            await session.execute(stmt)
