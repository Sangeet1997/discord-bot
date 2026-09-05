from sqlalchemy import select, update, delete
from sqlalchemy.dialects.mysql import insert
from database.db import async_session_factory
from database.models import User


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


async def bulk_add_vc_points(user_data: list[dict], points_to_add: int):
    """
    Inserts users if they do not exist with initial points,
    or atomically increments points if they already exist in a single query.
    user_data format: [{'id': member_id, 'name': member_name}, ...]
    """
    if not user_data:
        return

    values = [
        {"id": u["id"], "name": u["name"], "points": points_to_add}
        for u in user_data
    ]

    stmt = insert(User).values(values)
    stmt = stmt.on_duplicate_key_update(
        points=User.points + points_to_add,
        name=stmt.inserted.name,
    )

    async with async_session_factory() as session:
        async with session.begin():
            await session.execute(stmt)


async def delete_user():
    pass