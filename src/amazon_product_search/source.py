from typing import Optional

import pandas as pd

from amazon_product_search.constants import DATA_DIR


def load_products(locale: str, nrows: Optional[int] = None) -> pd.DataFrame:
    filename = f"{DATA_DIR}/product_catalogue-v0.3_{locale}.csv.zip"
    return pd.read_csv(filename, nrows=nrows, engine="python")


def load_labels(locale: str, nrows: Optional[int] = None) -> pd.DataFrame:
    filename = f"{DATA_DIR}/train-v0.3_{locale}.csv.zip"
    return pd.read_csv(filename, nrows=nrows, engine="python")
