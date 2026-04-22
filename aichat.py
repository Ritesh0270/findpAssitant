import os
import json
import time
import difflib
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from openai import OpenAI
from dotenv import load_dotenv


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_PATH)

print("=" * 60)
print("FindPros AI Starting...")
print("BASE DIR:", BASE_DIR)
print("ENV FILE FOUND:", os.path.exists(ENV_PATH))
print("API KEY LOADED:", "YES" if os.getenv("API_KEY") else "NO")
print("BASE URL:", os.getenv("API_BASE_URL"))
print("MODEL:", os.getenv("GROQ_MODEL"))
print("=" * 60)


class FindProsAssistant:
    def __init__(
        self,
        index_path="task_index.faiss",
        metadata_path="metadata.json",
        embedding_model="all-MiniLM-L6-v2",
        query_log_path="query_logs.json"
    ):
        self.api_key = os.getenv("API_KEY")
        self.base_url = os.getenv(
            "API_BASE_URL",
            "https://api.groq.com/openai/v1"
        )
        self.model = os.getenv(
            "GROQ_MODEL",
            "llama-3.3-70b-versatile"
        )

        self.index_path = os.path.join(BASE_DIR, index_path)
        self.metadata_path = os.path.join(BASE_DIR, metadata_path)
        self.query_log_path = os.path.join(BASE_DIR, query_log_path)

        self.embedding_model = SentenceTransformer(embedding_model)
        self.index = self.load_index()
        self.metadata = self.load_metadata()
        self.client = self.create_client()

        self._prepare_metadata_cache()

    def load_index(self):
        if not os.path.exists(self.index_path):
            raise FileNotFoundError(
                f"Missing FAISS file: {self.index_path}"
            )
        return faiss.read_index(self.index_path)

    def load_metadata(self):
        if not os.path.exists(self.metadata_path):
            raise FileNotFoundError(
                f"Missing metadata file: {self.metadata_path}"
            )

        with open(self.metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def create_client(self):
        if not self.api_key:
            print("API key not loaded.")
            return None

        try:
            client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            print("AI Client Connected")
            return client
        except Exception as e:
            print("Client Error:", e)
            return None

    def clean(self, text):
        return " ".join(str(text or "").strip().lower().split())

    def normalize_slug(self, text):
        return self.clean(str(text or "").replace("-", " "))

    def get_task_url(self, item):
        return (
            item.get("source")
            or item.get("base_source")
            or "https://quotes.findpros.com/"
        )

    def _prepare_metadata_cache(self):
        self.lookup_strings = []

        for item in self.metadata:
            item["_task_clean"] = self.clean(item.get("task", ""))
            item["_categories_clean"] = self.clean(item.get("categories", ""))
            item["_slug_clean"] = self.normalize_slug(item.get("slug", ""))
            item["_type_clean"] = self.clean(item.get("type", ""))

            self.lookup_strings.append({
                "task": item["_task_clean"],
                "slug": item["_slug_clean"],
                "categories": item["_categories_clean"],
                "type": item["_type_clean"]
            })

    def log_query(self, query, results_count=0, matched_tasks=None):
        try:
            entry = {
                "timestamp": int(time.time()),
                "query": query,
                "results_count": results_count,
                "matched_tasks": matched_tasks or []
            }

            logs = []
            if os.path.exists(self.query_log_path):
                with open(self.query_log_path, "r", encoding="utf-8") as f:
                    logs = json.load(f)

            logs.append(entry)
            logs = logs[-200:]  # keep last 200 queries only

            with open(self.query_log_path, "w", encoding="utf-8") as f:
                json.dump(logs, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print("Query log error:", e)

    def is_broad_query(self, query):
        words = self.clean(query).split()
        return len(words) <= 2

    def is_specific_query(self, query):
        words = self.clean(query).split()
        return len(words) >= 3

    def get_typo_similarity_bonus(self, query_clean, target_clean):
        if not query_clean or not target_clean:
            return 0

        ratio = difflib.SequenceMatcher(None, query_clean, target_clean).ratio()

        if ratio >= 0.92:
            return 70
        if ratio >= 0.86:
            return 40
        if ratio >= 0.80:
            return 20
        return 0

    def score_item(self, query, item):
        query_clean = self.clean(query)
        task_clean = item.get("_task_clean", self.clean(item.get("task", "")))
        categories_clean = item.get(
            "_categories_clean",
            self.clean(item.get("categories", ""))
        )
        slug_clean = item.get(
            "_slug_clean",
            self.normalize_slug(item.get("slug", ""))
        )
        item_type = item.get("_type_clean", self.clean(item.get("type", "")))

        score = 0
        query_words = query_clean.split()
        task_words = set(task_clean.split())
        category_words = set(categories_clean.split())
        query_word_set = set(query_words)

        # exact matches
        if query_clean == task_clean:
            score += 160

        if query_clean == slug_clean:
            score += 140

        if query_clean == categories_clean:
            score += 120

        # startswith / phrase
        if task_clean.startswith(query_clean) and query_clean:
            score += 90

        if slug_clean.startswith(query_clean) and query_clean:
            score += 80

        if categories_clean.startswith(query_clean) and query_clean:
            score += 60

        if query_clean in task_clean and query_clean:
            score += 65

        if query_clean in categories_clean and query_clean:
            score += 40

        if query_clean in slug_clean and query_clean:
            score += 35

        # word overlap
        score += len(query_word_set & task_words) * 10
        score += len(query_word_set & category_words) * 5

        # typo tolerance
        score += self.get_typo_similarity_bonus(query_clean, task_clean)
        score += max(
            0,
            self.get_typo_similarity_bonus(query_clean, slug_clean) - 10
        )

        # query intent preference
        if self.is_broad_query(query) and item_type == "category":
            score += 35

        if self.is_specific_query(query) and item_type == "task":
            score += 30

        # strong task preference for exact service-like phrases
        if len(query_words) >= 3 and query_clean == task_clean and item_type == "task":
            score += 50

        # urgent / budget / install / repair hints
        urgency_words = {"urgent", "quick", "asap", "immediately"}
        budget_words = {"cheap", "budget", "low cost", "affordable"}
        service_words = {"install", "repair", "replace", "remodel", "fix"}

        if any(w in query_clean for w in urgency_words):
            score += 5
        if any(w in query_clean for w in budget_words):
            score += 5
        if any(w in query_clean for w in service_words) and item_type == "task":
            score += 10

        return score

    def get_nearest_matches(self, query, limit=5):
        query_clean = self.clean(query)
        scored = []

        for item in self.metadata:
            task_clean = item.get("_task_clean", "")
            slug_clean = item.get("_slug_clean", "")
            categories_clean = item.get("_categories_clean", "")

            best_ratio = max(
                difflib.SequenceMatcher(None, query_clean, task_clean).ratio() if task_clean else 0,
                difflib.SequenceMatcher(None, query_clean, slug_clean).ratio() if slug_clean else 0,
                difflib.SequenceMatcher(None, query_clean, categories_clean).ratio() if categories_clean else 0
            )

            if best_ratio >= 0.55:
                clone = item.copy()
                clone["_fuzzy_ratio"] = best_ratio
                clone["resolved_url"] = self.get_task_url(clone)
                scored.append(clone)

        scored.sort(key=lambda x: x.get("_fuzzy_ratio", 0), reverse=True)

        results = []
        seen = set()

        for item in scored:
            key = (
                self.clean(item.get("task")),
                self.clean(item.get("type"))
            )
            if key in seen:
                continue
            seen.add(key)
            results.append(item)

        return results[:limit]

    def search(self, query, top_k=16):
        if not query.strip():
            return []

        query_vector = self.embedding_model.encode(
            [query],
            convert_to_numpy=True
        )
        query_vector = np.array(query_vector, dtype=np.float32)

        distances, indices = self.index.search(query_vector, top_k)

        candidates = []

        for idx in indices[0]:
            if idx == -1:
                continue

            item = self.metadata[idx].copy()
            item["resolved_url"] = self.get_task_url(item)
            item["_score"] = self.score_item(query, item)
            candidates.append(item)

        # fallback fuzzy candidates if semantic result weak
        fuzzy_candidates = self.get_nearest_matches(query, limit=6)
        for item in fuzzy_candidates:
            item["_score"] = max(item.get("_score", 0), self.score_item(query, item))
            candidates.append(item)

        candidates.sort(key=lambda x: x.get("_score", 0), reverse=True)

        results = []
        seen = set()

        for item in candidates:
            key = (
                self.clean(item.get("task")),
                self.clean(item.get("type"))
            )
            if key in seen:
                continue

            seen.add(key)
            results.append(item)

        return results[:8]

    def fallback(self, query, results, reason="No AI"):
        if not results:
            nearest = self.get_nearest_matches(query, limit=3)

            if not nearest:
                return (
                    "I couldn't find a strong match for your request. "
                    "Try describing the service in a simpler way, like repair, install, remodel, or the room/category name."
                )

            lines = [
                "I couldn't find an exact match, but these look close:",
                ""
            ]

            for i, item in enumerate(nearest, 1):
                task = item.get("task", "Service")
                lines.append(f"{i}. {task}")

            lines.append("")
            lines.append("Tell me if you want repair, installation, remodeling, or a broader category.")

            return "\n".join(lines)

        lines = [
            "I found some close matches that should help:",
            ""
        ]

        for i, item in enumerate(results[:3], 1):
            task = item.get("task", "Service")
            categories = item.get("categories", "")
            item_type = item.get("type", "").capitalize()

            if categories and self.clean(categories) != self.clean(task):
                lines.append(f"{i}. {task} ({item_type}) — Good fit for {categories}.")
            else:
                lines.append(f"{i}. {task} ({item_type})")

        lines.append("")
        lines.append(f"(Fallback reason: {reason})")
        lines.append("")
        lines.append("Tell me your budget, urgency, or whether this is repair or install.")

        return "\n".join(lines)

    def format_chat_history(self, chat_history):
        if not chat_history:
            return ""

        lines = []
        recent_messages = chat_history[-6:]

        for msg in recent_messages:
            role = str(msg.get("role", "")).strip().lower()
            text = str(msg.get("text", "")).strip()

            if not text:
                continue

            if role == "user":
                lines.append(f"User: {text}")
            else:
                lines.append(f"Assistant: {text}")

        return "\n".join(lines)

    def ask_ai(self, query, results, chat_history=None):
        if not self.client:
            return self.fallback(query, results, "API key not loaded")

        context = ""
        previous_conversation = self.format_chat_history(chat_history)

        for i, item in enumerate(results[:5], 1):
            context += f"""
Ref {i}
Task: {item.get("task", "")}
Type: {item.get("type", "")}
Categories: {item.get("categories", "")}
Slug: {item.get("slug", "")}
Source: {item.get("resolved_url", self.get_task_url(item))}
"""

        prompt = f"""
You are FindPros AI Assistant, a premium world-class conversational AI for home improvement, repairs, remodeling, and local professional services.

Your job is to understand what the user truly wants, then respond in the same polished, natural, intelligent style as a top-tier modern AI assistant.

CORE RULES:
1. Sound human, warm, smart, confident, and natural.
2. Reply in Hinglish if the user writes in Hinglish. Reply in English if the user writes in English.
3. Never sound robotic, repetitive, or like a search engine.
4. Use ONLY the provided context.
5. Recommend the best 2 or 3 relevant services naturally.
6. Prefer exact task matches over broad category matches when available.
7. If no perfect match exists, confidently suggest the closest useful options.
8. Keep the response short, polished, and easy to read.
9. Do not show raw URLs in the answer.
10. End with one short follow-up question or next helpful step.
11. Never start with phrases like:
   - Based on your query
   - I found these services
   - Here are the top options
   - I recommend the following

Previous Conversation:
{previous_conversation}

Current User Query:
{query}

Available Context:
{context}
"""

        try:
            print("Sending AI Request...")

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a premium assistant for home service recommendations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=260
            )

            answer = response.choices[0].message.content.strip()

            if not answer:
                return self.fallback(query, results, "Empty AI response")

            print("AI Success")
            return answer

        except Exception as e:
            print("AI ERROR:", e)
            return self.fallback(query, results, str(e))

    def reply(self, query, chat_history=None):
        query = query.strip()

        if not query:
            return {
                "answer": "Please enter a query.",
                "references": [],
                "recommendations": [],
                "top_result": None,
                "status": "empty_query"
            }

        results = self.search(query)

        if not results:
            fallback_answer = self.fallback(query, [], "No results")
            self.log_query(query, results_count=0, matched_tasks=[])

            return {
                "answer": fallback_answer,
                "references": [],
                "recommendations": [],
                "top_result": None,
                "status": "no_match"
            }

        answer = self.ask_ai(query, results, chat_history)

        references = []
        recommendations = []
        seen_recommendations = set()

        for i, item in enumerate(results[:5], 1):
            task = item.get("task", "Service")
            url = item.get("resolved_url", self.get_task_url(item))
            item_type = item.get("type", "task")

            references.append({
                "ref": i,
                "id": item.get("id"),
                "task": task,
                "type": item_type,
                "url": url
            })

            rec_key = (
                self.clean(task),
                self.clean(item_type)
            )

            if rec_key not in seen_recommendations and len(recommendations) < 3:
                seen_recommendations.add(rec_key)
                recommendations.append({
                    "id": item.get("id"),
                    "task": task,
                    "type": item_type,
                    "url": url
                })

        matched_tasks = [item.get("task", "") for item in results[:5]]
        self.log_query(
            query,
            results_count=len(results),
            matched_tasks=matched_tasks
        )

        top_result = None
        if results:
            top_item = results[0]
            top_result = {
                "id": top_item.get("id"),
                "task": top_item.get("task"),
                "type": top_item.get("type"),
                "url": top_item.get("resolved_url", self.get_task_url(top_item))
            }

        return {
            "answer": answer,
            "references": references,
            "recommendations": recommendations,
            "top_result": top_result,
            "status": "success"
        }