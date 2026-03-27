"""Database configuration and base models"""

import asyncio
import re
from urllib.parse import urlparse
from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

try:
    import asyncpg
except ImportError:
    asyncpg = None

from app.core.config import settings


class Base(DeclarativeBase):
    """Base class for all database models"""

    pass


# Create async engine for SQLite or PostgreSQL
# Note: SQLite URL needs to be converted for async support
db_url = settings.db_url
if db_url.startswith("sqlite:///"):
    # Convert sqlite:/// to sqlite+aiosqlite:///
    async_db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
else:
    async_db_url = db_url

engine = create_async_engine(
    async_db_url,
    echo=settings.is_development,
    future=True,
)

# Create async session factory
async_session_maker = sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


# Enable WAL mode for SQLite (for better concurrency)
if "sqlite" in db_url:
    sync_engine = create_engine(
        db_url,
        echo=settings.is_development,
    )

    @event.listens_for(sync_engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Set SQLite pragmas for better performance"""
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
        cursor.execute("PRAGMA temp_store=MEMORY")
        cursor.execute("PRAGMA busy_timeout=30000")  # 30 seconds
        cursor.close()


async def get_db() -> AsyncSession:
    """Dependency for getting async database session"""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """Initialize database (create database and tables)"""
    # For PostgreSQL, ensure database exists
    if "postgresql" in db_url and asyncpg:
        # Extract database name from URL
        # Format: postgresql+asyncpg://user:password@host:port/dbname
        match = re.search(r'/([^/?]+)(?:\?|$)', db_url)
        db_name = match.group(1) if match else None
        
        if db_name:
            # Parse connection parameters
            parsed = urlparse(db_url.replace("postgresql+asyncpg://", "postgresql://"))
            
            try:
                # Connect directly to postgres database using asyncpg
                conn = await asyncpg.connect(
                    host=parsed.hostname or 'localhost',
                    port=parsed.port or 5432,
                    user=parsed.username or 'postgres',
                    password=parsed.password or 'postgres',
                    database='postgres'
                )
                
                try:
                    # Check if database exists and create if not
                    exists = await conn.fetchval(
                        f"SELECT 1 FROM pg_database WHERE datname = '{db_name}'"
                    )
                    if not exists:
                        # CREATE DATABASE must be run outside a transaction
                        await conn.execute(f'CREATE DATABASE "{db_name}"')
                finally:
                    await conn.close()
            except Exception as e:
                # If asyncpg is not available or connection fails, continue
                # SQLAlchemy will fail with a better error message anyway
                pass
            
            # Small delay to ensure database is ready
            await asyncio.sleep(0.5)
    
    # Create tables in the target database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Close database connections"""
    await engine.dispose()
