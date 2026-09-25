from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.config import config

db_url = config.DATABASE_URL
if db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql+psycopg2://", 1)
elif db_url.startswith("postgresql://") and not db_url.startswith("postgresql+"):
    db_url = db_url.replace("postgresql://", "postgresql+psycopg2://", 1)

connect_args = {}
if db_url.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(db_url, connect_args=connect_args)

if config.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        try:
            if engine.dialect.name == "sqlite":
                columns = [
                    row[1]
                    for row in conn.exec_driver_sql("PRAGMA table_info(users)").fetchall()
                ]
                if "language" not in columns:
                    conn.exec_driver_sql(
                        "ALTER TABLE users ADD COLUMN language VARCHAR(10) DEFAULT 'pt'"
                    )
                    conn.commit()
            elif engine.dialect.name == "postgresql":
                conn.exec_driver_sql(
                    "ALTER TABLE users ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'pt'"
                )
                conn.commit()
        except Exception:
            pass


@contextmanager
def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
