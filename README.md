<div align="center">
  <img src="frontend/public/Higgins.png" alt="Higgins" width="180" style="border-radius: 50%;" />

  # Higgins

  ### *"I don't accept tips."*

  **Your own private major-domo — a locally-run AI assistant who manages your digital estate with the precision of a former British Regimental Sergeant Major and the memory of an elephant.**

  [![License: MIT](https://img.shields.io/badge/License-MIT-a855f7.svg)](LICENSE)
  [![Python](https://img.shields.io/badge/Python-3.10+-3776AB.svg)](https://python.org)
  [![React](https://img.shields.io/badge/React-19-61DAFB.svg)](https://react.dev)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com)

  ---

  *Named after Jonathan Quayle Higgins III — the fastidious, cultured, and impossibly well-organized estate manager from Magnum, P.I. — this Higgins manages your information with the same dedication, wit, and unwavering attention to detail. He may occasionally judge your file-naming conventions, but he'll never let you down.*

</div>

---

## ✨ What Is Higgins?

Higgins is a **fully local, self-hosted AI assistant** with a beautiful glass-morphism chat interface. No cloud subscriptions, no data leaving your machine, no third-party middlemen poking through your documents. Just you and Higgins, keeping the estate in order.

Think of it as your own Robin's Nest — except instead of a beachside Hawaiian mansion, it's your local machine, and instead of Zeus and Apollo guarding the gate, it's your firewall.

> *"But then, what can one expect from simple, primitive minds that overload at the drop of a multi-dependent, clause-declarative sentence?"*
>
> — Higgins, on other AI assistants, probably.

---

## 🏛️ Features

### 💬 Multi-Model Chat
Higgins doesn't play favorites. Connect to the model that suits the task:
- **Google Gemini** (Flash, Pro, and the full lineup)
- **OpenRouter** (access hundreds of models — Claude, GPT, Llama, Mistral, and more)
- **Ollama** (fully local models, no API key needed)

Switch models mid-conversation from the sidebar. Higgins adapts.

### 🌐 Web Search
Real-time web search baked directly into conversations. Higgins will search the web, synthesize results, and cite his sources — collapsible at the bottom of each reply so they don't clutter the conversation. Supports **DuckDuckGo** (default, no key needed), **Tavily**, **Brave**, **Google**, and **Serper**.

### 🧠 Local Brain (RAG)
Point Higgins at a folder of your documents and he'll index them into a local vector store. When you ask questions, he automatically retrieves relevant context from your personal knowledge base. Your documents never leave your machine.

### 💾 Memory & Preferences
Tell Higgins *"remember, I don't like tuna"* and he will. Permanently. Memories are automatically extracted from conversation and stored locally. Higgins uses them to personalize every future response — just like the real Higgins, who never forgot a single one of Magnum's transgressions.

### 📁 Project Workspaces
Select any folder as an active project. Higgins will:
- Auto-create and maintain a **`GEMINI.MD`** status file for project context
- Read your entire file tree and use it as context in conversations
- **Write and edit files** directly from chat responses
- Show a sliding file explorer panel with a built-in code editor

### 📌 Chat Management
- **Pin** important conversations
- **Archive** old ones to keep the sidebar clean
- **Rename** chats with a double-click
- Full **Markdown rendering** with syntax highlighting in responses

### ⏹️ Stop Generation
Changed your mind mid-response? Hit the **Stop** button to cancel immediately and keep whatever was generated so far.

---

## 🖼️ The Interface

A dark, glass-morphism UI that would make even Higgins approve — and he's notoriously hard to impress. Three-panel layout with a collapsible sidebar, main chat workspace, and an optional project explorer panel.

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+**
- **Node.js 18+**
- At least one API key (Gemini or OpenRouter), _or_ [Ollama](https://ollama.com) running locally

### Setup

```bash
# Clone the estate
git clone https://github.com/digger3927/Higgins.git
cd Higgins

# Set up the backend
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..

# Set up the frontend
cd frontend
npm install
cd ..
```

### Run

```bash
# One command to rule them all
./start.sh
```

That's it. Open [http://localhost:5173](http://localhost:5173) and Higgins will be waiting.

On first launch, click **Settings** in the sidebar to configure your API keys. Higgins will remember them across restarts.

---

## 🗂️ Project Structure

```
Higgins/
├── backend/
│   ├── main.py              # FastAPI server — the brains of the operation
│   ├── requirements.txt     # Python dependencies
│   ├── config/              # Auto-created: settings, chats, memories
│   └── venv/                # Python virtual environment
├── frontend/
│   ├── src/
│   │   ├── App.tsx          # The entire React UI
│   │   └── App.css          # Glass-morphism design system
│   └── public/
│       └── Higgins.png      # The man himself
├── start.sh                 # Single launcher script
└── README.md                # You are here
```

---

## ⚙️ Configuration

All settings are managed through the **Settings** panel in the UI. No `.env` files to wrestle with.

| Setting | Description |
|---|---|
| **Gemini API Key** | For Google Gemini models |
| **OpenRouter API Key** | For OpenRouter model catalog |
| **Ollama** | Auto-detected if running locally |
| **Search Provider** | DuckDuckGo (default), Tavily, Brave, Google, Serper |
| **Local Brain Directory** | Folder of documents to index for RAG |
| **Memory & Prefs** | View, add, and manage stored memories |

---

## 🧰 Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 19, TypeScript, Vite, Lucide Icons |
| **Backend** | Python, FastAPI, Uvicorn |
| **LLM APIs** | Google Gemini, OpenRouter, Ollama |
| **Search** | DuckDuckGo, Tavily, Brave, Google, Serper |
| **Styling** | Custom CSS with glass-morphism design system |

---

## 🔒 Privacy

Higgins runs entirely on your machine. Your chats, memories, documents, and API keys are stored locally in `backend/config/` and never transmitted anywhere except to the LLM API you choose. If you run Ollama, everything stays on your hardware — no network calls at all.

---

## 🎩 Why "Higgins"?

In *Magnum, P.I.*, Jonathan Quayle Higgins III was the impossibly refined, endlessly knowledgeable estate manager who kept Robin's Nest running with military precision. He had an anecdote for every occasion, a solution for every problem, and an opinion on everything (especially Magnum's wardrobe choices).

This Higgins carries on that tradition — managing your digital estate with the same meticulous care, remembering your preferences with unwavering loyalty, and organizing your projects with the discipline of a decorated Regimental Sergeant Major.

He just does it with neural networks instead of Dobermans.

> *"Sometimes you amaze me, Magnum, truly. Your intuitive grasp of human nature is so... so..."*
> *"Perceptive?"*
> *"Pre-adolescent."*

---

## 📄 License

MIT — do whatever you like with it. Higgins may disapprove, but he'll allow it.

---

<div align="center">
  <sub>Built with ☕, 🌺, and the spirit of Robin's Nest.</sub>
</div>
