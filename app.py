
import streamlit as st
import pandas as pd
import plotly.express as px
from pathlib import Path

# Page settings
st.set_page_config(
    page_title="Smart Retail Analytics",
    page_icon="🛍️",
    layout="wide"
)

# Find the dataset
DATA_FILE = Path(__file__).parent / "data" / "retail_transactions.csv"

st.title("🛍️ Smart Retail Analytics")
st.subheader("Customer Insights and Business Intelligence")
st.write("Analyze retail sales, products, customers, and business trends.")

# Load the dataset
if not DATA_FILE.exists():
    st.error("Dataset not found: data/retail_transactions.csv")
    st.info("Please check that the CSV file exists inside the data folder.")
    st.stop()

df = pd.read_csv(DATA_FILE)

# Clean column names
df.columns = df.columns.str.strip()

# Show dataset details
st.success("Retail dataset loaded successfully!")

st.write("### Dataset Preview")
st.dataframe(df.head(10), use_container_width=True)

st.write("### Dataset Information")
st.write(f"Total records: {len(df):,}")
st.write("Columns:", ", ".join(df.columns))

# Try to identify common column names
columns = {column.lower().strip(): column for column in df.columns}

sales_col = next(
    (columns[name] for name in ["sales", "total_sales", "amount", "revenue", "total"]
     if name in columns),
    None
)

quantity_col = next(
    (columns[name] for name in ["quantity", "qty"]
     if name in columns),
    None
)

product_col = next(
    (columns[name] for name in ["product", "product_name", "item"]
     if name in columns),
    None
)

# Summary cards
st.write("### Retail Summary")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Transactions", f"{len(df):,}")

with col2:
    st.metric(
        "Total Sales",
        f"{df[sales_col].sum():,.2f}" if sales_col else "Column not found"
    )

with col3:
    st.metric(
        "Total Quantity",
        f"{df[quantity_col].sum():,.0f}" if quantity_col else "Column not found"
    )

# Product analysis
if product_col:
    st.write("### Product Analysis")

    if quantity_col:
        product_sales = (
            df.groupby(product_col)[quantity_col]
            .sum()
            .reset_index()
            .sort_values(quantity_col, ascending=False)
            .head(10)
        )

        fig = px.bar(
            product_sales,
            x=product_col,
            y=quantity_col,
            title="Top Products by Quantity Sold",
            labels={
                product_col: "Product",
                quantity_col: "Quantity Sold"
            }
        )

        st.plotly_chart(fig, use_container_width=True)

# Sales distribution
if sales_col:
    st.write("### Sales Distribution")

    fig = px.histogram(
        df,
        x=sales_col,
        title="Distribution of Sales Values",
        labels={sales_col: "Sales Amount"}
    )

    st.plotly_chart(fig, use_container_width=True)

# Download dataset
st.write("### Download Data")

csv_data = df.to_csv(index=False).encode("utf-8")

st.download_button(
    label="Download Retail Dataset",
    data=csv_data,
    file_name="retail_transactions.csv",
    mime="text/csv"
)

st.caption("Smart Retail Analytics and Customer Insights System")

# ==========================================
# DATA WAREHOUSE AND OLAP ANALYSIS
# ==========================================

import sqlite3

st.divider()
st.header("📊 Data Warehouse and OLAP Analysis")

DB_FILE = Path(__file__).parent / "retail_warehouse.db"

if DB_FILE.exists():
    with sqlite3.connect(DB_FILE) as connection:

        # Read sales data from the warehouse
        warehouse_df = pd.read_sql_query("""
            SELECT
                f.InvoiceNo,
                d.FullDate,
                d.Month,
                d.MonthName,
                d.Year,
                c.CustomerID,
                ci.City,
                p.Description AS Product,
                f.Quantity,
                f.UnitPrice,
                f.Sales
            FROM FactSales f
            JOIN DimDate d ON f.DateKey = d.DateKey
            JOIN DimCustomer c ON f.CustomerKey = c.CustomerKey
            JOIN DimProduct p ON f.ProductKey = p.ProductKey
            JOIN DimCity ci ON f.CityKey = ci.CityKey
        """, connection)

    st.success("Connected to SQLite data warehouse!")

    st.subheader("1. Slice — Sales by City")

    selected_city = st.selectbox(
        "Select a city",
        sorted(warehouse_df["City"].dropna().unique())
    )

    slice_df = warehouse_df[warehouse_df["City"] == selected_city]

    st.metric("Sales in Selected City", f"₹{slice_df['Sales'].sum():,.2f}")
    st.dataframe(slice_df.head(20), use_container_width=True)

    st.subheader("2. Dice — Filter by City and Product")

    city_options = sorted(warehouse_df["City"].dropna().unique())
    product_options = sorted(warehouse_df["Product"].dropna().unique())

    selected_cities = st.multiselect(
        "Choose cities",
        city_options,
        default=city_options
    )

    selected_products = st.multiselect(
        "Choose products",
        product_options,
        default=product_options
    )

    dice_df = warehouse_df[
        warehouse_df["City"].isin(selected_cities)
        & warehouse_df["Product"].isin(selected_products)
    ]

    st.write(f"Matching sales records: {len(dice_df):,}")
    st.metric("Filtered Sales", f"₹{dice_df['Sales'].sum():,.2f}")
    st.dataframe(dice_df.head(20), use_container_width=True)

    st.subheader("3. Roll-up — Monthly Sales Summary")

    monthly_df = (
        warehouse_df.groupby(["Year", "Month", "MonthName"], as_index=False)
        ["Sales"].sum()
        .sort_values(["Year", "Month"])
    )

    fig = px.bar(
        monthly_df,
        x="MonthName",
        y="Sales",
        color="Year",
        title="Monthly Sales Summary",
        labels={"MonthName": "Month", "Sales": "Sales (₹)"}
    )

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(monthly_df, use_container_width=True)

    st.subheader("4. Drill-down — Sales by Date")

    selected_month = st.selectbox(
        "Choose a month to inspect",
        sorted(warehouse_df["FullDate"].str[:7].unique())
    )

    drill_df = warehouse_df[
        warehouse_df["FullDate"].str.startswith(selected_month)
    ]

    daily_df = (
        drill_df.groupby("FullDate", as_index=False)["Sales"]
        .sum()
        .sort_values("FullDate")
    )

    fig = px.line(
        daily_df,
        x="FullDate",
        y="Sales",
        markers=True,
        title=f"Daily Sales for {selected_month}"
    )

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(daily_df, use_container_width=True)

else:
    st.warning("Database not found. Run python create_database.py first.")

# ==========================================
# CUSTOMER SEGMENTATION USING K-MEANS
# ==========================================

from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from mlxtend.frequent_patterns import apriori, association_rules

st.divider()
st.header("👥 Customer Segmentation using K-Means")

# Prepare customer purchase data
customer_df = warehouse_df.groupby("CustomerID", as_index=False).agg(
    TotalSales=("Sales", "sum"),
    TotalQuantity=("Quantity", "sum"),
    TotalOrders=("InvoiceNo", "nunique")
)

if len(customer_df) >= 2:
    max_clusters = min(4, len(customer_df))

    n_clusters = st.slider(
        "Number of customer groups",
        min_value=2,
        max_value=max_clusters,
        value=min(3, max_clusters)
    )

    features = customer_df[
        ["TotalSales", "TotalQuantity", "TotalOrders"]
    ]

    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)

    model = KMeans(
        n_clusters=n_clusters,
        random_state=42,
        n_init=10
    )

    customer_df["CustomerSegment"] = model.fit_predict(scaled_features)

    st.write("Each customer is assigned to a segment based on sales, quantity, and orders.")

    fig = px.scatter(
        customer_df,
        x="TotalSales",
        y="TotalOrders",
        color=customer_df["CustomerSegment"].astype(str),
        size="TotalQuantity",
        hover_data=["CustomerID"],
        title="Customer Segments",
        labels={
            "TotalSales": "Total Customer Sales (₹)",
            "TotalOrders": "Number of Orders",
            "color": "Segment"
        }
    )

    st.plotly_chart(fig, use_container_width=True)
    st.dataframe(customer_df, use_container_width=True)

    st.subheader("Customer Segment Summary")

    segment_summary = customer_df.groupby(
        "CustomerSegment", as_index=False
    ).agg(
        Customers=("CustomerID", "count"),
        AverageSales=("TotalSales", "mean"),
        AverageOrders=("TotalOrders", "mean")
    )

    st.dataframe(segment_summary, use_container_width=True)

else:
    st.warning("At least two customers are needed for clustering.")


# ==========================================
# MARKET BASKET ANALYSIS USING APRIORI
# ==========================================

st.divider()
st.header("🛒 Market Basket Analysis using Apriori")

st.write(
    "This analysis identifies products that appear together "
    "in the same invoice."
)

min_support = st.slider(
    "Minimum support",
    min_value=0.01,
    max_value=0.50,
    value=0.05,
    step=0.01
)

min_confidence = st.slider(
    "Minimum confidence",
    min_value=0.10,
    max_value=1.00,
    value=0.30,
    step=0.05
)

# Create invoice-product transactions
basket_source = warehouse_df[
    ["InvoiceNo", "Product"]
].dropna().drop_duplicates()

basket = pd.crosstab(
    basket_source["InvoiceNo"],
    basket_source["Product"]
).gt(0)

if basket.shape[0] > 0 and basket.shape[1] >= 2:
    frequent_items = apriori(
        basket,
        min_support=min_support,
        use_colnames=True
    )

    if not frequent_items.empty:
        rules = association_rules(
            frequent_items,
            metric="confidence",
            min_threshold=min_confidence
        )

        if not rules.empty:
            rules["Antecedents"] = rules["antecedents"].apply(
                lambda items: ", ".join(sorted(items))
            )

            rules["Consequents"] = rules["consequents"].apply(
                lambda items: ", ".join(sorted(items))
            )

            display_rules = rules[
                [
                    "Antecedents",
                    "Consequents",
                    "support",
                    "confidence",
                    "lift"
                ]
            ].sort_values("lift", ascending=False)

            st.success(f"Found {len(display_rules)} association rules.")

            st.dataframe(
                display_rules.round(3),
                use_container_width=True
            )

            st.caption(
                "Support = frequency of the combination; "
                "confidence = how often the consequent appears "
                "when the antecedent appears; "
                "lift > 1 indicates a positive association."
            )

        else:
            st.info(
                "No rules found with these settings. "
                "Try lowering minimum support or confidence."
            )

    else:
        st.info(
            "No frequent product combinations found. "
            "Try lowering minimum support."
        )

else:
    st.warning(
        "Not enough invoice or product data for market basket analysis."
    )
