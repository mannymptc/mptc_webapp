import pyodbc

def connect_db():
    connection_string = (
        "Driver={ODBC Driver 17 for SQL Server};"
        "Server=mptcecommerce-sql-server.database.windows.net;"
        "Database=mptcecommerce-db;"
        "Uid=mptcadmin;"
        "Pwd=Mptc@2025;"
        "Encrypt=yes;"
        "TrustServerCertificate=no;"
        "Connection Timeout=30;"
    )

    return pyodbc.connect(connection_string)
