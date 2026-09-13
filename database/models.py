from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, String, Integer, Float, DateTime, func

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=300)
    xp: Mapped[int] = mapped_column(Integer, default=0)

class Point_Vault(Base):
    __tablename__ = "point_vaults"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    vault_name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    points: Mapped[int] = mapped_column(Integer, default=0)
    password: Mapped[str] = mapped_column(String(25), default="password")

class Soundboard(Base):
    __tablename__ = "soundboard"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    uploader: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uploader_name: Mapped[str] = mapped_column(String(150), nullable=False)
    local_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    duration: Mapped[float] = mapped_column(Float, nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    times_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), nullable=False)
    modified_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now(), nullable=False
    )

