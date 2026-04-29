# 🤖 AI Task Manager

> Multi-Agent AI Task Manager powered by **LangGraph** + **Gemini** + **FastAPI**

A modern web app where 4 specialized AI agents collaborate to tackle any task you throw at them.

## ✨ Features

- **4 Specialized Agents** — Planner → Researcher → Writer → Reviewer
- **Real-time streaming** via Server-Sent Events (SSE)
- **Modern dark UI** built with React (no build step)
- **Gemini 1.5 Flash** (free tier) via LangGraph
- **Vercel** deployment for the frontend
- **Configurable backend URL** via Settings

## 🏗️ Architecture

```
Frontend (Vercel)          Backend (any Python host)
┌─────────────────┐        ┌──────────────────────┐
│  React + Babel  │ SSE    │  FastAPI + LangGraph  │
│  (index.html)   │◄──────►│  Gemini 1.5 Flash     │
└─────────────────┘        └──────────────────────┘
```

## 🚀 Deploy

### Frontend → Vercel

1. Fork / clone this repo
2. Go to [vercel.com](https://vercel.com) → New Project → Import this repo
3. Vercel will auto-detect `vercel.json` and deploy `frontend/index.html`
4. After deploy, open the app → click **⚙️ Settings** → set your backend URL

### Backend → Railway / Render / Fly.io

```bash
cd backend
pip install -r requirements.txt
# Create .env from .env.example and add your GEMINI_API_KEY
uvicorn main:app --host 0.0.0.0 --port 8000
```

**Environment variables:**
| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Your [Google AI Studio](https://aistudio.google.com/app/apikey) free API key |

## 🛠️ Local Development

```bash
# Backend
cd backend
pip install -r requirements.txt
cp .env.example .env  # add your GEMINI_API_KEY
uvicorn main:app --reload

# Frontend — just open in browser
open frontend/index.html
# or serve with: python -m http.server 3000 (from frontend/)
```

## 🤖 Agent Pipeline

| Agent | Role |
|---|---|
| 🗺️ **Planner** | Breaks task into 3-4 actionable steps |
| 🔍 **Researcher** | Gathers insights and best practices |
| ✍️ **Writer** | Creates a comprehensive draft |
| ✅ **Reviewer** | Polishes and finalizes the output |

## 📁 Structure

```
ai-task-manager/
├── frontend/
│   └── index.html      # React SPA (no build needed)
├── backend/
│   ├── main.py         # FastAPI + SSE streaming
│   ├── agents.py       # LangGraph multi-agent graph
│   ├── requirements.txt
│   └── .env.example
└── vercel.json         # Vercel deployment config
```
