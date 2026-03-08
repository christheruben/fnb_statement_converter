from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from dotenv import load_dotenv
import os

"""This module sets up the database connection and session management for the application. It uses SQLAlchemy's asynchronous capabilities to allow for non-blocking database operations. The database URL is loaded from environment variables, and an asynchronous session maker is created to manage database sessions throughout the application."""

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_async_engine(DATABASE_URL, echo=True)

async_session_maker = async_sessionmaker(engine, expire_on_commit=False)


async def get_async_session():
    async with async_session_maker() as session:
        yield session