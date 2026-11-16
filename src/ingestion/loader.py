import pandas as pd
import requests



def load_csv(path) -> pd.DataFrame:
    """
    Read every column as text so pandas can't silently guess (and hide) bad types.
    """
    
    return pd.read_csv(path, dtype=str)


def load_api(url: str, headers: dict | None = None, timeout: int = 15) -> pd.DataFrame:
    """
    Fetch customer records from a JSON API and return them in the same all-text shape.
    """
    
    response = requests.get(url, headers=headers, timeout=timeout)
    response.raise_for_status()          # raises an error on 4xx/5xx instead of continuing
    payload = response.json()
    
    # Accept either [ {...}, {...} ] or {"data": [ {...}, {...} ]}
    records = (
        payload["data"] 
        if isinstance(payload, dict) and "data" in payload 
        else payload
    )

    df = pd.DataFrame(records)
    return df.where(df.isna(), df.astype(str))   # stringify everything except real nulls

