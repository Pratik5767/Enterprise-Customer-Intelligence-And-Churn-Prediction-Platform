# from sqlalchemy import text
# from src.db.session import engine



# with engine.connect() as conn:
#     print(conn.execute(text("SELECT subscription_status, COUNT(*) FROM customers GROUP BY 1")).all())



from sqlalchemy import text
from src.db.session import engine
from src.db.history import customer_history, latest_scores

with engine.connect() as c:
    print(c.execute(text("SELECT batch_id, COUNT(*) FROM churn_predictions GROUP BY 1")).all())

cid = latest_scores()["customer_id"].iloc[0]
print(customer_history(cid))          # two rows, one per run, same customer
