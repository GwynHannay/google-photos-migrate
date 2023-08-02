#!/usr/bin/env python3

import os
import re
import shutil
import sqlite3

import cv2
import exiftool
from datetime import datetime, timedelta
from skimage.metrics import structural_similarity as ssim

other_locations = [
    # "/Volumes/array/storage/photos/Zenphoto Backup/albums/2005/2005-06",
    # "/Volumes/array/storage/photos/Zenphoto Backup/albums/2005/2005-07",
    # "/Volumes/array/storage/photos/Zenphoto Backup/albums/2005/2005-08",
    "/Volumes/array/storage/photos/Categorised/Camera Phone/2015"
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
          size INTEGER,
          created_date TEXT
        );"""
        cursor.execute(main_table_query)
        conn.commit()

        duplicates_table_query = """CREATE TABLE duplicate_photos (
          id INTEGER PRIMARY KEY,
          google_photo_id INTEGER NOT NULL,
          duplicate_filepath TEXT NOT NULL,
          similarity_score TEXT NOT NULL,
          size INTEGER,
          created_date TEXT,
          new_path TEXT,
          completed TEXT,
          FOREIGN KEY(google_photo_id) REFERENCES google_photos(id)
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
            removed rounded brackets), original filename, filepath on system, file 
            size and the extracted original datetime.

    Raises:
        Exception: General exception.
    """
    try:
        conn = sqlite3.connect(db)
        cursor = conn.cursor()

        insert_query = """INSERT INTO google_photos
          (distinct_name, original_name, filepath, size, created_date)
          VALUES (?, ?, ?, ?, ?);"""

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
        records (list): Duplicate picture information with the id of matching Google 
            Photo, filepath of the duplicate, similarity score from 
            skimage.metrics.structural_similarity, file size, and extracted original 
            datetime.

    Raises:
        Exception: General exception.
    """
    try:
        conn = sqlite3.connect(db)
        cursor = conn.cursor()

        insert_query = """INSERT INTO duplicate_photos
          (google_photo_id, duplicate_filepath, similarity_score, size, created_date)
          VALUES (?, ?, ?, ?, ?);"""

        cursor.executemany(insert_query, records)
        conn.commit()
        print("Total", cursor.rowcount, "records insert into db")
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

        filename_query = """SELECT id, filepath FROM google_photos 
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

        filename_query = """SELECT dp.id, dp.duplicate_filepath
            FROM google_photos gp
            JOIN duplicate_photos dp ON dp.google_photo_id = gp.id
            WHERE dp.size > gp.size
                AND dp.completed IS NULL;"""
        cursor.execute(filename_query)
        matches = cursor.fetchall()

        cursor.close()
        conn.close()

        return matches
    except Exception as e:
        raise Exception(f"Could not query database: {e}")


def add_new_locations(records: list):
    """Updates duplicate photos table with new filepaths.

    Args:
        records (list): ID of the record to update, and the new filepath to add.

    Raises:
        Exception: General exception.
    """
    try:
        conn = sqlite3.connect(db)
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
        raise Exception(f"Could not update records: {e}")


def mark_duplicates_done(records: list):
    """Updates duplicate photos table with complete status so they aren't done again.

    Args:
        records (list): ID of the record to update.

    Raises:
        Exception: General exception.
    """
    try:
        conn = sqlite3.connect(db)
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
        raise Exception(f"Could not update records: {e}")


def get_most_accurate_dates():
    try:
        conn = sqlite3.connect(db)
        cursor = conn.cursor()

        filename_query = """SELECT 
                dp.new_path,
                gp.created_date AS google_date,
                dp.created_date as duplicate_date,
                gp.filepath,
                dp.id
            FROM google_photos gp
            JOIN duplicate_photos dp ON dp.google_photo_id = gp.id
            WHERE dp.new_path IS NOT NULL AND dp.completed IS NULL AND
                (dp.created_date > gp.created_date
                OR dp.created_date = 'None');"""
        cursor.execute(filename_query)
        matches = cursor.fetchall()

        cursor.close()
        conn.close()

        return matches
    except Exception as e:
        raise Exception(f"Could not query database: {e}")


def copy_file(filepath: str, duplicate_index: int = 0) -> str:
    basename = os.path.basename(filepath)

    if duplicate_index > 0:
        duplicate_path = os.path.join(
            local_dir, f"duplicate-{duplicate_index}")
        full_path = os.path.join(duplicate_path, basename)
        if os.path.exists(duplicate_path):
            if os.path.exists(full_path):
                return copy_file(filepath, duplicate_index=duplicate_index + 1)
            else:
                shutil.copy(filepath, full_path)
                return full_path
        else:
            os.mkdir(duplicate_path)
            shutil.copy(filepath, full_path)
            return full_path
    else:
        new_path = os.path.join(local_dir, basename)
        if os.path.exists(new_path):
            return copy_file(filepath, duplicate_index=duplicate_index + 1)
        else:
            shutil.copy(filepath, new_path)
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

    with exiftool.ExifToolHelper() as et:
        for match in matches:
            data_file = match[1]
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
                    google_photo_id = match[0]
                    file_size = os.stat(file).st_size
                    created_date = et.get_tags(file, "DateTimeOriginal")

                    if created_date[0].get('XMP:DateTimeOriginal'):
                        original_datetime = created_date[0].get(
                            'XMP:DateTimeOriginal')
                    elif created_date[0].get('EXIF:DateTimeOriginal'):
                        original_datetime = created_date[0].get(
                            'EXIF:DateTimeOriginal')
                    elif created_date[0].get('QuickTime:DateTimeOriginal'):
                        original_datetime = created_date[0].get(
                            'QuickTime:DateTimeOriginal')
                    else:
                        original_datetime = 'None'

                    return_records.append(
                        (google_photo_id,
                         file,
                         str(average_similarity),
                         file_size,
                         original_datetime)
                    )

                storage_video.release()
                data_video.release()
        return return_records


def index_photos():
    db_records = []
    with exiftool.ExifToolHelper() as et:
        for root, dirs, files in os.walk(data_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in extensions):
                    cleaned_filename = re.sub(r"\s\([^)]*\)\.", ".", file)
                    file_path = os.path.join(root, file)
                    file_size = os.stat(file_path).st_size
                    created_date = et.get_tags(file_path, "DateTimeOriginal")

                    if created_date[0].get('XMP:DateTimeOriginal'):
                        original_datetime = created_date[0].get(
                            'XMP:DateTimeOriginal')
                    elif created_date[0].get('EXIF:DateTimeOriginal'):
                        original_datetime = created_date[0].get(
                            'EXIF:DateTimeOriginal')
                    elif created_date[0].get('QuickTime:DateTimeOriginal'):
                        original_datetime = created_date[0].get(
                            'QuickTime:DateTimeOriginal')
                    else:
                        original_datetime = 'None'

                    db_records.append(
                        (cleaned_filename,
                         file,
                         file_path,
                         file_size,
                         original_datetime)
                    )
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
    new_copies = []
    better_copies = find_best_copies()
    if better_copies:
        if os.path.exists(local_dir):
            shutil.rmtree(local_dir)
        
        os.mkdir(local_dir)

    for best_copy in better_copies:
        duplicate_photo_id = best_copy[0]
        duplicate_filepath = best_copy[1]

        new_location = copy_file(duplicate_filepath)
        new_copies.append((new_location, duplicate_photo_id))

    add_new_locations(new_copies)


def replace_photos():
    new_files = get_most_accurate_dates()
    photos_moved = []

    with exiftool.ExifTool() as et:
        for duplicate in new_files:
            timezone_safety_date = None
            change_date = False

            duplicate_file = duplicate[0]
            google_date_string = duplicate[1]
            duplicate_date_string = duplicate[2]
            google_file = duplicate[3]
            duplicate_id = duplicate[4]

            google_date = format_date_string(google_date_string)
            duplicate_date = format_date_string(duplicate_date_string)

            if isinstance(google_date, datetime):
                if isinstance(duplicate_date, datetime):
                    timezone_safety_date = google_date + timedelta(hours=8)

                    if duplicate_date > timezone_safety_date:
                        change_date = True
                else:
                    change_date = True

                if change_date:
                    et.execute("-TagsFromFile", google_file, "-alldates",
                               "-FileModifyDate", duplicate_file, "-overwrite_original")
                else:
                    et.execute(f"-FileModifyDate={duplicate_date}", duplicate_file)

            shutil.move(duplicate_file, google_file)
            photos_moved.append((duplicate_id,))
        mark_duplicates_done(photos_moved)



def format_date_string(datestring: str) -> datetime | None:
    new_date = None

    match len(datestring):
        case 19:
            new_date = datetime.strptime(
                datestring, '%Y:%m:%d %H:%M:%S')
        case 28:
            new_date = datetime.strptime(
                datestring, '%Y:%m:%d %H:%M:%S.%f%z')
        case 24:
            new_date = datetime.strptime(
                datestring, '%Y:%m:%d %H:%M:%S.%fZ')
        case _:
            pass

    return new_date


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

    # Fix any incorrect dates on duplicate images, then replace Google Photos
    replace_photos()
