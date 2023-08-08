#!/usr/bin/env python3

import os
import re
import shutil

import cv2
import exiftool
import pytz
import yaml
from helpers import db
from datetime import datetime
from skimage.metrics import structural_similarity as ssim


###
### Setup and settings happen in this section
db_file = 'duplicates.db'
settings_file = './settings.yaml'
def setup():
    try:
        with open(settings_file, 'r') as f:
            settings = yaml.safe_load(f)

            return settings
    except Exception as e:
        raise Exception(f"Could not process settings: {e}")


settings = setup()
timezone = settings.get('timezone')
photos_dir = settings.get('google_location')
working_dir = settings.get('working_location')
duplicate_locations = settings.get('duplicate_locations')

tz = pytz.timezone(timezone)

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
### End of setup and settings
###


def index_photos():
    db_records = []
    files_in_dir = (file for file in get_valid_files(photos_dir))
    for root, filename in files_in_dir:
        cleaned_filename = re.sub(r"\s\([^)]*\)\.", ".", filename)
        file_path, file_size = get_photo_details(root, filename)

        db_records.append((cleaned_filename, filename, file_path, file_size))

        if check_batch_ready(db_records):
            db.insert_original_records(db_records)
            db_records = None
            db_records = []
    if len(db_records) > 0:
        db.insert_original_records(db_records)


def find_duplicates(storage_dir: str):
    db_records = []
    files_in_dir = (file for file in get_valid_files(storage_dir))
    for root, filename in files_in_dir:
        file_path, file_size = get_photo_details(root, filename)
        matches = process_file(file_path)
        db_records.append((file_path, file_size, matches))

        if check_batch_ready(db_records):
            db.insert_duplicate_records(db_records)
            db_records = None
            db_records = []
    if len(db_records) > 0:
        db.insert_duplicate_records(db_records)


def get_photo_details(root: str, filename: str) -> tuple:
    file_path = os.path.join(root, filename)
    file_size = os.stat(file_path).st_size

    return (file_path, file_size)


def get_valid_files(dir_path: str):
    files_in_dir = (file for file in walk_photos_directory(dir_path))
    for file in files_in_dir:
        if check_file_extension(file[1]):
            yield file


def check_file_extension(filename: str) -> bool:
    if any(filename.lower().endswith(ext) for ext in extensions):
        return True
    else:
        return False


def check_batch_ready(records: list, batch_len: int = 300) -> bool:
    if len(records) >= batch_len:
        return True
    else:
        return False


def walk_photos_directory(dir_path: str):
    for root, dirs, files in os.walk(dir_path):
        for file in files:
            yield (root, file)


def fetch_best_copies():
    new_copies = []
    better_copies = db.search_best_copies()
    if better_copies:
        if not os.path.exists(working_dir):
            os.mkdir(working_dir)

        for best_copy in better_copies:
            duplicate_photo_id = best_copy[0]
            duplicate_filepath = best_copy[1]

            new_location = copy_file(duplicate_filepath)
            new_copies.append((new_location, duplicate_photo_id))

        db.add_new_locations(new_copies)
        fetch_best_copies()


def replace_photos():
    new_files = db.search_best_copies()
    photos_moved = []

    with exiftool.ExifTool() as et:
        for duplicate in new_files:

            duplicate_file = duplicate[0]
            google_date_string = duplicate[1]
            duplicate_date_string = duplicate[2]
            google_file = duplicate[3]
            duplicate_id = duplicate[4]

            replace_date = compare_dates(
                google_date_string, duplicate_date_string)
            print(replace_date, google_date_string,
                  duplicate_date_string, google_file)

            if replace_date[0]:
                et.execute("-TagsFromFile", google_file, "-alldates",
                           "-FileModifyDate", duplicate_file, "-overwrite_original")
            else:
                et.execute(
                    f"-FileModifyDate={replace_date[1]}", duplicate_file)

            shutil.move(duplicate_file, google_file)
            photos_moved.append((duplicate_id,))
        db.add_complete_state(photos_moved)


def process_file(file_path: str) -> list:
    duplicate_records = []
    # Extract the basename
    basename = os.path.basename(file_path)

    # Check if a corresponding file exists in the database
    matches = db.search_original_records(basename)

    for match in matches:
        data_file = match[1]
        if os.path.exists(data_file):
            # Load and compare videos
            storage_video = cv2.VideoCapture(file_path)
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

                duplicate_records.append(
                    (google_photo_id, str(average_similarity)))

            storage_video.release()
            data_video.release()

    return duplicate_records


def get_original_datetime(filepath: str) -> str:
    with exiftool.ExifToolHelper() as et:
        created_date = et.get_tags(filepath, "DateTimeOriginal")

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

        if original_datetime == '0000:00:00 00:00:00':
            original_datetime = 'None'

        return original_datetime


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


def compare_dates(original_date_string: str, duplicate_date_string: str):
    original_date = format_date_string(original_date_string)
    if not isinstance(original_date, datetime):
        raise Exception(
            f"This from Google Photos wasn't a valid date: {original_date_string}")

    duplicate_date = format_date_string(duplicate_date_string)

    if isinstance(duplicate_date, datetime):
        original_naive_date = original_date.replace(tzinfo=pytz.utc)
        timezone_safety_date = original_naive_date.astimezone(tz)
        duplicate_with_tz = duplicate_date.astimezone(tz)

        if duplicate_with_tz > timezone_safety_date:
            return (True, original_date)
        else:
            return (False, duplicate_date)
    else:
        return (True, original_date)


def copy_file(filepath: str, duplicate_index: int = 0) -> str:
    basename = os.path.basename(filepath)

    if duplicate_index > 0:
        duplicate_path = os.path.join(
            working_dir, f"duplicate-{duplicate_index}")
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
        new_path = os.path.join(working_dir, basename)
        if os.path.exists(new_path):
            return copy_file(filepath, duplicate_index=duplicate_index + 1)
        else:
            shutil.copy2(filepath, new_path)
            return new_path


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
    if not os.path.exists(db_file):
        print("Creating SQLite database and tables")
        db.create_db()

        # Index Google Photos with cleaned filenames
        print("Storing records of Google Photos in database")
        index_photos()

    # Check for duplicates from other locations
    for location in duplicate_locations:
        print(f"Searching location for duplicates: {location}")
        find_duplicates(location)

    # # Get the best copies to local folder
    # print("Getting higher quality pictures")
    # fetch_best_copies()

    # # Fix any incorrect dates on duplicate images, then replace Google Photos
    # print("Replacing original pictures with higher quality")
    # replace_photos()
