import sqlite3
import os

db_path = "data/capture.db"
query = "SELECT * FROM messages"
sql = input("set the sql name file")     
sql_query_path = "scriptsSQL/" + sql + ".sql"

def run_query():
    if not os.path.exists(db_path):
        print("db_path not exist")
        return

    conn= None

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        with open(sql_query_path, "r", encoding= "utf-8") as f:
             content = f.read()
             

        cursor.execute(str(content))
        results = cursor.fetchall()

        print(results)

    finally:
        if conn:
            conn.close

if __name__ == "__main__":
        run_query()   