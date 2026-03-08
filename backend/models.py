from datetime import datetime, timezone
from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTable
from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass

class User(SQLAlchemyBaseUserTable[int], Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # email, hashed_password, is_active, is_superuser, is_verified
    # are all provided by SQLAlchemyBaseUserTable

    accounts: Mapped[list["Account"]] = relationship("Account", back_populates="user", cascade="all, delete-orphan")

class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    user: Mapped["User"] = relationship("User", back_populates="accounts")
    statements: Mapped[list["Statement"]] = relationship("Statement", back_populates="account", cascade="all, delete-orphan")

class Statement(Base):
    __tablename__ = "statements"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    account_number: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[str] = mapped_column(String, nullable=False)
    end_date: Mapped[str] = mapped_column(String, nullable=False)
    opening_balance: Mapped[float] = mapped_column(Float, nullable=False)
    closing_balance: Mapped[float] = mapped_column(Float, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now())

    account: Mapped["Account"] = relationship("Account", back_populates="statements")
    transactions: Mapped[list["Transaction"]] = relationship("Transaction", back_populates="statement", cascade="all, delete-orphan")


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    statement_id: Mapped[int] = mapped_column(Integer, ForeignKey("statements.id"), nullable=False)
    date: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=True)
    balance: Mapped[float] = mapped_column(Float, nullable=True)
    type: Mapped[str] = mapped_column(String, nullable=False)
    category: Mapped[str] = mapped_column(String, nullable=True)

    statement: Mapped["Statement"] = relationship("Statement", back_populates="transactions")