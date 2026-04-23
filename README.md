# FindPros AI Assistant (AI Smart Search Project)

## Overview

FindPros AI Assistant is an AI-powered smart chatbot built for service marketplace websites. It helps users quickly find the right home improvement, repair, remodeling, maintenance, and household services through natural language queries.

Instead of manually browsing multiple categories, users can simply type their needs like chatting with an assistant.

The system intelligently understands user intent, searches relevant services, and returns the best matching task or service page instantly.

---

## Features

* AI-powered smart search  
* Natural language query support  
* Hindi + English mixed language support  
* Fast semantic search using FAISS  
* Accurate task/category matching  
* Smart redirect to correct service page  
* Typo tolerant search  
* ChatGPT-style responsive UI  
* Recent chat / rename / delete chat  
* Query logging & analytics support  

---

## Tech Stack

* Python  
* Flask  
* HTML  
* CSS  
* JavaScript  
* FAISS  
* Sentence Transformers  
* Llama 3.3 70B Versatile  
* JSON Data Storage  

---

## Project Workflow

1. User enters query in chatbot  
2. Frontend sends request to Flask backend  
3. Query converted into embeddings  
4. FAISS searches nearest matching tasks  
5. AI understands user intent  
6. Best service results selected  
7. Response + redirect link returned to user  

---

## Installation & Setup

### 1. Clone Repository

```bash
git clone https://github.com/Ritesh0270/findpAssitant.git
cd findpAssitant
```

### 2. Create Virtual Environment

```bash
python -m venv venv
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run Application

```bash
python app.py
```

---

## Future Improvements

* Voice search assistant  
* Nearby professionals search  
* WhatsApp chatbot integration  
* Live booking system  
* User login dashboard  
* Admin analytics panel  
* Image upload based service detection  
* Multilingual expansion  
* AI recommendations / upselling  
* Cloud deployment scalability  

---

## Summary

FindPros AI Assistant demonstrates how AI + semantic search can improve service discovery in marketplace platforms. It provides users with faster, smarter, and more accurate results while increasing conversions and user satisfaction.

This project can evolve into a full AI sales assistant for service businesses.

---

## Snapshot of UI

![Demo1](img/home.png)
![Demo2](img/chat.png)
![Demo3](img/result.png)
