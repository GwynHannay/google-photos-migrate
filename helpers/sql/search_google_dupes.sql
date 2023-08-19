WITH dupes AS (
    SELECT filehash
    FROM google_photos
    GROUP BY filehash
    HAVING COUNT(DISTINCT id) > 1
), preference AS (
    SELECT id, ROW_NUMBER() OVER(PARTITION BY gp.filehash 
        ORDER BY CASE WHEN filepath LIKE '%duplicates-%' 
        THEN 1 ELSE 0 END DESC, filepath DESC) AS num
    FROM google_photos gp
    JOIN dupes ON dupes.filehash = gp.filehash
)
SELECT gp.id, filepath FROM google_photos gp
JOIN preference p ON p.id = gp.id
WHERE num = 1;