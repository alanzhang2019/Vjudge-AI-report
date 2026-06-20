SELECT luogu_uid, real_name, grade, target_grade, target_competition, school
FROM students
WHERE real_name IS NOT NULL
  AND real_name NOT LIKE '%测试%'
  AND real_name NOT LIKE 'phase3%'
ORDER BY id DESC
LIMIT 50;
