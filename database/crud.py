from sqlalchemy import select, update, delete
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
        await session.refresh(User)
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


    pass

async def delete_user():
    pass