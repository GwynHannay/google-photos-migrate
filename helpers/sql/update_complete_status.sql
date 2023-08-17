UPDATE google_duplicates
SET google_date = ?,
    duplicate_date = ?,
    completed = 'Yes'
WHERE id = ?;