-- List of all Google Photos processed by original scripts
CREATE TABLE google_photos (
    id INTEGER PRIMARY KEY,
    distinct_name TEXT NOT NULL,
    original_name TEXT NOT NULL,
    filepath TEXT NOT NULL UNIQUE,
    filehash TEXT NOT NULL,
    size INTEGER
);

-- List of all photos in specified other locations
CREATE TABLE duplicate_photos (
    id INTEGER PRIMARY KEY,
    duplicate_filepath TEXT NOT NULL UNIQUE,
    filehash TEXT NOT NULL,
    size INTEGER,
    searched TEXT
);

-- Many-to-many matching duplicate_photos with structurally similar google_photos
CREATE TABLE google_duplicates (
    id INTEGER PRIMARY KEY,
    google_photo_id INTEGER NOT NULL,
    duplicate_photo_id INTEGER NOT NULL,
    similarity_score TEXT NOT NULL,
    new_path TEXT,
    google_date TEXT,
    duplicate_date TEXT,
    completed TEXT,
    FOREIGN KEY(google_photo_id) REFERENCES google_photos(id),
    FOREIGN KEY(duplicate_photo_id) REFERENCES duplicate_photos(id),
    CONSTRAINT unique_matches UNIQUE(google_photo_id, duplicate_photo_id)
);

-- Duplicates of Google Photos (deleted from google_photos and added here)
CREATE TABLE deleted_photos (
    id INTEGER PRIMARY KEY,
    distinct_name TEXT NOT NULL,
    original_name TEXT NOT NULL,
    filepath TEXT NOT NULL UNIQUE,
    filehash TEXT NOT NULL,
    size INTEGER
);

-- Duplicates of photos from other locations (deleted from duplicate_photos and added here)
CREATE TABLE duplicate_duplicates (
    id INTEGER PRIMARY KEY,
    duplicate_filepath TEXT NOT NULL UNIQUE,
    filehash TEXT NOT NULL,
    size INTEGER
);