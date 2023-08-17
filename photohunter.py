#!/usr/bin/env python3

import hashlib
import os
import re
import shutil

import cv2
import exiftool
import pytz
import yaml
from helpers import db
from datetime import datetime
from itertools import zip_longest
from skimage.metrics import structural_similarity as ssim


###
### Setup and settings happen in this section
db_file = "duplicates.db"
settings_file = "./settings.yaml"


def setup():
    try:
        with open(settings_file, "r") as f:
            settings = yaml.safe_load(f)

            return settings
    except Exception as e:
        raise Exception(f"Could not process settings: {e}")


settings = setup()
timezone = settings.get("timezone")
photos_dir = settings.get("google_location")
working_dir = settings.get("working_location")
duplicate_locations = settings.get("duplicate_locations")

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

similarity_threshold = 0.9
### End of setup and settings
###


def index_photos():
    db_records = list()
    sql_filename = "index_google_photos"
    files_in_dir = (file for file in get_valid_files(photos_dir))
    for root, filename in files_in_dir:
        file_path, file_size, file_hash = get_photo_details(root, filename)
        base_filename = os.path.splitext(filename)
        cleaned_filename = re.sub(r"\s\([^)]*\)\.", ".", base_filename[0])

        db_records.append((cleaned_filename, filename, file_path, file_size, file_hash))
        db_records = prepare_batch(db_records, (False, sql_filename))
    if len(db_records) > 0:
        prepare_batch(db_records, (True, sql_filename))


def index_duplicates(storage_dir: str):
    sql_filename = "index_duplicate_photos"
    already_walked = db.get_results_with_single_val(
        ("search_checked_dirs", "".join([storage_dir, "%"]))
    )
    if not already_walked:
        db_records = list()
        files_in_dir = (file for file in get_valid_files(storage_dir))
        for root, filename in files_in_dir:
            file_path, file_size, file_hash = get_photo_details(root, filename)

            db_records.append((file_path, file_size, file_hash))
            db_records = prepare_batch(db_records, (False, sql_filename))
        if len(db_records) > 0:
            prepare_batch(db_records, (True, sql_filename))
    else:
        print(f"Directory already searched: {storage_dir}")


def prepare_batch(records: list, state: tuple, batch_size: int = 300) -> list:
    if len(records) >= batch_size or state[0]:
        db.insert_many_records((state[1], records))

        empty_list = list()
        return empty_list
    else:
        return records


def clear_original_duplicates():
    sql_filename = "search_google_dupes"
    duplicate_photos = db.get_results(sql_filename)
    if duplicate_photos:
        ids = [i[0] for i in duplicate_photos]
        files = [i[1] for i in duplicate_photos]

        delete_files(files)
        update_deleted_files(ids)


def update_deleted_files(ids: list):
    db.execute_query_with_list(("insert_deleted_photos", ids))
    db.execute_query_with_list(("delete_google_dupes", ids))
    clear_original_duplicates()


def delete_files(files: list):
    for file in files:
        try:
            os.remove(file)
        except Exception as e:
            raise Exception(f"Could not delete file: {file} {e}")


def find_duplicates():
    sql_filename = "search_possible_dupes"
    files = db.get_results(sql_filename)
    if files:
        confirm_duplicates(files)


def confirm_duplicates(files):
    db_records = list()
    match_sql_filename = "index_matches"
    update_sql_filename = "update_search_status"
    for file in files:
        db_records.append(process_file(file))

        if check_batch_ready(db_records):
            matches, ids = split_matched_records(db_records)
            db.insert_many_records((match_sql_filename, matches))
            db.execute_query_with_list((update_sql_filename, ids))

            db_records = None
            db_records = list()
    if len(db_records) > 0:
        matches, ids = split_matched_records(db_records)
        db.insert_many_records((match_sql_filename, matches))
        db.execute_query_with_list((update_sql_filename, ids))

    find_duplicates()


def split_matched_records(records: list) -> tuple:
    matches = list()
    ids = list()
    for record in records:
        if record[3]:
            matches.append((record[0], record[1], record[2]))
        ids.append(record[0])
    return (matches, ids)


def get_photo_details(root: str, filename: str) -> tuple:
    file_path = os.path.join(root, filename)
    file_size = os.stat(file_path).st_size
    hasher = hashlib.md5()

    with open(file_path, "rb") as f:
        buffer = f.read()
        hasher.update(buffer)

    return (file_path, file_size, hasher.hexdigest())


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
            if os.path.isfile(os.path.join(root, file)):
                yield (root, file)


def fetch_best_copies():
    better_copies = db.get_results("search_best_copies")
    if better_copies:
        copy_better_copies(better_copies)


def copy_better_copies(better_copies: list):
    new_copies = None
    new_copies = []
    sql_filename = "update_new_location"
    if not os.path.exists(working_dir):
        os.mkdir(working_dir)

    for best_copy in better_copies:
        photo_match_id = best_copy[0]
        duplicate_filepath = best_copy[1]

        new_location = copy_file(duplicate_filepath)
        new_copies.append((new_location, photo_match_id))

    db.execute_query_with_multiple_vals((sql_filename, new_copies))
    fetch_best_copies()


def replace_photos():
    new_files = db.get_results("search_new_copies")
    if new_files:
        move_better_copies(new_files)


def move_better_copies(new_files: list):
    sql_filename = "update_complete_status"
    updated_files = process_best_dates(new_files)

    for record in new_files:
        shutil.move(record[1], record[2])

    db.execute_query_with_multiple_vals((sql_filename, updated_files))
    replace_photos()


def process_best_dates(db_records: list):
    all_filepaths = [i[2] for i in db_records]
    all_filepaths.extend([i[1] for i in db_records])
    all_dates = get_original_datetimes(all_filepaths)

    google_dates = all_dates[: len(all_dates) // 2]
    duplicate_dates = all_dates[len(all_dates) // 2 :]

    if not len(google_dates) == len(db_records) or not len(duplicate_dates) == len(
        db_records
    ):
        raise Exception(f"Problem processing files: {db_records}")

    records = zip_longest(db_records, duplicate_dates, google_dates)
    file_updates = list()
    db_updates = list()
    for record in records:
        new_line = [record[0][2], record[0][1]]
        new_line.extend(compare_dates(record[2], record[1]))
        file_updates.append(new_line)

        db_updates.append(
            (
                record[2],
                record[1],
                record[0][0],
            )
        )

    replace_dates(file_updates)

    return db_updates


def replace_dates(files: list):
    with exiftool.ExifTool() as et:
        for record in files:
            google_file = record[0]
            duplicate_file = record[1]
            replace_date = record[2]
            modification_date = record[3]

            if replace_date:
                et.execute(
                    "-TagsFromFile",
                    google_file,
                    "-alldates",
                    "-FileModifyDate",
                    duplicate_file,
                    "-overwrite_original",
                )
            else:
                et.execute(f"-FileModifyDate={modification_date}", duplicate_file)


def get_original_datetimes(filepaths: list) -> list:
    with exiftool.ExifToolHelper() as et:
        original_datetimes = None
        original_datetimes = list()
        for filepath in filepaths:
            created_date = et.get_tags(filepath, "DateTimeOriginal")
            original_datetimes.append(find_preferred_datetime(created_date))

        return original_datetimes


def find_preferred_datetime(tags: list) -> str:
    if tags[0].get("XMP:DateTimeOriginal"):
        original_datetime = tags[0].get("XMP:DateTimeOriginal")
    elif tags[0].get("EXIF:DateTimeOriginal"):
        original_datetime = tags[0].get("EXIF:DateTimeOriginal")
    elif tags[0].get("QuickTime:DateTimeOriginal"):
        original_datetime = tags[0].get("QuickTime:DateTimeOriginal")
    else:
        original_datetime = "None"

    if original_datetime == "0000:00:00 00:00:00":
        original_datetime = "None"

    return original_datetime


def process_file(file: tuple) -> tuple:
    duplicate_record = tuple()
    # Extract the basename
    file_path = file[1]
    filename = os.path.basename(file_path)
    basename = os.path.splitext(filename)

    # Check if a corresponding file exists in the database
    matches = db.get_results_with_single_val(("search_google_photos", basename[0]))

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

            storage_video.release()
            data_video.release()

            if average_similarity >= similarity_threshold:
                google_photo_id = match[0]

                duplicate_record = (
                    file[0],
                    google_photo_id,
                    str(average_similarity),
                    True,
                )
                break

    if len(duplicate_record) < 1:
        duplicate_record = (file[0], None, None, False)

    return duplicate_record


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


def compare_dates(original_date_string: str, duplicate_date_string: str) -> list:
    original_date = format_date_string(original_date_string)
    if not isinstance(original_date, datetime):
        raise Exception(
            f"This from Google Photos wasn't a valid date: {original_date_string}"
        )

    duplicate_date = format_date_string(duplicate_date_string)

    if isinstance(duplicate_date, datetime):
        original_naive_date = original_date.replace(tzinfo=pytz.utc)
        timezone_safety_date = original_naive_date.astimezone(tz)
        duplicate_with_tz = duplicate_date.astimezone(tz)

        if duplicate_with_tz > timezone_safety_date:
            return [True, original_date]
        else:
            return [False, duplicate_date]
    else:
        return [True, original_date]


def copy_file(filepath: str, duplicate_index: int = 0) -> str:
    basename = os.path.basename(filepath)

    if duplicate_index > 0:
        duplicate_path = os.path.join(working_dir, f"duplicate-{duplicate_index}")
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
            new_date = datetime.strptime(datestring, "%Y:%m:%d %H:%M:%S")
        case 28:
            new_date = datetime.strptime(datestring, "%Y:%m:%d %H:%M:%S.%f%z")
        case 24:
            new_date = datetime.strptime(datestring, "%Y:%m:%d %H:%M:%S.%fZ")
        case _:
            pass

    return new_date


def clean_new_duplicates():
    db.execute_query("index_found_dupes")
    db.execute_query("index_new_dupes")
    db.execute_query("delete_duplicate_dupes")


if __name__ == "__main__":
    # Make sure db exists, or create it
    if not os.path.exists(db_file):
        print("Creating SQLite database and tables")
        db.create_db()

        # Index Google Photos with cleaned filenames
        print("Storing records of Google Photos in database")
        index_photos()
        clear_original_duplicates()

    # Check for duplicates from other locations
    for location in duplicate_locations:
        print(f"Searching location for duplicates: {location}")
        index_duplicates(location)

    # Compare photos to Google Photos
    print("Cleaning up duplicates found")
    clean_new_duplicates()
    print("Comparing new photos with Google photos")
    find_duplicates()

    # Get the best copies to local folder
    print("Getting higher quality pictures")
    fetch_best_copies()

    # Fix any incorrect dates on duplicate images, then replace Google Photos
    print("Replacing original pictures with higher quality")
    replace_photos()
