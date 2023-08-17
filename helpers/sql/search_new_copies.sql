SELECT gd.id, gd.new_path, gp.filepath
FROM google_photos gp
JOIN google_duplicates gd ON gd.google_photo_id = gp.id
WHERE gd.new_path IS NOT NULL AND gd.completed IS NULL;