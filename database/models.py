from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, String, Integer

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
    password: Mapped[str] = mapped_column(String(25),default="password")

