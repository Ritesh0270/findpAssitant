import json
import os
import re
import html
from urllib.parse import quote

import pymysql
from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_FILE = os.path.join(BASE_DIR, "documents.json")

GENERIC_CATEGORIES = {
    "install",
    "repair",
    "replace",
    "build",
    "service",
    "cleaning",
    "clean",
    "remodel",
    "renovate",
    "painting",
    "flooring",
    "delivery",
    "offsite",
    "fan",
    "planner",
    "raise",
    "resurface",
    "refinish",
    "pumping",
    "repair or service",
    "install or replace",
    "build or replace",
    "remove and haul waste, junk, building materials and debris",
}


def normalize_space(text):
    return " ".join(str(text or "").strip().split())


def clean_text(text):
    text = html.unescape(str(text or ""))
    text = normalize_space(text)
    return text


def normalize_slug(slug):
    slug = clean_text(slug).lower()
    slug = slug.replace("_", "-")
    slug = re.sub(r"-+", "-", slug)
    return slug


def slug_to_words(slug):
    return normalize_slug(slug).replace("-", " ").strip()


def looks_like_bad_slug(slug):
    slug = normalize_slug(slug)

    if not slug:
        return True

    if slug.isdigit():
        return True

    if len(slug) < 3:
        return True

    if not re.fullmatch(r"[a-z0-9-]+", slug):
        return True

    return False


def similarity_score(a, b):
    a_words = set(clean_text(a).lower().split())
    b_words = set(clean_text(b).lower().split())

    if not a_words or not b_words:
        return 0.0

    return len(a_words & b_words) / max(len(a_words), 1)


def is_slug_task_mismatch(task, slug):
    task_clean = clean_text(task).lower()
    slug_words = slug_to_words(slug)

    if slug_words in task_clean or task_clean in slug_words:
        return False

    score = similarity_score(task_clean, slug_words)

    return score < 0.20


def split_categories(categories):
    raw_parts = [clean_text(x) for x in str(categories or "").split(",")]

    parts = []
    seen = set()

    for part in raw_parts:
        part_l = part.lower().strip(" .")

        if not part_l:
            continue

        if part_l in GENERIC_CATEGORIES:
            continue

        if len(part_l) <= 2:
            continue

        if part_l in seen:
            continue

        seen.add(part_l)
        parts.append(part.strip())

    return parts


def build_source(item_type, slug, item_id):
    safe_slug = quote(normalize_slug(slug))

    if item_type == "task":
        return f"https://quotes.findpros.com/task.{safe_slug}.{item_id}.html?step=0"

    return f"https://quotes.findpros.com/category.{safe_slug}.{item_id}.html?step=0"


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
seen_ids = set()
seen_keys = set()

skipped = {
    "bad_slug": 0,
    "mismatch": 0,
    "duplicate": 0,
    "empty": 0
}


def add_rows(rows, item_type):
    for row in rows:
        item_id = row["ID"]
        task = clean_text(row.get("task"))
        slug = normalize_slug(row.get("slug"))
        categories_raw = clean_text(row.get("categories"))

        if not task or not slug:
            skipped["empty"] += 1
            continue

        if looks_like_bad_slug(slug):
            skipped["bad_slug"] += 1
            continue

        if item_type == "task" and is_slug_task_mismatch(task, slug):
            skipped["mismatch"] += 1
            continue

        categories = ", ".join(split_categories(categories_raw))

        id_key = (item_type, item_id)
        uniq_key = (item_type, slug, task.lower())

        if id_key in seen_ids or uniq_key in seen_keys:
            skipped["duplicate"] += 1
            continue

        seen_ids.add(id_key)
        seen_keys.add(uniq_key)

        final_data.append({
            "id": item_id,
            "task": task,
            "slug": slug,
            "type": item_type,
            "categories": categories,
            "source": build_source(item_type, slug, item_id)
        })


add_rows(task_data, "task")
add_rows(category_data, "category")

final_data.sort(key=lambda x: (x["type"], x["id"]))

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
    json.dump(final_data, f, indent=4, ensure_ascii=False)

print("=" * 60)
print(f"Data saved: {len(final_data)} records")
print(f"Output file: {OUTPUT_FILE}")
print("Skipped summary:")

for key, value in skipped.items():
    print(f" - {key}: {value}")

print("=" * 60)

cursor.close()
conn.close()