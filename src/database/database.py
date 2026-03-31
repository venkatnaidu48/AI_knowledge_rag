"""
Database connection and session management
"""

from sqlalchemy import create_engine, pool, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from typing import Generator
import logging

from config.settings import get_settings
from src.database.models import Base

logger = logging.getLogger(__name__)
settings = get_settings()


# Create database engine
engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    pool_pre_ping=True,
    pool_recycle=settings.DATABASE_POOL_RECYCLE,
    echo=settings.DEBUG,
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def initialize_database():
    """Initialize database - create all tables"""
    try:
        logger.info("Initializing database...")
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        raise


def get_database_session() -> Generator[Session, None, None]:
    """
    Dependency for getting database session
    Usage: def my_endpoint(db: Session = Depends(get_database_session)):
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def close_database_connection():
    """Close all database connections"""
    logger.info("Closing database connections...")
    engine.dispose()
    logger.info("Database connections closed")


# Connection pooling event listeners for debugging
@event.listens_for(engine, "connect")
def receive_connect(dbapi_conn, connection_record):
    """Log connection events"""
    if settings.DEBUG:
        logger.debug("Database connection opened")


@event.listens_for(engine, "close")
def receive_close(dbapi_conn, connection_record):
    """Log close events"""
    if settings.DEBUG:
        logger.debug("Database connection closed")


@event.listens_for(engine, "checkin")
def receive_checkin(dbapi_conn, connection_record):
    """Log checkin events (connection returned to pool)"""
    if settings.DEBUG:
        logger.debug("Database connection returned to pool")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_conn, connection_record, connection_proxy):
    """Log checkout events (connection taken from pool)"""
    if settings.DEBUG:
        logger.debug("Database connection taken from pool")
