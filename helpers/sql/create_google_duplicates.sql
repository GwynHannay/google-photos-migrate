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