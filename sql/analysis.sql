-- Run against the lab database only. These read-only queries show advanced SQL.
-- 1. Joins and aggregation: how many notes each user has in each category.
SELECT u.username, c.name, COUNT(*) AS notes
FROM posts p JOIN users u ON u.id=p.user_id
JOIN categories c ON c.id=p.category_id
GROUP BY u.username, c.name ORDER BY u.username, notes DESC;

-- 2. CTE and window function: rank each user's categories by note count.
WITH totals AS (
  SELECT user_id, category_id, COUNT(*) AS notes FROM posts
  GROUP BY user_id, category_id
)
SELECT u.username, c.name, t.notes,
  DENSE_RANK() OVER (PARTITION BY t.user_id ORDER BY t.notes DESC) AS category_rank
FROM totals t JOIN users u ON u.id=t.user_id JOIN categories c ON c.id=t.category_id;

-- 3. Latest note per user, using ROW_NUMBER.
WITH ranked AS (
  SELECT user_id, title, created_at,
    ROW_NUMBER() OVER (PARTITION BY user_id ORDER BY created_at DESC, id DESC) AS rn
  FROM posts
)
SELECT u.username, r.title, r.created_at FROM ranked r
JOIN users u ON u.id=r.user_id WHERE rn=1;
