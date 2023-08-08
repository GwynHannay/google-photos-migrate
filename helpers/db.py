import os
import sqlite3
from photohunter import db_file


db_file = os.path.join('..', db_file)

def create_db():
    """Create SQLite database with tables for Google Photos and duplicates.

    Raises:
        Exception: General exception with error message.
    """
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        main_table_query = """CREATE TABLE google_photos (
          id INTEGER PRIMARY KEY,
          distinct_name TEXT NOT NULL,
          original_name TEXT NOT NULL,
          filepath TEXT NOT NULL UNIQUE,
          size INTEGER,
          created_date TEXT
        );"""
        cursor.execute(main_table_query)
        conn.commit()

        duplicates_table_query = """CREATE TABLE duplicate_photos (
          id INTEGER PRIMARY KEY,
          duplicate_filepath TEXT NOT NULL,
          size INTEGER,
          created_date TEXT
        );"""
        cursor.execute(duplicates_table_query)
        conn.commit()

        m2m_query = """CREATE TABLE google_duplicates (
            id INTEGER PRIMARY KEY,
            google_photo_id INTEGER NOT NULL,
            duplicate_photo_id INTEGER NOT NULL,
            similarity_score TEXT NOT NULL,
            new_path TEXT,
            completed TEXT,
          FOREIGN KEY(google_photo_id) REFERENCES google_photos(id),
          FOREIGN KEY(duplicate_photo_id) REFERENCES duplicate_photos(id),
          CONSTRAINT unique_matches UNIQUE(google_photo_id, duplicate_photo_id)
        );"""
        cursor.execute(m2m_query)
        conn.commit()

        cursor.close()
        conn.close()
    except Exception as e:
        raise Exception(f"Could not create db and tables: {e}")


def insert_original_records(records: list):
    """Inserts multiple records of original Google Photos.

    Args:
        records (list): Google Photo information such as distinct filename (having 
            removed rounded brackets), original filename, filepath on system, file 
            size and the extracted original datetime.

    Raises:
        Exception: General exception.
    """
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        insert_query = """INSERT INTO google_photos
          (distinct_name, original_name, filepath, size)
          VALUES (?, ?, ?, ?);"""

        cursor.executemany(insert_query, records)
        conn.commit()
        print("Total", cursor.rowcount, "records inserted into google_photos")
        conn.commit()

        cursor.close()
        conn.close()
    except Exception as e:
        raise Exception(f"Could not insert records into google_photos: {e}")


def insert_duplicate_records(records: list):
    for record in records:
        duplicate_filepath = record[0]
        file_size = record[1]
        matches = record[2]

        duplicate_id = insert_duplicate_detail(duplicate_filepath, file_size)

        if duplicate_id:
            matching_records = [(duplicate_id,) + match for match in matches]
            insert_matches(matching_records)
        else:
            raise Exception(f"Did not receive an ID for this record: {record}")


def insert_duplicate_detail(filepath: str, filesize: int) -> int | None:
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        insert_query = """INSERT INTO duplicate_photos
          (duplicate_filepath, size)
          VALUES (?, ?);"""

        cursor.execute(insert_query, (filepath, filesize,))
        conn.commit()

        cursor.close()
        conn.close()

        return cursor.lastrowid
    except Exception as e:
        raise Exception(f"Could not insert record into duplicate_photos: {e}")


def insert_matches(matches: list):
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        insert_query = """INSERT INTO google_duplicates
          (duplicate_photo_id, google_photo_id, similarity_score)
          VALUES (?, ?, ?);"""

        cursor.executemany(insert_query, matches)
        conn.commit()

        cursor.close()
        conn.close()

        return cursor.lastrowid
    except sqlite3.IntegrityError as ie:
        print(
            f"Error, entries not loaded into google_duplicates: {matches} {ie}")
    except Exception as e:
        raise Exception(f"Could not insert record into duplicate_photos: {e}")


def search_original_records(filename: str) -> list:
    """Fetches Google Photos files that might be the same as the other location based on
        distinct filenames (removed round brackets).

    Args:
        filename (string): Name of possible duplicate to search.

    Raises:
        Exception: General exception.

    Returns:
        list: Filepaths of potential matches.
    """
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        filename_query = """SELECT id, filepath FROM google_photos 
            WHERE distinct_name = ?"""
        cursor.execute(filename_query, (filename,))
        matches = cursor.fetchall()

        cursor.close()
        conn.close()

        return matches
    except Exception as e:
        raise Exception(f"Could not query database for original photos: {e}")


# TODO: Include ability for multiple better copies and choose best
def search_best_copies(batch_size: int = 300) -> list:
    """Compares the sizes of Google Photos against duplicates and returns the larger 
        files, which are assumed to be better quality.

    Raises:
        Exception: General exception.

    Returns:
        list: Original filepath and duplicate filepath of images where the larger copy 
            was found outside of Google Photos.
    """
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        filename_query = """SELECT dp.id, dp.duplicate_filepath
            FROM google_photos gp
            JOIN duplicate_photos dp ON dp.google_photo_id = gp.id
            WHERE dp.size > gp.size
                AND dp.completed IS NULL
            LIMIT 300;"""
        cursor.execute(filename_query)
        matches = cursor.fetchmany(batch_size)

        cursor.close()
        conn.close()

        return matches
    except Exception as e:
        raise Exception(f"Could not query database for best copies: {e}")


def search_new_copies():
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        filename_query = """SELECT dp.new_path, gp.filepath, dp.id
            FROM google_photos gp
            JOIN duplicate_photos dp ON dp.google_photo_id = gp.id
            WHERE dp.new_path IS NOT NULL AND dp.completed IS NULL;"""
        cursor.execute(filename_query)
        matches = cursor.fetchall()

        cursor.close()
        conn.close()

        return matches
    except Exception as e:
        raise Exception(f"Could not query database for new copies: {e}")


def add_new_locations(records: list):
    """Updates duplicate photos table with new filepaths.

    Args:
        records (list): ID of the record to update, and the new filepath to add.

    Raises:
        Exception: General exception.
    """
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        update_query = """UPDATE duplicate_photos
          SET new_path = ?
          WHERE id = ?"""

        cursor.executemany(update_query, records)
        conn.commit()
        print("Total", cursor.rowcount, "records updated with new location")

        cursor.close()
        conn.close()
    except Exception as e:
        raise Exception(f"Could not update records with new locations: {e}")


def add_complete_state(records: list):
    """Updates duplicate photos table with complete status so they aren't done again.

    Args:
        records (list): ID of the record to update.

    Raises:
        Exception: General exception.
    """
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()

        update_query = """UPDATE duplicate_photos
          SET completed = 'Yes'
          WHERE id = ?"""

        cursor.executemany(update_query, records)
        conn.commit()
        print("Total", cursor.rowcount, "records marked as done")

        cursor.close()
        conn.close()
    except Exception as e:
        raise Exception(f"Could not update records with complete state: {e}")