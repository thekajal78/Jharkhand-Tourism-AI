# AI/ML Module —  Jharkhand Explore AI
###  This folder is YOUR responsibility as the AI/ML developer

---

## 📁 Folder Structure (Every file explained)

```
ai_ml/
│
├── main.py                          ← Entry point. Starts FastAPI on port 8001.
│                                      Loads all 3 AI models on startup.
│
├── requirements.txt                 ← All Python packages you need
├── Dockerfile                       ← How to containerize this service
│
├── services/                        ← YOUR CORE AI CODE (most important folder)
│   ├── clip_service.py              ← CLIP model + FAISS visual search
│   ├── recommendation_service.py   ← Collaborative + content-based filtering
│   └── chatbot_service.py          ← Intent detection + multilingual NLP
│
├── routers/                         ← API endpoints (thin layer over services)
│   ├── clip_router.py              ← POST /clip/search/text, /clip/search/image
│   ├── recommendation_router.py    ← GET /recommend/user/{id}, /recommend/popular
│   └── chatbot_router.py           ← POST /chat/message, /chat/sentiment
│
├── models/                          ← Model weights (downloaded at runtime)
│   └── clip/                       ← ViT-B/32.pt goes here (~350MB, auto-downloaded)
│
└── tests/                           ← Your test files
    ├── test_clip.py                ← Tests for CLIP + FAISS
    ├── test_recommendations.py     ← Tests for recommendation engine
    └── test_chatbot.py             ← Tests for chatbot + NLP
```

---

## 🚀 How to Run (Local Development)

```bash
# 1. Go to ai_ml folder
cd ai_ml

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the service
uvicorn main:app --reload --port 8001

# 4. Open API docs in browser
# http://localhost:8001/docs
```

On **first run**, CLIP model downloads automatically (~350MB). After that it loads from `models/clip/`.

---

## 🧪 How to Run Tests

```bash
cd ai_ml
pytest tests/ -v
```

---

## 🔗 How This Service Connects to the Rest of the Project

```
Tourist's Browser (port 3000)
         ↓
    React Frontend
         ↓
  FastAPI Backend (port 8000)    ← Other team's code
         ↓
  AI/ML Service (port 8001)      ← YOUR code
```

The backend calls YOUR endpoints like:
- `POST http://ai_service:8001/clip/search/text`   — when tourist searches by text
- `POST http://ai_service:8001/clip/search/image`  — when tourist uploads a photo
- `GET  http://ai_service:8001/recommend/user/42`  — to get personalized suggestions
- `POST http://ai_service:8001/chat/message`       — when tourist sends a chat message

---

## 🧠 Understanding the 3 AI Systems

### 1. CLIP (clip_service.py)
```
Tourist uploads photo of waterfall
         ↓
CLIP encodes image → [0.2, 0.8, 0.1, ...] (512 numbers)
         ↓
FAISS searches: "which destination vector is closest?"
         ↓
Returns: "Hundru Falls (95% match), Dassam Falls (89% match)"
```

### 2. Recommendations (recommendation_service.py)
```
User_42 liked: Hundru Falls, Netarhat, Betla
         ↓
Collaborative: "User_15 also liked these + loved Rajrappa"
Content-based: "These 3 share eco/nature features → suggest similar"
         ↓
Hybrid result: "We think you'll love Rajrappa (score: 0.92)"
```

### 3. Chatbot (chatbot_service.py)
```
Tourist types: "मुझे झरने दिखाओ" (Hindi)
         ↓
Language detection: Hindi (Devanagari script detected)
         ↓
IndicTrans2 translation: "Show me waterfalls"
         ↓
Intent: FIND_DESTINATION (confidence: 0.9)
Entity: {locations: [], category: "waterfall"}
         ↓
Response generated in English
         ↓
IndicTrans2 translates back to Hindi
         ↓
Tourist gets: "यहाँ झारखंड के सुंदर झरने हैं..."
```

---

## 📦 Key Libraries

| Library | Why We Use It |
|---------|--------------|
| `openai-clip` | The CLIP model itself |
| `torch` | Runs the neural network |
| `faiss-cpu` | Fast vector similarity search |
| `transformers` | IndicTrans2 for tribal languages |
| `scikit-learn` | Cosine similarity for recommendations |
| `pandas/numpy` | Data manipulation |

---

## ⚡ Model Download Summary

| Model | Size | Downloads To | Auto-download? |
|-------|------|-------------|----------------|
| CLIP ViT-B/32 | ~350MB | `models/clip/` | ✅ Yes |
| IndicTrans2 | ~500MB | `models/indictrans/` | ✅ Yes |
| Recommendation | ~1MB | `models/recommendation_model.pkl` | ✅ Built on first run |

---

## 🆘 Common Issues

**Model not downloading?**
```bash
# Check internet, then manually download:
python -c "import clip; clip.load('ViT-B/32', download_root='./models/clip')"
```

**FAISS not installed?**
```bash
pip install faiss-cpu   # CPU version
pip install faiss-gpu   # GPU version (if you have NVIDIA GPU)
```

**IndicTrans2 too slow to load?**
The service still works without it — falls back to English-only responses.
Tribal language translation is a "nice to have" for production.
