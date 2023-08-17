UPDATE duplicate_photos
SET searched = 'Yes'
WHERE id IN (%s);