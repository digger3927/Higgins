import requests
import json
import sqlite3
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from deep_research_engine.config import config, RunMode, LLMProvider

class SearchEngine:
    def search(self, query: str) -> List[Dict[str, str]]:
        if config.RUN_MODE == RunMode.ONLINE:
            return self._online_search(query)
        else:
            return self._offline_search(query)
    
    def _online_search(self, query: str) -> List[Dict[str, str]]:
        """Uses DuckDuckGo to perform the web search."""
        print(f"[SearchEngine] Online search for: {query}")
        results = []
        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                # Pull the top 10 results to increase detail and coverage
                for r in ddgs.text(query, max_results=10):
                    results.append({"title": r.get("title", ""), "url": r.get("href", ""), "snippet": r.get("body", "")})
        except Exception as e:
            print(f"[SearchEngine] DDGS error: {e}")
        return results

    def _offline_search(self, query: str) -> List[Dict[str, str]]:
        """Queries local database tables using SQLite full-text search."""
        print(f"[SearchEngine] Offline search for: {query}")
        results = []
        try:
            # Assume we have a local.db with a table 'documents' having full-text search setup
            conn = sqlite3.connect('local.db')
            cursor = conn.cursor()
            # This is a placeholder query, assumes FTS5 table named documents_fts
            cursor.execute("SELECT title, content FROM documents WHERE content LIKE ? LIMIT 5", (f"%{query}%",))
            rows = cursor.fetchall()
            for row in rows:
                results.append({"title": row[0], "snippet": row[1][:200], "url": "local://db"})
            conn.close()
        except sqlite3.OperationalError as e:
            print(f"[SearchEngine] Offline DB error: {e}")
            results.append({"title": "Local DB missing", "snippet": "Could not access local.db", "url": ""})
        return results

    def fetch_page(self, url: str) -> str:
        if config.RUN_MODE == RunMode.ONLINE and url.startswith("http"):
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                # Set text limit to 40000 characters for deep extraction
                return soup.get_text(separator=' ', strip=True)[:40000]
            except requests.RequestException as e:
                print(f"[SearchEngine] Network error fetching {url}: {e}")
                return ""
        return "Offline or invalid URL."


class InferenceEngine:
    def generate(self, prompt: str) -> str:
        if config.LLM_PROVIDER == LLMProvider.OLLAMA:
            return self._ollama_generate(prompt)
        else:
            return self._cloud_generate(prompt)
            
    def _ollama_generate(self, prompt: str) -> str:
        """Call local Ollama instance."""
        print("[InferenceEngine] Generating via local Ollama...")
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": config.OLLAMA_MODEL, "prompt": prompt, "stream": False},
                timeout=60
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except requests.RequestException as e:
            print(f"[InferenceEngine] Local Ollama error: {e}")
            return "Error calling local LLM."

    def _cloud_generate(self, prompt: str) -> str:
        """Call cloud LLM (e.g. OpenAI)."""
        print("[InferenceEngine] Generating via Cloud API...")
        if not config.CLOUD_API_KEY:
            return "Error: CLOUD_API_KEY not set."
        headers = {
            "Authorization": f"Bearer {config.CLOUD_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "gpt-3.5-turbo", # Placeholder
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7
        }
        try:
            response = requests.post(config.CLOUD_API_URL, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.RequestException as e:
            print(f"[InferenceEngine] Cloud API error: {e}")
            return "Error calling cloud LLM."

search_engine = SearchEngine()
inference_engine = InferenceEngine()
