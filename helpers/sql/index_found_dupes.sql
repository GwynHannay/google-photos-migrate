WITH dupes AS (
    SELECT filehash, MIN(id) AS id
    FROM duplicate_photos
    GROUP BY filehash
    HAVING COUNT(DISTINCT id) > 1
)
INSERT INTO duplicate_duplicates
SELECT dp.id, dp.duplicate_filepath, dp.filehash, dp.size 
FROM duplicate_photos dp
JOIN dupes ON dupes.id = dp.id;