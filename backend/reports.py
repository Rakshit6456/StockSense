"""CSV/PDF export (Person 4)."""
import pandas as pd

from backend.inventory import list_products, list_transactions


def inventory_report_df():
    return pd.DataFrame(list_products())


def sales_report_df(since=None):
    return pd.DataFrame(list_transactions(tx_type="SALE", since=since))


def export_csv(df, path):
    df.to_csv(path, index=False)
