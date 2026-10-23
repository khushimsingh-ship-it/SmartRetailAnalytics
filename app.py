
import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from mlxtend.frequent_patterns import apriori, association_rules


# --------------------------------------------------
# 1. PROJECT PATHS AND PAGE SETTINGS
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "retail_transactions.csv"
DB_FILE = BASE_DIR / "retail_warehouse.db"

st.set_page_config(
    page_title="Smart Retail Analytics",
    page_icon="🛍️",
    layout="wide"
)


# --------------------------------------------------
# 2. LOAD AND PREPARE RETAIL DATA
# --------------------------------------------------

@st.cache_data
def load_retail_data():
    if not DATA_FILE.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATA_FILE}"
        )

    df = pd.read_csv(DATA_FILE)

    required_columns = [
        "InvoiceNo", "InvoiceDate", "CustomerID", "City",
        "StockCode", "Description", "Quantity", "UnitPrice"
    ]

    missing = [
        col for col in required_columns if col not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing required CSV columns: {missing}"
        )

    df["InvoiceDate"] = pd.to_datetime(
        df["InvoiceDate"], errors="coerce"
    )
    df["Quantity"] = pd.to_numeric(
        df["Quantity"], errors="coerce"
    ).fillna(0)
    df["UnitPrice"] = pd.to_numeric(
        df["UnitPrice"], errors="coerce"
    ).fillna(0)

    df["Sales"] = df["Quantity"] * df["UnitPrice"]

    for col in ["InvoiceNo", "CustomerID", "City",
                "StockCode", "Description"]:
        df[col] = df[col].fillna("Unknown").astype(str)

    return df


# --------------------------------------------------
# 3. AUTOMATICALLY CREATE THE DATA WAREHOUSE
# --------------------------------------------------

def create_warehouse(df):
    with sqlite3.connect(DB_FILE) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS DimDate (
                DateKey INTEGER PRIMARY KEY,
                FullDate TEXT,
                Month INTEGER,
                MonthName TEXT,
                Quarter TEXT,
                Year INTEGER
            );

            CREATE TABLE IF NOT EXISTS DimCustomer (
                CustomerKey INTEGER PRIMARY KEY AUTOINCREMENT,
                CustomerID TEXT UNIQUE
            );

            CREATE TABLE IF NOT EXISTS DimProduct (
                ProductKey INTEGER PRIMARY KEY AUTOINCREMENT,
                StockCode TEXT UNIQUE,
                Description TEXT
            );

            CREATE TABLE IF NOT EXISTS DimCity (
                CityKey INTEGER PRIMARY KEY AUTOINCREMENT,
                City TEXT UNIQUE
            );

            CREATE TABLE IF NOT EXISTS FactSales (
                SalesKey INTEGER PRIMARY KEY AUTOINCREMENT,
                InvoiceNo TEXT,
                DateKey INTEGER,
                CustomerKey INTEGER,
                ProductKey INTEGER,
                CityKey INTEGER,
                Quantity REAL,
                UnitPrice REAL,
                Sales REAL,
                FOREIGN KEY (DateKey) REFERENCES DimDate(DateKey),
                FOREIGN KEY (CustomerKey) REFERENCES DimCustomer(CustomerKey),
                FOREIGN KEY (ProductKey) REFERENCES DimProduct(ProductKey),
                FOREIGN KEY (CityKey) REFERENCES DimCity(CityKey)
            );
        """)

        count = conn.execute(
            "SELECT COUNT(*) FROM FactSales"
        ).fetchone()[0]

        # Rebuild the generated warehouse if it is empty.
        if count == 0 and not df.empty:
            conn.execute("DELETE FROM FactSales")

            for table in [
                "DimDate", "DimCustomer", "DimProduct", "DimCity"
            ]:
                conn.execute(f"DELETE FROM {table}")

            dates = df.loc[
                df["InvoiceDate"].notna(), "InvoiceDate"
            ].drop_duplicates()

            date_rows = []
            for date in dates:
                date_rows.append((
                    int(date.strftime("%Y%m%d")),
                    date.strftime("%Y-%m-%d"),
                    date.month,
                    date.strftime("%B"),
                    f"Q{date.quarter}",
                    date.year
                ))

            conn.executemany("""
                INSERT OR IGNORE INTO DimDate
                (DateKey, FullDate, Month, MonthName, Quarter, Year)
                VALUES (?, ?, ?, ?, ?, ?)
            """, date_rows)

            customers = [
                (value,) for value in df["CustomerID"].unique()
            ]
            conn.executemany("""
                INSERT OR IGNORE INTO DimCustomer (CustomerID)
                VALUES (?)
            """, customers)

            products = [
                (code, description)
                for code, description in
                df[["StockCode", "Description"]]
                .drop_duplicates("StockCode")
                .itertuples(index=False, name=None)
            ]
            conn.executemany("""
                INSERT OR IGNORE INTO DimProduct
                (StockCode, Description) VALUES (?, ?)
            """, products)

            cities = [(value,) for value in df["City"].unique()]
            conn.executemany("""
                INSERT OR IGNORE INTO DimCity (City)
                VALUES (?)
            """, cities)

            date_map = dict(conn.execute(
                "SELECT FullDate, DateKey FROM DimDate"
            ).fetchall())
            customer_map = dict(conn.execute(
                "SELECT CustomerID, CustomerKey FROM DimCustomer"
            ).fetchall())
            product_map = dict(conn.execute(
                "SELECT StockCode, ProductKey FROM DimProduct"
            ).fetchall())
            city_map = dict(conn.execute(
                "SELECT City, CityKey FROM DimCity"
            ).fetchall())

            facts = []
            for row in df.itertuples(index=False):
                date_key = None
                if pd.notna(row.InvoiceDate):
                    date_key = date_map.get(
                        row.InvoiceDate.strftime("%Y-%m-%d")
                    )

                facts.append((
                    str(row.InvoiceNo),
                    date_key,
                    customer_map.get(str(row.CustomerID)),
                    product_map.get(str(row.StockCode)),
                    city_map.get(str(row.City)),
                    float(row.Quantity),
                    float(row.UnitPrice),
                    float(row.Sales)
                ))

            conn.executemany("""
                INSERT INTO FactSales
                (InvoiceNo, DateKey, CustomerKey, ProductKey,
                 CityKey, Quantity, UnitPrice, Sales)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, facts)

        conn.commit()


# --------------------------------------------------
# 4. LOAD WAREHOUSE DATA
# --------------------------------------------------

def load_warehouse():
    query = """
        SELECT
            f.InvoiceNo,
            d.FullDate AS InvoiceDate,
            d.Month,
            d.MonthName,
            d.Quarter,
            d.Year,
            c.CustomerID,
            ci.City,
            p.StockCode,
            p.Description,
            f.Quantity,
            f.UnitPrice,
            f.Sales
        FROM FactSales f
        LEFT JOIN DimDate d ON f.DateKey = d.DateKey
        LEFT JOIN DimCustomer c
            ON f.CustomerKey = c.CustomerKey
        LEFT JOIN DimProduct p ON f.ProductKey = p.ProductKey
        LEFT JOIN DimCity ci ON f.CityKey = ci.CityKey
    """

    with sqlite3.connect(DB_FILE) as conn:
        return pd.read_sql_query(query, conn)


# --------------------------------------------------
# 5. DASHBOARD HEADER
# --------------------------------------------------

st.title("🛍️ Smart Retail Analytics")
st.subheader("Customer Insights and Business Intelligence")
st.write(
    "Analyze retail sales, products, customers, "
    "and business trends."
)

try:
    df = load_retail_data()
    create_warehouse(df)

    # IMPORTANT: Define warehouse_df before any analysis.
    warehouse_df = load_warehouse()

except Exception as error:
    st.error(f"Unable to load the project data: {error}")
    st.stop()


# --------------------------------------------------
# 6. DATASET PREVIEW AND INFORMATION
# --------------------------------------------------

st.header("📋 Dataset Preview")
st.dataframe(df.head(20), use_container_width=True)

st.header("📌 Dataset Information")

col1, col2 = st.columns(2)
col1.metric("Total Records", f"{len(df):,}")
col2.metric("Number of Columns", len(df.columns))

st.write("**Columns:**", ", ".join(df.columns))

st.download_button(
    "⬇️ Download Retail Dataset",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="retail_transactions.csv",
    mime="text/csv"
)


# --------------------------------------------------
# 7. RETAIL SUMMARY
# --------------------------------------------------

st.header("💰 Retail Summary")

c1, c2, c3 = st.columns(3)

c1.metric(
    "Total Transactions",
    f"{df['InvoiceNo'].nunique():,}"
)
c2.metric(
    "Total Sales",
    f"{df['Sales'].sum():,.2f}"
)
c3.metric(
    "Total Quantity",
    f"{df['Quantity'].sum():,.0f}"
)

left, right = st.columns(2)

with left:
    city_sales = (
        df.groupby("City", as_index=False)["Sales"]
        .sum()
        .sort_values("Sales", ascending=False)
    )

    st.subheader("Sales by City")
    st.plotly_chart(
        px.bar(
            city_sales, x="City", y="Sales",
            title="Total Sales by City"
        ),
        use_container_width=True
    )

with right:
    product_sales = (
        df.groupby("Description", as_index=False)["Sales"]
        .sum()
        .nlargest(10, "Sales")
    )

    st.subheader("Top 10 Products")
    st.plotly_chart(
        px.bar(
            product_sales,
            x="Sales",
            y="Description",
            orientation="h",
            title="Top Products by Sales"
        ),
        use_container_width=True
    )


# --------------------------------------------------
# 8. DATA WAREHOUSE AND OLAP
# --------------------------------------------------

st.header("📊 Data Warehouse and OLAP Analysis")

st.success(
    f"Warehouse ready: {len(warehouse_df):,} fact records"
)

if not warehouse_df.empty:
    selected_city = st.selectbox(
        "Slice: Select a city",
        sorted(warehouse_df["City"].dropna().unique())
    )

    city_df = warehouse_df[
        warehouse_df["City"] == selected_city
    ]

    st.subheader("Slice — Sales for Selected City")
    st.dataframe(
        city_df.head(100),
        use_container_width=True
    )

    available_products = sorted(
        warehouse_df["Description"].dropna().unique()
    )

    selected_products = st.multiselect(
        "Dice: Select products",
        available_products,
        default=available_products[:2]
    )

    diced_df = warehouse_df[
        (warehouse_df["City"] == selected_city)
        & (warehouse_df["Description"].isin(selected_products))
    ]

    st.subheader("Dice — City and Product Analysis")
    st.dataframe(diced_df.head(100), use_container_width=True)

    monthly_df = (
        warehouse_df.dropna(subset=["InvoiceDate"])
        .groupby("MonthName", as_index=False)["Sales"]
        .sum()
    )

    st.subheader("Roll-up — Monthly Sales")
    st.plotly_chart(
        px.bar(
            monthly_df, x="MonthName", y="Sales",
            title="Monthly Sales Summary"
        ),
        use_container_width=True
    )

    if warehouse_df["InvoiceDate"].notna().any():
        available_dates = sorted(
            warehouse_df["InvoiceDate"].dropna().unique()
        )
        selected_date = st.selectbox(
            "Drill-down: Select a date",
            available_dates
        )

        daily_df = warehouse_df[
            warehouse_df["InvoiceDate"] == selected_date
        ]

        st.write(f"Transactions for {selected_date}")
        st.dataframe(daily_df, use_container_width=True)


# --------------------------------------------------
# 9. CUSTOMER SEGMENTATION USING K-MEANS
# --------------------------------------------------

st.header("👥 Customer Segmentation using K-Means")

customer_df = (
    warehouse_df.groupby("CustomerID", as_index=False)
    .agg(
        TotalSales=("Sales", "sum"),
        TotalQuantity=("Quantity", "sum"),
        TotalOrders=("InvoiceNo", "nunique")
    )
)

if len(customer_df) >= 2:
    features = [
        "TotalSales", "TotalQuantity", "TotalOrders"
    ]

    X = customer_df[features].replace(
        [float("inf"), float("-inf")], 0
    ).fillna(0)

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    max_clusters = min(5, len(customer_df))
    n_clusters = st.slider(
        "Number of customer groups",
        min_value=2,
        max_value=max_clusters,
        value=min(3, max_clusters)
    )

    model = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=10
    )

    customer_df["Segment"] = (
        model.fit_predict(X_scaled).astype(str)
    )

    st.plotly_chart(
        px.scatter(
            customer_df,
            x="TotalSales",
            y="TotalQuantity",
            color="Segment",
            hover_data=["CustomerID", "TotalOrders"],
            title="Customer Segmentation"
        ),
        use_container_width=True
    )

    st.subheader("Customer Segment Summary")
    st.dataframe(
        customer_df.groupby("Segment", as_index=False).agg(
            Customers=("CustomerID", "count"),
            AverageSales=("TotalSales", "mean"),
            AverageQuantity=("TotalQuantity", "mean"),
            AverageOrders=("TotalOrders", "mean")
        ).round(2),
        use_container_width=True
    )

    st.download_button(
        "⬇️ Download Customer Segments",
        data=customer_df.to_csv(index=False).encode("utf-8"),
        file_name="customer_segments.csv",
        mime="text/csv"
    )
else:
    st.warning("At least two customers are needed for clustering.")


# --------------------------------------------------
# 10. MARKET BASKET ANALYSIS USING APRIORI
# --------------------------------------------------

st.header("🛒 Market Basket Analysis using Apriori")

st.write(
    "Find products that frequently appear in the same invoice."
)

basket_df = df[
    (df["Quantity"] > 0)
    & (df["InvoiceNo"] != "Unknown")
].copy()

if not basket_df.empty:
    basket = pd.crosstab(
        basket_df["InvoiceNo"],
        basket_df["Description"]
    )
    basket = basket.gt(0)

    # Apriori needs more than one product to find associations.
    if basket.shape[1] >= 2:
        support = st.slider(
            "Minimum support",
            min_value=0.01,
            max_value=0.50,
            value=0.05,
            step=0.01
        )

        confidence = st.slider(
            "Minimum confidence",
            min_value=0.10,
            max_value=1.00,
            value=0.50,
            step=0.05
        )

        if st.button("Run Market Basket Analysis"):
            try:
                frequent_itemsets = apriori(
                    basket,
                    min_support=support,
                    use_colnames=True
                )

                if frequent_itemsets.empty:
                    st.info(
                        "No frequent product combinations found. "
                        "Try lowering minimum support."
                    )
                else:
                    st.subheader("Frequent Itemsets")

                    display_items = frequent_itemsets.copy()
                    display_items["itemsets"] = (
                        display_items["itemsets"]
                        .apply(lambda items: ", ".join(sorted(items)))
                    )

                    st.dataframe(
                        display_items.sort_values(
                            "support", ascending=False
                        ),
                        use_container_width=True
                    )

                    rules = association_rules(
                        frequent_itemsets,
                        metric="confidence",
                        min_threshold=confidence
                    )

                    if rules.empty:
                        st.info(
                            "No association rules matched the "
                            "confidence threshold. Try lowering it."
                        )
                    else:
                        rules["antecedents"] = (
                            rules["antecedents"]
                            .apply(lambda items: ", ".join(sorted(items)))
                        )
                        rules["consequents"] = (
                            rules["consequents"]
                            .apply(lambda items: ", ".join(sorted(items)))
                        )

                        st.subheader("Product Association Rules")
                        st.dataframe(
                            rules[
                                [
                                    "antecedents",
                                    "consequents",
                                    "support",
                                    "confidence",
                                    "lift"
                                ]
                            ].sort_values(
                                "confidence", ascending=False
                            ).round(3),
                            use_container_width=True
                        )

            except Exception as error:
                st.error(
                    f"Market basket analysis failed: {error}"
                )
    else:
        st.info(
            "At least two distinct products are needed "
            "for market basket analysis."
        )
else:
    st.info("No positive-quantity transactions are available.")


# --------------------------------------------------
# 11. FOOTER
# --------------------------------------------------

st.divider()
st.caption(
    "Smart Retail Analytics and Customer Insights System | "
    "Data Warehousing and Data Mining Academic Project"
)
