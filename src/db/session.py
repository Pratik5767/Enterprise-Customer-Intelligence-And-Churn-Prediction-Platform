import os
from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, sessionmaker



# SQLite for development. 
# For PostgreSQL set an environment variable, e.g. postgresql+psycopg2://user:password@localhost:5432/churn_db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///churn.db")

engine = create_engine(DATABASE_URL)


# Enforce foreign keys in SQLite
@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_key(dbapi_connection, _record):
    if engine.dialect.name == "sqlite":
        dbapi_connection.execute("PRAGMA foreign_keys=ON")


SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass