from sqlalchemy import text
from src.db.session import engine



with engine.connect() as conn:
    print(conn.execute(text("SELECT subscription_status, COUNT(*) FROM customers GROUP BY 1")).all())

