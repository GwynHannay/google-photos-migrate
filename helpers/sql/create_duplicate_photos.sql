CREATE TABLE duplicate_photos (
    id INTEGER PRIMARY KEY,
    duplicate_filepath TEXT NOT NULL UNIQUE,
    filehash TEXT NOT NULL,
    size INTEGER,
    searched TEXT
);