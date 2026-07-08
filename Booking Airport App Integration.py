Airport App Integration — API, Autocomplete, AI Recommender, Flight Filtering

This document contains a complete, ready-to-run integration plan and code snippets to add the **global airports dataset** to a modern application. It includes:

* Backend: FastAPI (Python) with endpoints for search, autocomplete, recommender and flight filtering
* Database: SQLite + example schema and seed script (easy to swap to Postgres)
* Frontend: React component (single-file) with autocomplete, airport selection and calls to recommender
* AI Recommender: Lightweight scoring model using TF–IDF + simple business rules (easy to replace with embeddings)
* Docker: Dockerfile + docker-compose for local dev

---
 Overview

Architecture:

* FastAPI serves REST endpoints and a small vector-like recommender using scikit-learn TF–IDF.
* SQLite stores `airports` table (`code, name, city, country, type, popularity`) — `type` = tourist/cargo/private
* React frontend consumes `/autocomplete`, `/airports`, `/recommend` and `/flights/filter`.

---

Backend — `app/main.py`


app/main.py
from fastapi import FastAPI, Query
from pydantic import BaseModel
import sqlite3
from typing import List, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import json

app = FastAPI(title="Airports API")
DB = "./data/airports.db"

--- Utility: DB connection ---
def conn():
    return sqlite3.connect(DB)

--- Load dataset into memory for recommender ---
def load_airports():
    c = conn()
    rows = c.execute("SELECT code, name, city, country, type, popularity FROM airports").fetchall()
    c.close()
    airports = [ {"code":r[0],"name":r[1],"city":r[2],"country":r[3],"type":r[4],"popularity":r[5]} for r in rows]
    return airports

_airports_cache = load_airports()
_corpus = [f"{a['name']} {a['city']} {a['country']}" for a in _airports_cache]
_vectorizer = TfidfVectorizer(ngram_range=(1,2), max_features=20000)
if _corpus:
    _X = _vectorizer.fit_transform(_corpus)
else:
    _X = None

--- Models ---
class AirportOut(BaseModel):
    code: str
    name: str
    city: str
    country: str

class RecommendRequest(BaseModel):
    q: Optional[str] = None
    country: Optional[str] = None
    type: Optional[str] = None  # tourist/cargo/private
    top_k: Optional[int] = 5

--- Endpoints ---
@app.get('/airports', response_model=List[AirportOut])
def airports(q: Optional[str] = Query(None), country: Optional[str] = Query(None), type: Optional[str] = Query(None), limit: int = 50):
    c = conn()
    sql = "SELECT code, name, city, country FROM airports WHERE 1=1"
    params = []
    if country:
        sql += " AND country = ?"
        params.append(country)
    if type:
        sql += " AND type = ?"
        params.append(type)
    if q:
        sql += " AND (name LIKE ? OR city LIKE ? OR code LIKE ? OR country LIKE ?)"
        like = f"%{q}%"
        params.extend([like, like, like, like])
    sql += " LIMIT ?"
    params.append(limit)
    rows = c.execute(sql, params).fetchall()
    c.close()
    return [ {"code":r[0],"name":r[1],"city":r[2],"country":r[3]} for r in rows ]

@app.get('/autocomplete')
def autocomplete(q: str = Query(...), limit: int = 8):
    """Simple autocomplete: search code/name/city starting with query"""
    qlow = q.lower()
    results = []
    for a in _airports_cache:
        if a['code'].lower().startswith(qlow) or a['name'].lower().startswith(qlow) or a['city'].lower().startswith(qlow):
            results.append({"code":a['code'],"name":a['name'],"city":a['city'],"country":a['country']})
            if len(results)>=limit:
                break
    return results

@app.post('/recommend')
def recommend(req: RecommendRequest):
    """Lightweight TF-IDF based recommender + business rules.
    Scores by text-similarity and boosts by popularity and type match.
    """
    if _X is None:
        return []
    query_text = ""
    if req.q:
        query_text += req.q + " "
    if req.country:
        query_text += req.country
    qv = _vectorizer.transform([query_text])
    sims = (qv @ _X.T).toarray()[0]  # cosine-like via dot on normalized TF-IDF
    scores = []
    for i,a in enumerate(_airports_cache):
        score = float(sims[i])
        # boost by type match
        if req.type and a['type']==req.type:
            score *= 1.25
        # boost by popularity (0-1 stored)
        score *= (1 + a.get('popularity',0))
        scores.append((score, a))
    scores.sort(key=lambda x: x[0], reverse=True)
    topk = req.top_k or 5
    return [ {"code":a['code'],"name":a['name'],"city":a['city'],"country":a['country'],"score":s} for s,a in scores[:topk] ]

--- Flight filtering example endpoint (stub) ---
class FlightFilterRequest(BaseModel):
    origin: str
    destination: str
    depart_date: Optional[str]
    return_date: Optional[str]
    cabin: Optional[str] = 'economy'
    airlines: Optional[List[str]] = None
    max_stops: Optional[int] = 2

@app.post('/flights/filter')
def flight_filter(req: FlightFilterRequest):
    # This is a stub showing how to filter flights: return a mock response structure
    # In production this would call an external flight API (Amadeus, Sabre, Skyscanner)
    return {
        "origin": req.origin,
        "destination": req.destination,
        "results": [
            {"flight": "EX123", "airline": "DemoAir", "stops": 0, "price": 420, "currency": "USD"}
        ]
    }
  
Database schema + seed script `data/seed_db.py`

python
 data/seed_db.py
import sqlite3
DB = './data/airports.db'
conn = sqlite3.connect(DB)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS airports(
    code TEXT PRIMARY KEY,
    name TEXT,
    city TEXT,
    country TEXT,
    type TEXT,
    popularity REAL
)") Insert a few seed rows (extend with your global dataset)
seed = [
    ("NBO","Jomo Kenyatta Intl","Nairobi","Kenya","tourist",0.9),
    ("JFK","John F. Kennedy Intl","New York","USA","tourist",1.0),
    ("LHR","Heathrow","London","UK","tourist",1.0),
    ("DXB","Dubai Intl","Dubai","UAE","tourist",1.0),
    ("CDG","Charles de Gaulle","Paris","France","tourist",0.95),
]
c.executemany('INSERT OR REPLACE INTO airports(code,name,city,country,type,popularity) VALUES(?,?,?,?,?,?)', seed)
conn.commit()
conn.close()
```

> **Tip**: load your full A→Z dataset into this table using the same INSERT pattern.

---

## Frontend — React `src/components/AirportPicker.jsx`

```jsx
import React, {useState, useEffect, useRef} from 'react';

export default function AirportPicker({onSelect}){
  const [q, setQ] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const activeReq = useRef(null);

  useEffect(()=>{
    if(!q || q.length<1){ setSuggestions([]); return; }
    const controller = new AbortController();
    activeReq.current = controller;
    fetch(`/autocomplete?q=${encodeURIComponent(q)}&limit=8`, {signal: controller.signal})
      .then(r=>r.json())
      .then(data=> setSuggestions(data))
      .catch(e=> {/* ignore aborted */});
    return ()=> controller.abort();
  }, [q]);

  return (
    <div className="airport-picker">
      <input placeholder="Search airport or city (e.g. NBO, Nairobi)" value={q} onChange={e=>setQ(e.target.value)} />
      <ul className="suggestions">
        {suggestions.map(s => (
          <li key={s.code} onClick={()=>{ onSelect(s); setQ(''); setSuggestions([]); }}>
            <strong>{s.code}</strong> — {s.name} · {s.city}, {s.country}
          </li>
        ))}
      </ul>
    </div>
  );
}


Frontend — calling the recommender

js
Example usage in React after user picks preferences
async function getRecommendations({q,country,type,top_k=5}){
  const res = await fetch('/recommend', {
    method: 'POST', headers: {'Content-Type':'application/json'},
    body: JSON.stringify({q,country,type,top_k})
  });
  return res.json();
}


---

Docker & Run

**Dockerfile (backend)**

Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY ./app /app
COPY ./data /app/data
RUN pip install fastapi uvicorn scikit-learn
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
```

**docker-compose.yml**

```yaml
version: '3.8'
services:
  api:
    build: .
    ports:
      - '8000:8000'
    volumes:
      - ./data:/app/data
```

Run locally:

bash
python data/seed_db.py
uvicorn app.main:app --reload

Open: `http://localhost:8000/docs` for interactive API docs.

---

Notes & Next Steps

* **Scalability**: move the DB to Postgres and build an embeddings index (Milvus/Elastic/FAISS) for a true vector-based recommender.
* **Realtime Autocomplete**: add Redis caching & prefix-search index (trie) or use ElasticSearch for production.
* **Flight data**: integrate Amadeus/Sabre/Skyscanner APIs for real flight search & booking.
* **Security**: add auth, rate-limiting, input sanitation.
* **UI polish**: add fuzzy matching, keyboard navigation, and highlights.

---

If you want, I can now:

* Generate full runnable repo (zipped with sample data)
* Convert recommender to an embeddings-based service (OpenAI / local embeddings)
* Add Postgres + Alembic migrations

Say which you want next and I’ll build it.
