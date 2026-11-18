import pandas as pd

from src.config import PROCESSED_DIR
from src.ml.predict import predict_batch
from src.ml.settings import DATA_PATH, MODEL_VERSION



def main():
    df = pd.read_csv(DATA_PATH)
    active = df[df["subscription_status"] == "active"]        # eligible = customers still subscribed
    scores = predict_batch(active)
    out = pd.concat([active[["customer_id", "tenure", "contract_type", "monthly_charges"]], scores], axis=1)
    out = out.sort_values("churn_probability", ascending=False)
    out.to_csv(PROCESSED_DIR / f"predictions_{MODEL_VERSION}.csv", index=False)
    print(f"Scored {len(out):,} active customers; {int(out['predicted_churn'].sum()):,} flagged "
          f"at threshold {out['threshold'].iloc[0]:.2f}.")



if __name__ == "__main__":
    main()