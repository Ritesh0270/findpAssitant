import pymysql
import json
from dotenv import load_dotenv
import os

load_dotenv()

conn = pymysql.connect(
    host=os.getenv("DB_HOST"),
    user=os.getenv("DB_USER"),
    password=os.getenv("DB_PASSWORD"),
    database=os.getenv("DB_NAME"),
    cursorclass=pymysql.cursors.DictCursor
)

cursor = conn.cursor()

task_query = """
SELECT 
    p.ID,
    TRIM(p.post_title) AS task,
    TRIM(p.post_name) AS slug,
    GROUP_CONCAT(
        DISTINCT TRIM(t.name)
        ORDER BY t.name
        SEPARATOR ', '
    ) AS categories
FROM wp_posts p
JOIN wp_term_relationships tr ON p.ID = tr.object_id
JOIN wp_term_taxonomy tt 
    ON tr.term_taxonomy_id = tt.term_taxonomy_id
    AND tt.taxonomy = 'task_category'
JOIN wp_terms t ON tt.term_id = t.term_id
WHERE p.post_type = 'task'
AND p.post_status = 'publish'
AND TRIM(p.post_title) <> ''
AND TRIM(p.post_name) <> ''
GROUP BY p.ID, p.post_title, p.post_name
ORDER BY p.ID;
"""

category_query = """
SELECT
    t.term_id AS ID,
    TRIM(t.name) AS task,
    TRIM(t.slug) AS slug,
    TRIM(t.name) AS categories
FROM wp_terms t
JOIN wp_term_taxonomy tt ON t.term_id = tt.term_id
WHERE tt.taxonomy = 'task_category'
AND TRIM(t.name) <> ''
AND TRIM(t.slug) <> ''
ORDER BY t.term_id;
"""

cursor.execute(task_query)
task_data = cursor.fetchall()

cursor.execute(category_query)
category_data = cursor.fetchall()

final_data = []
seen = set()

for row in task_data:
    if not row["task"] or not row["slug"]:
        continue

    item_id = row["ID"]
    task = row["task"].strip()
    slug = row["slug"].strip()
    categories = (row["categories"] or "").strip()

    key = ("task", item_id)
    if key in seen:
        continue
    seen.add(key)

    source = f"https://quotes.findpros.com/task.{slug}.{item_id}.html?step=0"

    final_data.append({
        "id": item_id,
        "task": task,
        "slug": slug,
        "type": "task",
        "categories": categories,
        "source": source
    })

for row in category_data:
    if not row["task"] or not row["slug"]:
        continue

    item_id = row["ID"]
    task = row["task"].strip()
    slug = row["slug"].strip()
    categories = (row["categories"] or "").strip()

    key = ("category", item_id)
    if key in seen:
        continue
    seen.add(key)

    source = f"https://quotes.findpros.com/category.{slug}.{item_id}.html?step=0"
    final_data.append({
        "id": item_id,
        "task": task,
        "slug": slug,
        "type": "category",
        "categories": categories,
        "source": source
    })

with open("documents.json", "w", encoding="utf-8") as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print(f"Data saved: {len(final_data)} records")
cursor.close()
conn.close()