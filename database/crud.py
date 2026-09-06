from sqlalchemy import select, update, delete
from sqlalchemy.dialects.mysql import insert
from database.db import async_session_factory
from database.models import User, Point_Vault


async def get_all_users():
    pass

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
    Inserts users if they do not exist with initial points/xp,
    or atomically increments points/xp if they already exist in a single query.
    user_data format: [{'id': member_id, 'name': member_name, 'points': int, 'xp': int}, ...]
    """
    if not user_data:
        return

    stmt = insert(User).values(user_data)
    stmt = stmt.on_duplicate_key_update(
        points=User.points + stmt.inserted.points,
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