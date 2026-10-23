
import sqlite3
from pathlib import Path

import pandas as pd

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "data" / "retail_transactions.csv"
DB_FILE = BASE_DIR / "retail_warehouse.db"
SCHEMA_FILE = BASE_DIR / "schema.sql"

# Check required files
if not DATA_FILE.exists():
    raise FileNotFoundError(f"Dataset not found: {DATA_FILE}")

if not SCHEMA_FILE.exists():
    raise FileNotFoundError(f"Schema file not found: {SCHEMA_FILE}")

# Read retail data
df = pd.read_csv(DATA_FILE)
df.columns = df.columns.str.strip()

required = [
    "InvoiceNo", "InvoiceDate", "CustomerID", "City",
    "StockCode", "Description", "Quantity", "UnitPrice"
]

missing = [column for column in required if column not in df.columns]

if missing:
    raise ValueError(f"Missing columns in CSV: {missing}")

# Prepare data types and calculate sales
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="raise")
df["Quantity"] = pd.to_numeric(df["Quantity"], errors="raise").astype(int)
df["UnitPrice"] = pd.to_numeric(df["UnitPrice"], errors="raise")
df["Sales"] = df["Quantity"] * df["UnitPrice"]

# Connect to SQLite
with sqlite3.connect(DB_FILE) as connection:
    connection.execute("PRAGMA foreign_keys = ON")

    # Create the warehouse tables
    schema = SCHEMA_FILE.read_text(encoding="utf-8")
    connection.executescript(schema)

    # Rebuild tables so rerunning this script won't duplicate data
    connection.executescript("""
        DELETE FROM FactSales;
        DELETE FROM DimDate;
        DELETE FROM DimCustomer;
        DELETE FROM DimProduct;
        DELETE FROM DimCity;
    """)

    # Date dimension
    dates = pd.DataFrame({
        "FullDate": df["InvoiceDate"].dt.strftime("%Y-%m-%d")
    }).drop_duplicates().sort_values("FullDate")

    dates["DateKey"] = (
        pd.to_datetime(dates["FullDate"]).dt.strftime("%Y%m%d").astype(int)
    )
    dates["Month"] = pd.to_datetime(dates["FullDate"]).dt.month
    dates["MonthName"] = pd.to_datetime(dates["FullDate"]).dt.strftime("%B")
    dates["Quarter"] = (
        "Q" + pd.to_datetime(dates["FullDate"]).dt.quarter.astype(str)
    )
    dates["Year"] = pd.to_datetime(dates["FullDate"]).dt.year

    dates[[
        "DateKey", "FullDate", "Month",
        "MonthName", "Quarter", "Year"
    ]].to_sql("DimDate", connection, if_exists="append", index=False)

    # Customer dimension
    customers = (
        df[["CustomerID"]]
        .dropna()
        .drop_duplicates()
        .sort_values("CustomerID")
        .reset_index(drop=True)
    )
    customers["CustomerKey"] = range(1, len(customers) + 1)

    customers[["CustomerKey", "CustomerID"]].to_sql(
        "DimCustomer", connection, if_exists="append", index=False
    )

    # Product dimension
    products = (
        df[["StockCode", "Description"]]
        .drop_duplicates(subset=["StockCode"])
        .sort_values("StockCode")
        .reset_index(drop=True)
    )
    products["ProductKey"] = range(1, len(products) + 1)

    products[["ProductKey", "StockCode", "Description"]].to_sql(
        "DimProduct", connection, if_exists="append", index=False
    )

    # City dimension
    cities = (
        df[["City"]]
        .dropna()
        .drop_duplicates()
        .sort_values("City")
        .reset_index(drop=True)
    )
    cities["CityKey"] = range(1, len(cities) + 1)

    cities[["CityKey", "City"]].to_sql(
        "DimCity", connection, if_exists="append", index=False
    )

    # Create lookup dictionaries
    date_map = dict(zip(dates["FullDate"], dates["DateKey"]))
    customer_map = dict(zip(customers["CustomerID"], customers["CustomerKey"]))
    product_map = dict(zip(products["StockCode"], products["ProductKey"]))
    city_map = dict(zip(cities["City"], cities["CityKey"]))

    # Build the sales fact table
    fact = pd.DataFrame({
        "InvoiceNo": df["InvoiceNo"],
        "DateKey": df["InvoiceDate"].dt.strftime("%Y-%m-%d").map(date_map),
        "CustomerKey": df["CustomerID"].map(customer_map),
        "ProductKey": df["StockCode"].map(product_map),
        "CityKey": df["City"].map(city_map),
        "Quantity": df["Quantity"],
        "UnitPrice": df["UnitPrice"],
        "Sales": df["Sales"]
    })

    fact.to_sql("FactSales", connection, if_exists="append", index=False)

    # Print database summary
    print("\nDATABASE CREATED SUCCESSFULLY!")

    for table in [
        "DimDate", "DimCustomer", "DimProduct", "DimCity", "FactSales"
    ]:
        count = pd.read_sql_query(
            f"SELECT COUNT(*) AS total FROM {table}", connection
        )["total"][0]
        print(f"{table}: {count} records")

print(f"\nDatabase location: {DB_FILE}")
