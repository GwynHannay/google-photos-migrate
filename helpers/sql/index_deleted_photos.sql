INSERT INTO deleted_photos
SELECT * FROM google_photos
WHERE id IN (%s);