# database.py

import sqlite3
import json

# --- Database Connection and Setup ---
def get_db_connection():
    """Creates a connection to the SQLite database."""
    conn = sqlite3.connect('history.db')
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

def create_table():
    """Creates the 'analyses' table if it doesn't already exist."""
    conn = get_db_connection()
    conn.execute('''
        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            summary TEXT NOT NULL,
            tasks TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# --- Database Functions ---
def insert_analysis(summary, tasks):
    """Inserts a new analysis record into the database."""
    tasks_json = json.dumps(tasks)  # Convert the list of tasks to a JSON string
    conn = get_db_connection()
    conn.execute('INSERT INTO analyses (summary, tasks) VALUES (?, ?)', (summary, tasks_json))
    conn.commit()
    conn.close()

def get_all_analyses():
    """Retrieves all past analyses from the database, ordered by newest first."""
    conn = get_db_connection()
    analyses = conn.execute('SELECT * FROM analyses ORDER BY created_at DESC').fetchall()
    conn.close()
    return analyses