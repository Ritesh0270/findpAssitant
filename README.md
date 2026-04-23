# FindPros AI Assistant

FindPros AI Assistant is an AI-powered smart search and lead-generation assistant built for service marketplace websites. It helps users quickly find the right home improvement, repair, construction, remodeling, and maintenance services through natural language chat.

Instead of manually browsing categories, users can simply type queries like:

- I want roof repair
- Need bathroom remodel
- TV wall mount karwana hai
- Window repair needed

The system understands intent, searches service data intelligently, and returns the best matching task/service page.

---

# Features

## AI Smart Search
Uses LLM + semantic search to understand user intent.

## Natural Language Queries
Users can search like chatting with ChatGPT.

## Multi-language Support
Supports English + Hindi mixed queries.

## Fast Result Matching
Uses FAISS vector search for instant service matching.

## Smart Redirect
Returns correct task/category URL pages.

## Chat UI
Modern ChatGPT-style interface built using HTML/CSS/JavaScript.

## Query Logs
Stores search logs for analytics and future improvements.

---

# Tech Stack

## Frontend
- HTML
- CSS
- JavaScript

## Backend
- Python
- Flask

## AI / Search
- Llama 3.3 70B Versatile
- Sentence Transformers
- all-MiniLM-L6-v2 Embedding Model
- FAISS Vector Search

## Data
- JSON Metadata
- Task / Category Mapping

---

# Project Structure

```text
FindPros/
│── app.py
│── aichat.py
│── fetch.py
│── index.py
│── documents.json
│── metadata.json
│── task_index.faiss
│── query_logs.json
│── templates/
│   └── index.html
│── static/
│   ├── style.css
│   └── script.js
│── .env
│── README.md

## Screenshots

### Homepage
![Home](img/home.png)

### Chat Interface
![Chat](img/chat.png)

### Search Results
![Result](img/result.png)
