WITH all_matches AS (
    SELECT 
        gd.id, 
        gd.google_photo_id, 
        gd.duplicate_photo_id, 
        gd.similarity_score, 
        gd.new_path, 
        gd.completed, 
        dp.size,
        dp.duplicate_filepath, 
        RANK() OVER (
            PARTITION BY duplicate_photo_id, completed 
            ORDER BY similarity_score DESC, dp.size DESC
        ) AS dupe_rank, 
        RANK() OVER (
            PARTITION BY google_photo_id, completed 
            ORDER BY similarity_score DESC, dp.size DESC
        ) AS google_rank
    FROM google_photos gp
    JOIN google_duplicates gd ON gd.google_photo_id = gp.id
    JOIN duplicate_photos dp ON gd.duplicate_photo_id = dp.id
    WHERE dp.size > gp.size
), dupes_done AS (
    SELECT nd.id
    FROM all_matches AS ad
    JOIN all_matches AS nd ON ad.duplicate_photo_id = nd.duplicate_photo_id
        AND ad.id <> nd.id
        AND nd.completed IS NULL
        AND ((nd.similarity_score = ad.similarity_score
            AND nd.size <= ad.size)
            OR
            nd.similarity_score < ad.similarity_score)
    WHERE ad.completed = 'Yes'
), google_done AS (
    SELECT nd.id
    FROM all_matches AS ad
    JOIN all_matches AS nd ON ad.google_photo_id = nd.google_photo_id
        AND ad.id <> nd.id
        AND nd.completed IS NULL
        AND ((nd.similarity_score = ad.similarity_score
            AND nd.size <= ad.size)
                OR
            nd.similarity_score < ad.similarity_score)
    WHERE ad.completed = 'Yes'
)
SELECT am.id, duplicate_filepath
FROM all_matches am
LEFT JOIN dupes_done dd ON dd.id = am.id
LEFT JOIN google_done gd ON gd.id = am.id
WHERE dd.id IS NULL
    AND gd.id IS NULL
    AND new_path IS NULL
    AND dupe_rank = 1
    AND google_rank = 1;