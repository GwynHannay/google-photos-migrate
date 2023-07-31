#!/usr/bin/env python3

import os
import cv2
import re
import sqlite3
import shutil
from skimage.metrics import structural_similarity as ssim

other_locations = [
    "/Volumes/array/storage/photos/Zenphoto Backup/albums/2004",
    "/Volumes/array/storage/photos/Zenphoto Backup/albums/2005"
]

data_dir = "../output"
local_dir = "./copies"

extensions = [
    ".jpg",
    ".jpeg",
    ".png",
    ".raw",
    ".ico",
    ".tiff",
    ".webp",
    ".heic",
    ".heif",
    ".gif",
    ".mp4",
    ".mov",
    ".qt",
    ".mov.qt",
    ".mkv",
    ".wmv",
    ".webm",
]

similarity_threshold = 0.8

db = "duplicates.db"

duplicates = "./duplicates_data.txt"
open(duplicates, "w").close()


def create_db():
    """Create SQLite database with tables for Google Photos and duplicates.

    Raises:
        Exception: General exception with error message.
    """
    try:
        conn = sqlite3.connect(db)
        cursor = conn.cursor()

        main_table_query = """CREATE TABLE google_photos (
          id INTEGER PRIMARY KEY,
          distinct_name TEXT NOT NULL,
          original_name TEXT NOT NULL,
          filepath TEXT NOT NULL,
          size INTEGER
        );"""
        cursor.execute(main_table_query)
        conn.commit()

        duplicates_table_query = """CREATE TABLE duplicate_photos (
          id INTEGER PRIMARY KEY,
          original_filepath TEXT NOT NULL,
          duplicate_filepath TEXT NOT NULL,
          similarity_score TEXT NOT NULL,
          size INTEGER
        );"""
        cursor.execute(duplicates_table_query)
        conn.commit()

        cursor.close()
        conn.close()
    except Exception as e:
        raise Exception(f"Could not create db and tables: {e}")


def insert_original_records(records: list):
    """Inserts multiple records of original Google Photos.

    Args:
        records (list): Google Photo information such as distinct filename (having 
            removed rounded brackets), original filename, filepath on system and file 
            size.

    Raises:
        Exception: General exception.
    """
    try:
        conn = sqlite3.connect(db)
        cursor = conn.cursor()

        insert_query = """INSERT INTO google_photos
          (distinct_name, original_name, filepath, size)
          VALUES (?, ?, ?, ?);"""

        cursor.executemany(insert_query, records)
        conn.commit()
        print("Total", cursor.rowcount, "records insert into db")
        conn.commit()

        cursor.close()
        conn.close()
    except Exception as e:
        raise Exception(f"Could not insert records: {e}")


def insert_duplicates_records(records: list):
    """Inserts multiple records of duplicate pictures found.

    Args:
        records (list): Duplicate picture information such as the filepath of the 
            original (matches google_photos.filepath), filepath of the duplicate,
            similarity score from skimage.metrics.structural_similarity, and file size.

    Raises:
        Exception: General exception.
    """
    try:
        conn = sqlite3.connect(db)
        cursor = conn.cursor()

        insert_query = """INSERT INTO duplicate_photos
          (original_filepath, duplicate_filepath, similarity_score, size)
          VALUES (?, ?, ?, ?);"""

        cursor.executemany(insert_query, records)
        conn.commit()

        cursor.close()
        conn.close()
    except Exception as e:
        raise Exception(f"Could not insert records: {e}")


def check_db(filename: str) -> list:
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
        conn = sqlite3.connect(db)
        cursor = conn.cursor()

        filename_query = """SELECT filepath FROM google_photos 
            WHERE distinct_name = ?"""
        cursor.execute(filename_query, (filename,))
        matches = cursor.fetchall()

        cursor.close()
        conn.close()

        return matches
    except Exception as e:
        raise Exception(f"Could not query database: {e}")


def find_best_copies() -> list:
    """Compares the sizes of Google Photos against duplicates and returns the larger 
        files, which are assumed to be better quality.

    Raises:
        Exception: General exception.

    Returns:
        list: Original filepath and duplicate filepath of images where the larger copy 
            was found outside of Google Photos.
    """
    try:
        conn = sqlite3.connect(db)
        cursor = conn.cursor()

        filename_query = """SELECT dp.original_filepath, dp.duplicate_filepath
            FROM google_photos gp
            JOIN duplicate_photos dp ON dp.original_filepath = gp.filepath
            WHERE dp.size > gp.size;"""
        cursor.execute(filename_query)
        matches = cursor.fetchall()

        cursor.close()
        conn.close()

        return matches
    except Exception as e:
        raise Exception(f"Could not query database: {e}")


def copy_file(filepath: str, duplicate_index: int=0) -> str:
    basename = os.path.basename(filepath)

    if duplicate_index > 0:
        duplicate_path = os.path.join(
            local_dir, f"duplicate-{duplicate_index}")
        full_path = os.path.join(duplicate_path, basename)
        if os.path.exists(duplicate_path):
            if os.path.exists(full_path):
                return copy_file(filepath, duplicate_index=duplicate_index + 1)
            else:
                shutil.copy2(filepath, full_path)
                return full_path
        else:
            os.mkdir(duplicate_path)
            shutil.copy2(filepath, full_path)
            return full_path
    else:
        new_path = os.path.join(local_dir, basename)
        if os.path.exists(new_path):
            return copy_file(filepath, duplicate_index=duplicate_index + 1)
        else:
            shutil.copy2(filepath, new_path)
            return new_path


def compare_frames(frame1, frame2):
    # Resize frames to a consistent size for comparison
    frame1 = cv2.resize(frame1, (500, 500))
    frame2 = cv2.resize(frame2, (500, 500))

    # Convert frames to grayscale
    gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
    gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

    # Compute structural similarity index (SSIM) between the frames
    similarity = ssim(gray1, gray2)

    return similarity


def process_file(file: str) -> list:
    return_records = []
    # Extract the basename
    basename = os.path.basename(file)

    # Check if a corresponding file exists in the database
    matches = check_db(basename)

    for match in matches:
        data_file = match
        if os.path.exists(data_file):
            # Load and compare videos
            storage_video = cv2.VideoCapture(file)
            data_video = cv2.VideoCapture(data_file)

            similarity_sum = 0
            frame_count = 0

            while True:
                # Read frames from the videos
                ret1, storage_frame = storage_video.read()
                ret2, data_frame = data_video.read()

                if not ret1 or not ret2:
                    break

                similarity = compare_frames(storage_frame, data_frame)
                similarity_sum += similarity
                frame_count += 1

            average_similarity = similarity_sum / frame_count if frame_count > 0 else 0

            if average_similarity >= similarity_threshold:
                file_size = os.stat(file).st_size
                return_records.append(
                    (data_file, file, str(average_similarity), file_size))

            storage_video.release()
            data_video.release()
    return return_records


def index_photos():
    db_records = []
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in extensions):
                cleaned_filename = re.sub(r"\s\([^)]*\)\.", ".", file)
                file_path = os.path.join(root, file)
                file_size = os.stat(file_path).st_size
                db_records.append(
                    (cleaned_filename, file, file_path, file_size))
        insert_original_records(db_records)
        db_records = None
        db_records = []


def find_duplicates(storage_dir: str):
    db_records = []
    # Loop over files in the storage directory
    for root, dirs, files in os.walk(storage_dir):
        print(dirs)
        for file in files:
            # Check file extension
            if any(file.lower().endswith(ext) for ext in extensions):
                file_path = os.path.join(root, file)
                db_records.extend(process_file(file_path))

        insert_duplicates_records(db_records)
        db_records = None
        db_records = []


def fetch_best_copies():
    better_copies = find_best_copies()
    if better_copies:
        if not os.path.exists(local_dir):
            os.mkdir(local_dir)

    for best_copy in better_copies:
        new_location = copy_file(best_copy[1])
        with open(duplicates, "a") as f:
            f.write(f"{new_location} - {best_copy[0]}\n")


if __name__ == "__main__":
    # Make sure db exists, or create it
    if not os.path.exists(db):
        print("Creating SQLite database and tables")
        create_db()

        # Index Google Photos with cleaned filenames
        print("Storing records of Google Photos in database")
        index_photos()

        # Check for duplicates from other locations
        for location in other_locations:
            print(f"Searching location for duplicates: {location}")
            find_duplicates(location)

    # Get the best copies to local folder
    print("Getting higher quality pictures")
    fetch_best_copies()
