import os
import sys
import json
import logging
import asyncio
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deep_research_engine.config import config as dr_config, RunMode, OutputFormat, LLMProvider
from deep_research_engine.engine_router import search_engine, inference_engine
from deep_research_engine.research_loop import run_research, ResearchState

logger = logging.getLogger("higgins-deep-research")

RESEARCH_SESSIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research_sessions.json")

_sessions_registry: Dict[str, Dict[str, Any]] = {}

def load_research_sessions() -> Dict[str, Any]:
    if os.path.exists(RESEARCH_SESSIONS_FILE):
        try:
            with open(RESEARCH_SESSIONS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading research sessions: {e}")
    return {"sessions": {}}

def save_research_sessions(db: Dict[str, Any]):
    try:
        with open(RESEARCH_SESSIONS_FILE, "w") as f:
            json.dump(db, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving research sessions: {e}")

try:
    _sessions_registry = load_research_sessions().get("sessions", {})
except Exception as e:
    logger.error(f"Failed to load sessions on module load: {e}")

def run_deep_research_task(session_id: str, query: str, model_name: str, max_rounds: int, config_opts: Dict[str, Any]):
    _sessions_registry[session_id] = {
        "id": session_id,
        "query": query,
        "model_name": model_name,
        "max_rounds": max_rounds,
        "current_round": 0,
        "status": "running",
        "logs": [{"time": 0, "level": "info", "message": "Started new standalone deep research engine"}],
        "sources": [],
        "evolving_report": "",
        "research_plan": "Using new standalone engine"
    }
    
    # Configure the standalone engine based on UI config
    dr_config.MAX_ITERATIONS = max_rounds
    if "gemini" not in model_name.lower() and "/" not in model_name:
        dr_config.LLM_PROVIDER = LLMProvider.OLLAMA
        dr_config.OLLAMA_MODEL = model_name.replace("ollama/", "")
    else:
        dr_config.LLM_PROVIDER = LLMProvider.CLOUD
        dr_config.CLOUD_API_KEY = config_opts.get("gemini_api_key") or config_opts.get("openrouter_api_key")
        
    def update_progress(state: ResearchState):
        _sessions_registry[session_id]["current_round"] = state.iteration
        
        # Build evolving report
        report = f"## Research in Progress (Iteration {state.iteration})\n\n"
        if state.queries:
            report += "### Queries:\n" + "\n".join(f"- {q}" for q in state.queries) + "\n\n"
        if state.findings:
            report += "### Latest Findings:\n" + state.findings[-1].get("facts", "") + "\n\n"
            
        _sessions_registry[session_id]["evolving_report"] = report
        _sessions_registry[session_id]["logs"].append({"time": 0, "level": "info", "message": f"Completed iteration {state.iteration}"})

    try:
        # Run research synchronously in this background task
        state = run_research(query, progress_callback=update_progress)
        
        _sessions_registry[session_id]["status"] = "completed" if state.is_complete else "failed"
        _sessions_registry[session_id]["current_round"] = state.iteration
        _sessions_registry[session_id]["evolving_report"] = state.synthesis
        
        sources = []
        for f in state.findings:
            sources.append({"url": f.get("query"), "title": f.get("query")})
        _sessions_registry[session_id]["sources"] = sources
        
        _sessions_registry[session_id]["logs"].append({"time": 0, "level": "info", "message": "Research loop finished."})
        
    except Exception as e:
        logger.error(f"Error in standalone deep research: {e}")
        _sessions_registry[session_id]["status"] = "failed"
        _sessions_registry[session_id]["error"] = str(e)
    
    db = load_research_sessions()
    if "sessions" not in db:
        db["sessions"] = {}
    db["sessions"][session_id] = _sessions_registry[session_id]
    save_research_sessions(db)
