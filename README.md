# Smart Retail Analytics and Customer Insights System

A Data Warehousing and Data Mining project that analyzes retail transactions to discover sales trends, understand customer behavior, identify popular products, and support data-driven business decisions.

## 📌 Project Overview

The Smart Retail Analytics and Customer Insights System is designed to transform retail transaction data into meaningful insights. It uses data warehousing concepts, data visualization, machine learning, and market basket analysis to help understand business performance.

## ✨ Features

- **Sales Analysis:** Analyze sales, quantities, and transaction records.
- **Interactive Dashboard:** View data summaries and charts.
- **Data Warehouse:** Organize retail data using fact and dimension tables.
- **OLAP Operations:** Perform slice, dice, roll-up, and drill-down analysis.
- **Customer Segmentation:** Group customers using the K-Means clustering algorithm.
- **Market Basket Analysis:** Discover product associations using the Apriori algorithm.
- **Data Export:** Download data for further analysis.

## 🛠️ Technologies Used

- Python
- Streamlit
- Pandas
- NumPy
- Plotly
- Scikit-learn
- MLxtend
- SQLite
- SQL

## 📂 Project Structure

```text
SmartRetailAnalytics/
├── app.py
├── create_database.py
├── schema.sql
├── requirements.txt
├── data/
│   └── retail_transactions.csv
└── README.md
```

## ⚙️ Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/khushimsingh-ship-it/SmartRetailAnalytics.git
```

### 2. Open the project folder

```bash
cd SmartRetailAnalytics
```

### 3. Create a virtual environment

```bash
python -m venv .venv
```

### 4. Activate the environment on Windows

```powershell
.\.venv\Scripts\Activate.ps1
```

### 5. Install the required libraries

```bash
python -m pip install -r requirements.txt
```

### 6. Create the retail data warehouse

```bash
python create_database.py
```

### 7. Run the Streamlit dashboard

```bash
python -m streamlit run app.py
```

The dashboard should open in your browser. If it does not, open the local URL displayed in the terminal.

## 📊 Data Warehousing Concepts

The project uses a dimensional data model containing:

- **DimDate:** Date-related information.
- **DimCustomer:** Customer details.
- **DimProduct:** Product information.
- **DimCity:** City information.
- **FactSales:** Transaction quantities, prices, and sales values.

The warehouse supports analytical queries and OLAP operations for exploring retail performance.

## 🤖 Data Mining Techniques

### Customer Segmentation

K-Means clustering groups customers based on transaction-related features such as total sales, quantities purchased, and order counts.

### Market Basket Analysis

The Apriori algorithm identifies frequently purchased product combinations and association rules.

## 🎯 Project Objectives

- Understand retail sales performance.
- Identify popular products and customer purchasing patterns.
- Apply data warehousing and OLAP techniques.
- Explore customer segmentation using machine learning.
- Discover product associations to support business decisions.

## 👩‍💻 Author

**Khushi Singh**

GitHub: [khushimsingh-ship-it](https://github.com/khushimsingh-ship-it)

## 📄 License

This project was developed for educational purposes as part of a Data Warehousing and Data Mining academic project.
