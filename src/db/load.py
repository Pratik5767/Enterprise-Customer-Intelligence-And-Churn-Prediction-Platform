from src.db.models import Customer
from src.db.session import Base, SessionLocal, engine



def init_db() -> None:
    Base.metadata.create_all(bind=engine)      # creates tables if they don't exist


def upsert_customers(df) -> int:
    """Insert new customers, update existing ones. Safe to run repeatedly."""
    
    cols = [c.name for c in Customer.__table__.columns if c.name != "created_at"]
    data = df[cols].astype(object)
    records = data.where(data.notna(), None).to_dict("records")
    with SessionLocal() as session:
        for rec in records:
            session.merge(Customer(**rec))     # merge = insert-or-update by primary key
        session.commit()
    return len(records)

