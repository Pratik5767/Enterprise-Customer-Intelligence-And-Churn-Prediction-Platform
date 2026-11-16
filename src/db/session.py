import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker



# SQLite for development. 
# For PostgreSQL set an environment variable, e.g. postgresql+psycopg2://user:password@localhost:5432/churn_db
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///churn.db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass