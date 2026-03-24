"""
db.py — Database Layer
======================
PURPOSE:
    This file does ONE job: read all the JSONL files from the data folder
    and load them into a SQLite database. SQLite is a simple file-based
    database — no server needed, no installation needed, it's built into Python.

WHY SQLite?
    - Zero configuration — just a single .db file on disk
    - Built into Python (no pip install needed)
    - Perfect for this project size (~18,000 records total)
    - The LLM will generate SQL queries that run against this database

HOW IT WORKS:
    1. We loop through each subfolder in the data/ directory
    2. Each subfolder = one entity type (e.g. sales_order_headers)
    3. We read all .jsonl files inside that subfolder
    4. We use pandas to load the records and write them as a SQL table
    5. The table name = the folder name (e.g. "sales_order_headers")
"""

import os
import json
import glob
import sqlite3
import pandas as pd

# ─── CONFIGURATION ────────────────────────────────────────────────────────────

# Path to your data folder (relative to this file)
# When you run this, make sure your 'data' folder is inside 'backend/'
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")

# The SQLite database file will be created here
DB_PATH = os.path.join(os.path.dirname(__file__), "sap_o2c.db")


# ─── MAIN LOADER FUNCTION ─────────────────────────────────────────────────────

def load_all_data():
    """
    Reads every JSONL folder in DATA_DIR and loads it into SQLite.

    Each folder becomes one table.
    Each JSONL file inside the folder = rows in that table.
    Multiple JSONL files in same folder are combined into one table.

    Returns: sqlite3 connection object
    """

    # Connect to SQLite — creates the file if it doesn't exist
    conn = sqlite3.connect(DB_PATH)
    print(f"Connected to database: {DB_PATH}")

    # Get list of all subfolders in data/
    # Each subfolder = one entity type
    folders = sorted([
        f for f in os.listdir(DATA_DIR)
        if os.path.isdir(os.path.join(DATA_DIR, f))
    ])

    if not folders:
        print(f"ERROR: No folders found in {DATA_DIR}")
        print("Make sure you copied the data files into backend/data/")
        return conn

    print(f"\nFound {len(folders)} entity folders to load...\n")

    for folder_name in folders:
        folder_path = os.path.join(DATA_DIR, folder_name)

        # Find all .jsonl files inside this folder
        jsonl_files = glob.glob(os.path.join(folder_path, "*.jsonl"))

        if not jsonl_files:
            print(f"  SKIP {folder_name} — no .jsonl files found")
            continue

        # Read ALL jsonl files in this folder into one list of records
        all_records = []
        for filepath in jsonl_files:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:  # skip empty lines
                        try:
                            record = json.loads(line)
                            all_records.append(record)
                        except json.JSONDecodeError as e:
                            print(f"  WARNING: Skipping bad line in {filepath}: {e}")

        if not all_records:
            print(f"  SKIP {folder_name} — no valid records")
            continue

        # Convert list of dicts → pandas DataFrame
        # pandas handles mixed types, missing fields, etc. automatically
        df = pd.DataFrame(all_records)

        # Clean up: convert dict/list values to strings
        # (Some fields like 'creationTime' are nested objects e.g. {"hours":11,"minutes":31})
        for col in df.columns:
            df[col] = df[col].apply(
                lambda x: json.dumps(x) if isinstance(x, (dict, list)) else x
            )

        # Write to SQLite
        # Table name = folder name (e.g. "sales_order_headers")
        # if_exists="replace" = drop and recreate the table each time
        # This means every time you run db.py, the data is freshly loaded
        df.to_sql(
            name=folder_name,  # table name in SQLite
            con=conn,  # database connection
            if_exists="replace",  # overwrite if table already exists
            index=False  # don't write DataFrame row numbers as a column
        )

        print(f"  ✅ {folder_name}: {len(df)} records loaded")

    print(f"\nAll data loaded successfully into: {DB_PATH}")
    return conn


def get_connection():
    """
    Returns a connection to the existing SQLite database.
    Used by other files (main.py, graph.py) to run queries.

    If the database doesn't exist yet, it loads the data first.
    """
    if not os.path.exists(DB_PATH):
        print("Database not found — loading data for the first time...")
        return load_all_data()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # makes rows behave like dicts
    return conn


def get_schema_description():
    """
    Returns a text description of all tables and their columns.

    WHY THIS EXISTS:
        The LLM needs to know the database structure to generate correct SQL.
        We pass this description in the system prompt so the LLM knows
        exactly what tables and columns exist.

    Example output:
        Table: sales_order_headers
          Columns: salesOrder, salesOrderType, soldToParty, totalNetAmount, ...
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Get list of all tables in the database
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = [row[0] for row in cursor.fetchall()]

    schema_lines = ["DATABASE SCHEMA (SQLite)\n"]
    schema_lines.append("=" * 50)

    for table in tables:
        # Get column info for each table
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        col_names = [col[1] for col in columns]  # col[1] = column name

        # Get row count
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        count = cursor.fetchone()[0]

        schema_lines.append(f"\nTable: {table} ({count} rows)")
        schema_lines.append(f"  Columns: {', '.join(col_names)}")

    conn.close()
    return "\n".join(schema_lines)


def run_query(sql: str):
    """
    Executes a SQL query and returns results as a list of dicts.

    WHY THIS EXISTS:
        When the LLM generates a SQL query, we run it here and
        return the results back to the LLM to format as natural language.

    Args:
        sql: A valid SQLite SQL string

    Returns:
        List of dicts, e.g. [{"salesOrder": "1001", "totalNetAmount": "500.00"}, ...]
        Or raises an exception if the SQL is invalid.
    """
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        rows = cursor.fetchall()

        # Get column names from cursor description
        if cursor.description:
            col_names = [desc[0] for desc in cursor.description]
            # Convert each row to a dict
            results = [dict(zip(col_names, row)) for row in rows]
        else:
            results = []

        return results

    except Exception as e:
        raise Exception(f"SQL Error: {str(e)}\nQuery was: {sql}")
    finally:
        conn.close()


# ─── RUN DIRECTLY ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    """
    When you run: python db.py
    It will load all data into the database and print the schema.

    Run this ONCE before starting the server.
    """
    print("=" * 60)
    print("SAP O2C Data Loader")
    print("=" * 60)

    # Load all data
    conn = load_all_data()
    conn.close()

    # Print the schema so you can verify everything loaded correctly
    print("\n" + "=" * 60)
    print("DATABASE SCHEMA SUMMARY")
    print("=" * 60)
    print(get_schema_description())
