from src.db.models import ModelExperiment
from src.db.session import Base, SessionLocal, engine



def log_experiments(rows: list[dict]) -> None:
    Base.metadata.create_all(bind=engine)       # creates model_experiments if it doesn't exist yet
    
    with SessionLocal() as session:
        for row in rows:
            session.add(ModelExperiment(**row))
        session.commit()

