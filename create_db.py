"""
Script to create the campconnect MySQL database.
Run once with: .venv\Scripts\python.exe create_db.py
"""
import pymysql

try:
    conn = pymysql.connect(
        host="127.0.0.1",
        port=3306,
        user="root",
        password="",          # Root has no password on this MySQL install
        charset="utf8mb4",
    )
    cursor = conn.cursor()
    cursor.execute(
        "CREATE DATABASE IF NOT EXISTS campconnect "
        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    )
    cursor.execute("SHOW DATABASES LIKE 'campconnect'")
    result = cursor.fetchone()
    conn.commit()
    conn.close()
    print(f"SUCCESS: Database campconnect is ready: {result}")
except Exception as e:
    print(f"ERROR: {e}")
