import json
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


with open("documents.json", "r", encoding="utf-8") as f:
    data = json.load(f)

documents = []
metadata = []

for row in data:
    task = row.get("task", "").strip()
    categories = row.get("categories", "").strip()
    source = row.get("source", "").strip()
    item_type = row.get("type", "").strip()
    slug = row.get("slug", "").strip()

    text = (
        f"Task: {task}. "
        f"Type: {item_type}. "
        f"Categories: {categories}. "
        f"Slug: {slug}. "
        f"Source: {source}"
    )

    documents.append(text)
    metadata.append({
        "id": row.get("id"),
        "task": task,
        "slug": slug,
        "type": item_type,
        "categories": categories,
        "source": source
    })

model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(documents, convert_to_numpy=True)

embeddings = np.array(embeddings, dtype=np.float32)

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)

faiss.write_index(index, "task_index.faiss")

with open("metadata.json", "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=4, ensure_ascii=False)

print(f"Index and metadata saved: {len(metadata)} records")