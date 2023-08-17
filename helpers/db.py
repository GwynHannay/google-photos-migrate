import os
import sqlite3
from photohunter import db_file

sql_dir = 'helpers/sql'

table_scripts = [
    "create_google_photos",
    "create_duplicate_photos",
    "create_google_duplicates",
    "create_deleted_photos",
    "create_duplicate_dupes"
]



def read_sql_file(sql_file: str) -> str:
    query = str
    sql_file = ''.join([sql_file, '.sql'])
    with open(os.path.join(sql_dir, sql_file)) as s:
        query = s.read()
    return query


def create_db():
    """Create SQLite database with tables using SQL file.

    Raises:
        Exception: General exception with error message.
    """
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        for script in table_scripts:
            query = read_sql_file(script)

            cursor.execute(query)
            conn.commit()

        cursor.close()
        conn.close()
    except Exception as e:
        raise Exception(f"Could not create db and tables: {e}")


def insert_many_records(records: tuple):
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        query = read_sql_file(records[0])

        cursor.executemany(query, records[1])
        conn.commit()
        print("Total", cursor.rowcount, f"records inserted: {records[0]}")
        conn.commit()

        cursor.close()
        conn.close()
    except sqlite3.IntegrityError as ie:
        print(f"Integrity error on insert: {records} {ie}")
    except Exception as e:
        raise Exception(f"Could not insert records: {records} {e}")


def get_results(filename: str, batch_size: int = 300) -> list:
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        query = read_sql_file(filename)

        cursor.execute(query)
        matches = cursor.fetchmany(batch_size)

        cursor.close()
        conn.close()

        return matches
    except Exception as e:
        raise Exception(f"Could not query database: {filename} {e}")


def get_results_with_single_val(records: tuple) -> list:
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        query = read_sql_file(records[0])
        cursor.execute(query, (records[1],))
        matches = cursor.fetchall()

        cursor.close()
        conn.close()

        return matches
    except Exception as e:
        raise Exception(f"Could not query database: {records} {e}")


def execute_query(filename: str):
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        query = read_sql_file(filename)

        cursor.execute(query)
        conn.commit()
        print("Total", cursor.rowcount, f"records impacted by script: {filename}")

        cursor.close()
        conn.close()
    except Exception as e:
        raise Exception(f"Could not execute query: {filename} {e}")


def execute_query_with_list(records: tuple):
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        list_placeholders = ','.join(['?'] * len(records[1]))
        query = read_sql_file(records[0]) % list_placeholders

        cursor.execute(query, records[1])
        conn.commit()
        print("Total", cursor.rowcount, f"records impacted by script: {records[0]}")

        cursor.close()
        conn.close()
    except Exception as e:
        raise Exception(f"Could not execute query with list: {records} {e}")


def execute_query_with_multiple_vals(records: tuple):
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        query = read_sql_file(records[0])

        cursor.executemany(query, records[1])
        conn.commit()
        print("Total", cursor.rowcount, f"records impacted by script: {records[0]}")

        cursor.close()
        conn.close()
    except Exception as e:
        raise Exception(f"Could not execute query with values: {records} {e}")
