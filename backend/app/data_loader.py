import os
import pandas as pd
from pathlib import Path
from typing import Tuple

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def calculate_rate_band(monthly_rate_inr: int) -> str:
    """Categorizes a monthly rate into low, mid, or high rate band."""
    if monthly_rate_inr < 200000:
        return "low"
    elif monthly_rate_inr <= 300000:
        return "mid"
    else:
        return "high"


def load_hoardings(data_path: Path = None) -> pd.DataFrame:
    """Loads hoardings.csv with error handling and rate band computation."""
    target_path = data_path or (DATA_DIR / "hoardings.csv")
    if not target_path.exists():
        raise FileNotFoundError(f"Hoardings dataset not found at {target_path}")

    try:
        hoardings_df = pd.read_csv(target_path)
        required_columns = {"site_id", "location", "size_sqft", "traffic_score", "monthly_rate_inr"}
        if not required_columns.issubset(hoardings_df.columns):
            missing = required_columns - set(hoardings_df.columns)
            raise ValueError(f"Missing required columns in hoardings CSV: {missing}")

        hoardings_df["site_id"] = hoardings_df["site_id"].astype(str).str.strip()
        hoardings_df["location"] = hoardings_df["location"].astype(str).str.strip()
        hoardings_df["size_sqft"] = hoardings_df["size_sqft"].astype(int)
        hoardings_df["traffic_score"] = hoardings_df["traffic_score"].astype(float)
        hoardings_df["monthly_rate_inr"] = hoardings_df["monthly_rate_inr"].astype(int)
        hoardings_df["rate_band"] = hoardings_df["monthly_rate_inr"].apply(calculate_rate_band)

        return hoardings_df
    except Exception as exc:
        raise RuntimeError(f"Error loading hoardings CSV: {str(exc)}") from exc


def load_customers(data_path: Path = None) -> pd.DataFrame:
    """Loads customers.csv with error handling."""
    target_path = data_path or (DATA_DIR / "customers.csv")
    if not target_path.exists():
        raise FileNotFoundError(f"Customers dataset not found at {target_path}")

    try:
        customers_df = pd.read_csv(target_path)
        required_columns = {"customer_id", "name", "industry", "budget_band", "relationship_score", "last_contact_date"}
        if not required_columns.issubset(customers_df.columns):
            missing = required_columns - set(customers_df.columns)
            raise ValueError(f"Missing required columns in customers CSV: {missing}")

        customers_df["customer_id"] = customers_df["customer_id"].astype(str).str.strip()
        customers_df["name"] = customers_df["name"].astype(str).str.strip()
        customers_df["industry"] = customers_df["industry"].astype(str).str.strip()
        customers_df["budget_band"] = customers_df["budget_band"].astype(str).str.strip().str.lower()
        customers_df["relationship_score"] = customers_df["relationship_score"].astype(int)
        customers_df["last_contact_date"] = pd.to_datetime(customers_df["last_contact_date"]).dt.strftime("%Y-%m-%d")

        return customers_df
    except Exception as exc:
        raise RuntimeError(f"Error loading customers CSV: {str(exc)}") from exc


def load_bookings(data_path: Path = None) -> pd.DataFrame:
    """Loads bookings.csv with date parsing and validation."""
    target_path = data_path or (DATA_DIR / "bookings.csv")
    if not target_path.exists():
        raise FileNotFoundError(f"Bookings dataset not found at {target_path}")

    try:
        bookings_df = pd.read_csv(target_path)
        required_columns = {"booking_id", "site_id", "customer_id", "start_date", "end_date", "value_inr"}
        if not required_columns.issubset(bookings_df.columns):
            missing = required_columns - set(bookings_df.columns)
            raise ValueError(f"Missing required columns in bookings CSV: {missing}")

        bookings_df["booking_id"] = bookings_df["booking_id"].astype(str).str.strip()
        bookings_df["site_id"] = bookings_df["site_id"].astype(str).str.strip()
        bookings_df["customer_id"] = bookings_df["customer_id"].astype(str).str.strip()
        bookings_df["start_date"] = pd.to_datetime(bookings_df["start_date"]).dt.strftime("%Y-%m-%d")
        bookings_df["end_date"] = pd.to_datetime(bookings_df["end_date"]).dt.strftime("%Y-%m-%d")
        bookings_df["value_inr"] = bookings_df["value_inr"].astype(int)

        return bookings_df
    except Exception as exc:
        raise RuntimeError(f"Error loading bookings CSV: {str(exc)}") from exc


def load_all_datasets(data_dir: Path = None) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Loads all three CSV datasets together."""
    base_dir = data_dir or DATA_DIR
    hoardings = load_hoardings(base_dir / "hoardings.csv")
    customers = load_customers(base_dir / "customers.csv")
    bookings = load_bookings(base_dir / "bookings.csv")
    return hoardings, customers, bookings
