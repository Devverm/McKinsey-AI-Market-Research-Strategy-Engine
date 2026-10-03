# McKinsey AI Market Research & Strategy Engine

> An agentic AI system that researches a market, validates its evidence, and turns it into consulting-style strategic insight.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688?logo=fastapi&logoColor=white)
![LangGraph](https://img.shields.io/badge/LangGraph-orchestration-1C3C3C)
![Gemini](https://img.shields.io/badge/Google-Gemini-4285F4?logo=google&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-14-000000?logo=nextdotjs&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-vector%20memory-FF6F00)

---

## Overview

The **McKinsey AI Market Research & Strategy Engine** automates the first, most time-consuming stage of strategy work: market research. Given a research question, a team of cooperating AI agents plans the investigation, gathers sources from the live web, checks every claim against its evidence, and synthesizes the verified findings into structured, consultant-grade strategic output.

Instead of a single prompt-and-pray LLM call, the engine runs a **multi-step agent workflow** (built on LangGraph). Only evidence that passes validation is kept, and that validated evidence is stored in a **persistent vector memory**, so each new research job can build on what the system has already learned.

> **Disclaimer:** This is an independent project. It is not affiliated with, endorsed by, or sponsored by McKinsey & Company.

## Key Features

- **Multi-agent research workflow**: LangGraph coordinates specialised agents through a repeatable research pipeline.
- **Live web research**: Tavily-powered search pulls current, citable sources.
- **Evidence validation**: Claims are checked for support before they are trusted or stored.
- **Persistent evidence memory**: Validated claims are embedded and stored in ChromaDB for retrieval in future jobs.
- **Gemini end to end**: Reasoning and embeddings both run on Google Gemini, keeping the stack on a single LLM provider.
- **Asynchronous research jobs**: Long-running research runs as tracked jobs, persisted in a local SQLite database.
- **Modern web UI**: A Next.js + Tailwind frontend for submitting questions and reading results.
- **REST API**: A typed FastAPI backend with Pydantic models and settings management.

## Architecture

```
┌────────────────┐      REST       ┌───────────────────────────────┐
│  Next.js UI    │ ──────────────▶ │  FastAPI backend              │
│  (frontend/)   │ ◀────────────── │  (backend/)                   │
└────────────────┘                 │  jobs · config · API routes   │
                                   └──────────────┬────────────────┘
                                                  │
                                   ┌──────────────▼────────────────┐
                                   │  LangGraph agent pipeline     │
                                   │  (ai/)                        │
                                   │  plan → search → validate →   │
                                   │  synthesize                   │
                                   └───────┬───────────────┬───────┘
                                           │               │
                              ┌────────────▼───┐   ┌───────▼──────────────┐
                              │ Tavily Search  │   │ ChromaDB evidence    │
                              │ (live web)     │   │ memory (chroma_db/)  │
                              └────────────────┘   └──────────────────────┘
                                           │
                                   ┌───────▼────────┐
                                   │ Google Gemini  │
                                   │ LLM + embeddings│
                                   └────────────────┘
```

## Tech Stack

| Layer | Technology |
| --- | --- |
| API | FastAPI, Uvicorn, Pydantic v2, pydantic-settings |
| Agent orchestration | LangGraph |
| LLM & embeddings | Google Gemini (`google-genai`) |
| Web search | Tavily (`tavily-python`) |
| Vector memory | ChromaDB (persistent, local) |
| Job store | SQLite (`research_jobs.db`) |
| Frontend | Next.js 14, React 18, TypeScript, Tailwind CSS |
| Testing | pytest |

## Project Structure

```
.
├── ai/                  # Agents, LangGraph workflow, and memory (ChromaDB store)
├── backend/             # FastAPI app, core config, API and job handling
├── frontend/            # Next.js UI components (app also configured at repo root)
├── chroma_db/           # Persistent vector store for validated evidence
├── data/                # Project data
├── deployment/          # Deployment configuration
├── docs/                # Additional documentation
├── logs/                # Runtime logs
├── research_jobs.db     # SQLite database of research jobs
├── requirements.txt     # Python dependencies
├── package.json         # Frontend dependencies and scripts
├── .env.example         # Backend environment template
└── .env.local.example   # Frontend environment template
```

## Getting Started

### Prerequisites

- Python 3.11 or newer
- Node.js 18 or newer
- A [Google Gemini API key](https://aistudio.google.com/)
- A [Tavily API key](https://tavily.com/)

### 1. Clone the repository

```bash
git clone https://github.com/Devverm/McKinsey-AI-Market-Research-Strategy-Engine.git
cd McKinsey-AI-Market-Research-Strategy-Engine
```

### 2. Configure environment variables

```bash
cp .env.example .env
cp .env.local.example .env.local
```

Open `.env` and add your keys. The backend reads its settings through `backend/core/config.py`. At minimum you will need:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_EMBEDDING_MODEL=your_embedding_model_name
TAVILY_API_KEY=your_tavily_api_key
CHROMA_DB_PATH=./chroma_db
```

Never commit your real `.env` file.

### 3. Run the backend

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

uvicorn backend.main:app --reload --port 8000
```

The interactive API docs are then available at `http://localhost:8000/docs`.

### 4. Run the frontend

```bash
npm install
npm run dev
```

Open `http://localhost:3000` in your browser.

## Usage

1. Open the web app and enter a market research question, for example: *"What is the competitive landscape for electric two-wheelers in India, and where are the strategic openings?"*
2. The engine creates a research job and the agent pipeline starts working.
3. The agents search the web, extract claims, and validate each one against its sources.
4. Validated evidence is saved to memory, and a structured strategic summary is returned.

## Testing

```bash
pytest
```

## Roadmap

- [ ] Export reports to PDF and PowerPoint
- [ ] Standard strategy frameworks (SWOT, Porter's Five Forces, TAM/SAM/SOM)
- [ ] Source quality and confidence scoring
- [ ] Streaming progress updates in the UI
- [ ] Docker-based deployment

## Contributing

Contributions are welcome. Please open an issue to discuss what you would like to change, then submit a pull request.

1. Fork the repo
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Commit your changes and push the branch
4. Open a pull request

## License

No license has been specified yet. Add a `LICENSE` file (for example MIT) to define how others may use this project.

## Acknowledgements

Built with [FastAPI](https://fastapi.tiangolo.com/), [LangGraph](https://langchain-ai.github.io/langgraph/), [Google Gemini](https://ai.google.dev/), [Tavily](https://tavily.com/), [ChromaDB](https://www.trychroma.com/), and [Next.js](https://nextjs.org/).
