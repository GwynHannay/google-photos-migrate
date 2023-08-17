CREATE TABLE deleted_photos (
    id INTEGER PRIMARY KEY,
    distinct_name TEXT NOT NULL,
    original_name TEXT NOT NULL,
    filepath TEXT NOT NULL UNIQUE,
    filehash TEXT NOT NULL,
    size INTEGER
);