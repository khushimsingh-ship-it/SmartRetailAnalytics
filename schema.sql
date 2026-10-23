
CREATE TABLE IF NOT EXISTS DimDate (
    DateKey INTEGER PRIMARY KEY,
    FullDate TEXT,
    Month INTEGER,
    MonthName TEXT,
    Quarter TEXT,
    Year INTEGER
);

CREATE TABLE IF NOT EXISTS DimCustomer (
    CustomerKey INTEGER PRIMARY KEY,
    CustomerID INTEGER UNIQUE
);

CREATE TABLE IF NOT EXISTS DimProduct (
    ProductKey INTEGER PRIMARY KEY,
    StockCode TEXT UNIQUE,
    Description TEXT
);

CREATE TABLE IF NOT EXISTS DimCity (
    CityKey INTEGER PRIMARY KEY,
    City TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS FactSales (
    SalesKey INTEGER PRIMARY KEY AUTOINCREMENT,
    InvoiceNo TEXT,
    DateKey INTEGER,
    CustomerKey INTEGER,
    ProductKey INTEGER,
    CityKey INTEGER,
    Quantity INTEGER,
    UnitPrice REAL,
    Sales REAL,
    FOREIGN KEY (DateKey) REFERENCES DimDate(DateKey),
    FOREIGN KEY (CustomerKey) REFERENCES DimCustomer(CustomerKey),
    FOREIGN KEY (ProductKey) REFERENCES DimProduct(ProductKey),
    FOREIGN KEY (CityKey) REFERENCES DimCity(CityKey)
);
