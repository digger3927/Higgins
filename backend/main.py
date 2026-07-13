import os
import json
import logging
import asyncio
import time
import re
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx
import google.generativeai as genai
from dotenv import load_dotenv

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("higgins-backend")

# Load environment variables
load_dotenv()

app = FastAPI(title="Higgins Backend")

# Enable CORS for the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For local development, allow all
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.json")
CHATS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "chats.json")
BRAIN_INDEX_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "brain.json")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

class Settings(BaseModel):
    gemini_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None
    preferred_model: Optional[str] = None
    enabled_openrouter_models: Optional[List[str]] = None
    # Search Engine Keys
    search_provider: Optional[str] = None
    tavily_api_key: Optional[str] = None
    brave_api_key: Optional[str] = None
    google_api_key: Optional[str] = None
    google_cx: Optional[str] = None
    serper_api_key: Optional[str] = None
    # Local Brain Directory
    brain_directory: Optional[str] = None

class Message(BaseModel):
    role: str
    content: str

class ChatPayload(BaseModel):
    chat_id: str
    messages: List[Message]
    model: str
    web_search_enabled: Optional[bool] = False
    local_brain_enabled: Optional[bool] = False

class ChatUpdatePayload(BaseModel):
    title: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None

class CreateChatPayload(BaseModel):
    model: str

# Config helper
def load_settings() -> Dict[str, Any]:
    default_config = {
        "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
        "openrouter_api_key": os.getenv("OPENROUTER_API_KEY", ""),
        "preferred_model": os.getenv("PREFERRED_MODEL", "google/gemini-2.5-flash"),
        "enabled_openrouter_models": [],
        "search_provider": "duckduckgo",
        "tavily_api_key": os.getenv("TAVILY_API_KEY", ""),
        "brave_api_key": os.getenv("BRAVE_API_KEY", ""),
        "google_api_key": os.getenv("GOOGLE_API_KEY", ""),
        "google_cx": os.getenv("GOOGLE_CX", ""),
        "serper_api_key": os.getenv("SERPER_API_KEY", ""),
        "brain_directory": ""
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                data = json.load(f)
                # Ensure all default keys exist
                for k, v in default_config.items():
                    if k not in data:
                        data[k] = v
                return data
        except Exception as e:
            logger.error(f"Error loading config: {e}")
    return default_config

def save_settings(settings: Dict[str, Any]):
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving config: {e}")
        raise HTTPException(status_code=500, detail="Failed to save settings file")

# Chats persistence helper
def load_chats_db() -> Dict[str, Any]:
    if os.path.exists(CHATS_FILE):
        try:
            with open(CHATS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading chats file: {e}")
    return {"chats": {}}

def save_chats_db(db: Dict[str, Any]):
    try:
        with open(CHATS_FILE, "w") as f:
            json.dump(db, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving chats file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save chats database")

@app.get("/api/settings")
async def get_settings():
    return load_settings()

@app.post("/api/settings")
async def update_settings(settings: Settings):
    current = load_settings()
    if settings.gemini_api_key is not None:
        current["gemini_api_key"] = settings.gemini_api_key
    if settings.openrouter_api_key is not None:
        current["openrouter_api_key"] = settings.openrouter_api_key
    if settings.preferred_model is not None:
        current["preferred_model"] = settings.preferred_model
    if settings.enabled_openrouter_models is not None:
        current["enabled_openrouter_models"] = settings.enabled_openrouter_models
    
    # Search settings
    if settings.search_provider is not None:
        current["search_provider"] = settings.search_provider
    if settings.tavily_api_key is not None:
        current["tavily_api_key"] = settings.tavily_api_key
    if settings.brave_api_key is not None:
        current["brave_api_key"] = settings.brave_api_key
    if settings.google_api_key is not None:
        current["google_api_key"] = settings.google_api_key
    if settings.google_cx is not None:
        current["google_cx"] = settings.google_cx
    if settings.serper_api_key is not None:
        current["serper_api_key"] = settings.serper_api_key
        
    # Brain Settings
    if settings.brain_directory is not None:
        current["brain_directory"] = settings.brain_directory
    
    save_settings(current)
    return current

# Chats management routes
@app.get("/api/chats")
async def get_chats():
    db = load_chats_db()
    chats_list = list(db["chats"].values())
    
    def sort_key(chat):
        pinned = 1 if chat.get("is_pinned", False) else 0
        created = chat.get("created_at", 0)
        return (pinned, created)
        
    chats_list.sort(key=sort_key, reverse=True)
    return chats_list

@app.post("/api/chats")
async def create_chat(payload: CreateChatPayload):
    db = load_chats_db()
    chat_id = str(int(time.time() * 1000))
    new_chat = {
        "id": chat_id,
        "title": "New Chat",
        "messages": [],
        "model": payload.model,
        "is_pinned": False,
        "is_archived": False,
        "created_at": time.time()
    }
    db["chats"][chat_id] = new_chat
    save_chats_db(db)
    return new_chat

@app.put("/api/chats/{chat_id}")
async def update_chat(chat_id: str, payload: ChatUpdatePayload):
    db = load_chats_db()
    if chat_id not in db["chats"]:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    chat = db["chats"][chat_id]
    if payload.title is not None:
        chat["title"] = payload.title
    if payload.is_pinned is not None:
        chat["is_pinned"] = payload.is_pinned
    if payload.is_archived is not None:
        chat["is_archived"] = payload.is_archived
        
    save_chats_db(db)
    return chat

@app.delete("/api/chats/{chat_id}")
async def delete_chat(chat_id: str):
    db = load_chats_db()
    if chat_id not in db["chats"]:
        raise HTTPException(status_code=404, detail="Chat session not found")
    
    del db["chats"][chat_id]
    save_chats_db(db)
    return {"status": "success", "message": "Chat deleted"}

# Fetch dynamic models list from OpenRouter API
@app.get("/api/openrouter-catalog")
async def get_openrouter_catalog():
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get("https://openrouter.ai/api/v1/models", timeout=8.0)
            if res.status_code == 200:
                data = res.json()
                catalog = []
                for item in data.get("data", []):
                    pricing = item.get("pricing", {})
                    context_len = item.get("context_length", 0)
                    
                    catalog.append({
                        "id": item.get("id"),
                        "name": item.get("name"),
                        "description": item.get("description", ""),
                        "context_length": context_len,
                        "prompt_price": pricing.get("prompt", "0"),
                        "completion_price": pricing.get("completion", "0")
                    })
                catalog.sort(key=lambda x: x["name"])
                return catalog
    except Exception as e:
        logger.error(f"Failed to fetch OpenRouter models catalog: {e}")
        return [
            {"id": "meta-llama/llama-3-8b-instruct:free", "name": "Llama 3 8B (Free)", "context_length": 8192},
            {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "context_length": 200000},
            {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "context_length": 128000},
            {"id": "deepseek/deepseek-chat", "name": "DeepSeek V3", "context_length": 64000}
        ]

# Dynamic Models fetching
@app.get("/api/models")
async def get_models():
    config = load_settings()
    
    gemini_models = [
        {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "google"},
        {"id": "google/gemini-1.5-pro", "name": "Gemini 1.5 Pro", "provider": "google"},
        {"id": "google/gemini-1.5-flash", "name": "Gemini 1.5 Flash", "provider": "google"},
    ]
    
    enabled_or_ids = config.get("enabled_openrouter_models", [])
    openrouter_models = []
    
    if not enabled_or_ids:
        default_or_models = [
            {"id": "meta-llama/llama-3-8b-instruct:free", "name": "Llama 3 8B (Free)", "provider": "openrouter"},
            {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet", "provider": "openrouter"},
            {"id": "openai/gpt-4o-mini", "name": "GPT-4o Mini", "provider": "openrouter"},
            {"id": "deepseek/deepseek-chat", "name": "DeepSeek V3", "provider": "openrouter"},
        ]
        openrouter_models = default_or_models
    else:
        for model_id in enabled_or_ids:
            display_name = model_id
            if "/" in display_name:
                display_name = display_name.split("/")[-1].replace("-", " ").replace(":", " ").title()
            openrouter_models.append({
                "id": model_id,
                "name": display_name,
                "provider": "openrouter"
            })
            
    ollama_models = []
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{OLLAMA_HOST}/api/tags", timeout=2.0)
            if res.status_code == 200:
                tags_data = res.json()
                for model in tags_data.get("models", []):
                    model_name = model.get("name")
                    display_name = model_name
                    if ":" in display_name:
                        name_part, tag_part = display_name.split(":", 1)
                        if tag_part == "latest":
                            display_name = name_part
                    
                    ollama_models.append({
                        "id": model_name,
                        "name": f"{display_name} (Local)",
                        "provider": "ollama"
                    })
    except Exception as e:
        logger.warning(f"Failed to fetch local Ollama models (is Ollama running?): {e}")
        
    return gemini_models + openrouter_models + ollama_models

# Search Engine Crawlers & APIs
async def search_duckduckgo(query: str) -> List[Dict[str, str]]:
    results = []
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            # We run in a threadpool to prevent blocking the async event loop
            loop = asyncio.get_event_loop()
            ddg_res = await loop.run_in_executor(
                None, lambda: list(ddgs.text(query, max_results=5))
            )
            for item in ddg_res:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("href", ""),
                    "snippet": item.get("body", "")
                })
    except Exception as e:
        logger.error(f"DuckDuckGo search error: {e}")
    return results

async def search_tavily(query: str, api_key: str) -> List[Dict[str, str]]:
    results = []
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": api_key, "query": query, "max_results": 5},
                timeout=8.0
            )
            if res.status_code == 200:
                data = res.json()
                for item in data.get("results", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("content", "")
                    })
    except Exception as e:
        logger.error(f"Tavily Search API error: {e}")
    return results

async def search_brave(query: str, api_key: str) -> List[Dict[str, str]]:
    results = []
    try:
        async with httpx.AsyncClient() as client:
            headers = {"Accept": "application/json", "X-Subscription-Token": api_key}
            res = await client.get(
                f"https://api.search.brave.com/res/v1/web/search?q={query}",
                headers=headers,
                timeout=8.0
            )
            if res.status_code == 200:
                data = res.json()
                for item in data.get("web", {}).get("results", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("description", "")
                    })
    except Exception as e:
        logger.error(f"Brave Search API error: {e}")
    return results

async def search_google(query: str, api_key: str, cx: str) -> List[Dict[str, str]]:
    results = []
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(
                "https://www.googleapis.com/customsearch/v1",
                params={"q": query, "key": api_key, "cx": cx, "num": 5},
                timeout=8.0
            )
            if res.status_code == 200:
                data = res.json()
                for item in data.get("items", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", "")
                    })
    except Exception as e:
        logger.error(f"Google Custom Search API error: {e}")
    return results

async def search_serper(query: str, api_key: str) -> List[Dict[str, str]]:
    results = []
    try:
        async with httpx.AsyncClient() as client:
            headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
            res = await client.post(
                "https://google.serper.dev/search",
                headers=headers,
                json={"q": query, "num": 5},
                timeout=8.0
            )
            if res.status_code == 200:
                data = res.json()
                for item in data.get("organic", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", "")
                    })
    except Exception as e:
        logger.error(f"Serper API error: {e}")
    return results

async def perform_web_search(query: str, config: Dict[str, Any]) -> Tuple[str, List[Dict[str, str]]]:
    provider = config.get("search_provider", "duckduckgo")
    logger.info(f"Triggering web search query: '{query}' via provider: {provider}")
    
    results = []
    if provider == "duckduckgo":
        results = await search_duckduckgo(query)
    elif provider == "tavily":
        key = config.get("tavily_api_key")
        if key:
            results = await search_tavily(query, key)
    elif provider == "brave":
        key = config.get("brave_api_key")
        if key:
            results = await search_brave(query, key)
    elif provider == "google":
        key = config.get("google_api_key")
        cx = config.get("google_cx")
        if key and cx:
            results = await search_google(query, key, cx)
    elif provider == "serper":
        key = config.get("serper_api_key")
        if key:
            results = await search_serper(query, key)
            
    if not results:
        logger.warning(f"No search results fetched for query '{query}' from provider {provider}")
        return "No search results found or provider connection failed.", []
        
    formatted = []
    for idx, r in enumerate(results, 1):
        formatted.append(f"[{idx}] Title: {r.get('title')}\nSource: {r.get('url')}\nSnippet: {r.get('snippet')}\n")
    return "\n".join(formatted), results

# LLM streaming helper generators
async def stream_gemini(api_key: str, model_name: str, messages: List[Dict[str, str]], chat_id: str, sources: Optional[List[Dict[str, Any]]] = None):
    accumulated_content = ""
    try:
        genai.configure(api_key=api_key)
        contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })

        clean_model = model_name
        if clean_model.startswith("google/"):
            clean_model = clean_model.replace("google/", "")
            
        model = genai.GenerativeModel(clean_model)
        response = await model.generate_content_async(contents, stream=True)
        
        async for chunk in response:
            if chunk.text:
                accumulated_content += chunk.text
                yield f"data: {json.dumps({'type': 'chunk', 'content': chunk.text})}\n\n"
        
        save_chat_messages(chat_id, messages, accumulated_content, sources=sources)
        yield "data: [DONE]\n\n"
        
    except Exception as e:
        logger.error(f"Gemini streaming error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

async def stream_openrouter(api_key: str, model_name: str, messages: List[Dict[str, str]], chat_id: str, sources: Optional[List[Dict[str, Any]]] = None):
    accumulated_content = ""
    try:
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "HTTP-Referer": "http://localhost:8000",
                    "Content-Type": "application/json",
                    "X-Title": "Higgins Assistant"
                },
                json={
                    "model": model_name,
                    "messages": messages,
                    "stream": True
                },
                timeout=60.0
            ) as response:
                if response.status_code != 200:
                    err_body = await response.aread()
                    logger.error(f"OpenRouter API returned error {response.status_code}: {err_body}")
                    yield f"data: {json.dumps({'type': 'error', 'content': f'OpenRouter Error {response.status_code}: {err_body.decode()}'})}\n\n"
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    if line.startswith("data: "):
                        data_str = line[6:]
                        if data_str == "[DONE]":
                            save_chat_messages(chat_id, messages, accumulated_content, sources=sources)
                            yield "data: [DONE]\n\n"
                            break
                        try:
                            data_json = json.loads(data_str)
                            choices = data_json.get("choices", [])
                            if choices:
                                delta = choices[0].get("delta", {})
                                chunk_text = delta.get("content", "")
                                if chunk_text:
                                    accumulated_content += chunk_text
                                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk_text})}\n\n"
                        except json.JSONDecodeError:
                            continue
    except Exception as e:
        logger.error(f"OpenRouter streaming error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

async def stream_ollama(model_name: str, messages: List[Dict[str, str]], chat_id: str, sources: Optional[List[Dict[str, Any]]] = None):
    accumulated_content = ""
    try:
        ollama_messages = []
        for msg in messages:
            ollama_messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
            
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{OLLAMA_HOST}/api/chat",
                json={
                    "model": model_name,
                    "messages": ollama_messages,
                    "stream": True
                },
                timeout=120.0
            ) as response:
                if response.status_code != 200:
                    err_body = await response.aread()
                    logger.error(f"Ollama returned error {response.status_code}: {err_body}")
                    yield f"data: {json.dumps({'type': 'error', 'content': f'Ollama Error {response.status_code}: {err_body.decode()}'})}\n\n"
                    return

                async for line in response.aiter_lines():
                    if not line:
                        continue
                    try:
                        data_json = json.loads(line)
                        chunk_text = data_json.get("message", {}).get("content", "")
                        if chunk_text:
                            accumulated_content += chunk_text
                            yield f"data: {json.dumps({'type': 'chunk', 'content': chunk_text})}\n\n"
                        
                        if data_json.get("done", False):
                            save_chat_messages(chat_id, messages, accumulated_content, sources=sources)
                            yield "data: [DONE]\n\n"
                            break
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        logger.error(f"Ollama streaming error: {e}")
        yield f"data: {json.dumps({'type': 'error', 'content': f'Failed to connect to local Ollama. Details: {str(e)}'})}\n\n"

def save_chat_messages(chat_id: str, client_messages: List[Dict[str, str]], assistant_content: str, sources: Optional[List[Dict[str, Any]]] = None):
    try:
        db = load_chats_db()
        if chat_id in db["chats"]:
            chat = db["chats"][chat_id]
            updated_messages = list(client_messages)
            assistant_msg = {"role": "assistant", "content": assistant_content}
            if sources:
                assistant_msg["sources"] = sources
            updated_messages.append(assistant_msg)
            chat["messages"] = updated_messages
            
            if chat.get("title") == "New Chat" and len(client_messages) > 0:
                first_prompt = client_messages[0]["content"]
                clean_title = first_prompt.strip().replace("\n", " ")
                if len(clean_title) > 30:
                    chat["title"] = clean_title[:30] + "..."
                else:
                    chat["title"] = clean_title
            
            save_chats_db(db)
            logger.info(f"Successfully saved message history for chat {chat_id}")
    except Exception as e:
        logger.error(f"Failed to auto-save chat message history: {e}")

async def generate_search_query(user_prompt: str, model_name: str, config: Dict[str, Any]) -> str:
    # 1. Simple heuristic: If it is short (<= 6 words), just use it directly
    words = user_prompt.strip().split()
    if len(words) <= 6:
        return user_prompt.strip()

    # 2. Extract keywords using LLM if keys are available
    try:
        current_date_str = time.strftime("%B %d, %Y")
        system_instruction = f"""You are an advanced search query optimizer. 
Convert the user's conversational prompt into a concise, highly precise search engine query (max 6 keywords). 

CRITICAL Context:
- The current date is {current_date_str}.
- If the user asks about an event in this year (e.g., World Cup 2026, which runs June/July 2026), formulate terms matching the active stage (e.g. "live scores", "schedule", "bracket", "matches") rather than historical qualifiers (which are long over).
- Stick strictly to the user's query intent. Do not add words like "qualification" or "qualifiers" unless the user explicitly requested it.

Output ONLY the optimized search keywords. No quotes, no prefix, no explanations."""
        
        if "gemini" in model_name.lower():
            api_key = config.get("gemini_api_key")
            if api_key:
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel("gemini-2.5-flash")
                response = await model.generate_content_async(
                    contents=f"{system_instruction}\n\nUser Prompt: {user_prompt}"
                )
                if response.text:
                    query = response.text.strip().strip('"').strip("'")
                    logger.info(f"LLM optimized search query: '{query}'")
                    return query
        elif "openrouter" in model_name.lower() or "/" in model_name:
            api_key = config.get("openrouter_api_key")
            if api_key:
                async with httpx.AsyncClient() as client:
                    res = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": "google/gemini-2.5-flash" if "gemini" not in model_name else model_name,
                            "messages": [
                                {"role": "system", "content": system_instruction},
                                {"role": "user", "content": user_prompt}
                            ],
                            "temperature": 0.0
                        },
                        timeout=5.0
                    )
                    if res.status_code == 200:
                        data = res.json()
                        query = data["choices"][0]["message"]["content"].strip().strip('"').strip("'")
                        logger.info(f"LLM optimized search query: '{query}'")
                        return query
    except Exception as e:
        logger.error(f"Failed to optimize search query with LLM: {e}")

    # Fallback heuristic: clean prefixes and slice words
    prefixes_to_remove = [
        "give me an update on", "tell me about", "what is", "who is", "search for",
        "do you know", "can you find", "show me", "please search", "look up", "update on"
    ]
    temp_query = user_prompt.lower().strip()
    for prefix in prefixes_to_remove:
        if temp_query.startswith(prefix):
            temp_query = temp_query[len(prefix):].strip()
    
    fallback_words = re.sub(r'[?.!,;:]', '', temp_query).split()[:8]
    fallback_query = " ".join(fallback_words)
    logger.info(f"Heuristic fallback search query: '{fallback_query}'")
    return fallback_query

# Local Brain Text Extraction & Search Ranking Helpers
def extract_text_from_pdf(file_path: str) -> str:
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content + "\n"
        return text
    except Exception as e:
        logger.error(f"Error reading PDF {file_path}: {e}")
        return ""

def extract_text_from_file(file_path: str) -> str:
    if file_path.lower().endswith(".pdf"):
        return extract_text_from_pdf(file_path)
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error reading file {file_path}: {e}")
        return ""

def chunk_text(text: str, file_path: str, relative_path: str) -> List[Dict[str, Any]]:
    chunks = []
    chunk_size = 800
    overlap = 150
    cleaned_text = re.sub(r'\n{3,}', '\n\n', text)
    
    start = 0
    while start < len(cleaned_text):
        end = start + chunk_size
        chunk_content = cleaned_text[start:end]
        chunks.append({
            "text": chunk_content,
            "source": relative_path,
            "full_path": file_path
        })
        # Standard step size based on overlap
        start += (chunk_size - overlap)
    return chunks

def search_brain_index(query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    query_words = [w.lower() for w in re.sub(r'[^\w\s]', '', query).split() if len(w) > 2]
    if not query_words:
        query_words = [w.lower() for w in query.split()]
        
    scores = []
    for chunk in chunks:
        chunk_text_lower = chunk["text"].lower()
        score = 0.0
        
        for word in query_words:
            count = chunk_text_lower.count(word)
            if count > 0:
                # Term frequency scoring normalized by chunk length
                score += (1.0 + count) / (1.0 + len(chunk_text_lower.split()) / 100.0)
                
        if score > 0:
            scores.append((score, chunk))
            
    scores.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scores[:5]]

# Directory navigation API for local folder picker UI
@app.get("/api/browse")
async def browse_directory(path: Optional[str] = None):
    if not path or path.strip() == "":
        path = os.path.expanduser("~")
        
    if not os.path.exists(path):
        path = os.path.expanduser("~")
        
    if not os.path.isdir(path):
        path = os.path.dirname(path)
        if not path or not os.path.isdir(path):
            path = os.path.expanduser("~")
            
    abs_path = os.path.abspath(path)
    
    try:
        subdirs = []
        for item in os.listdir(abs_path):
            if item.startswith("."):
                continue
            item_path = os.path.join(abs_path, item)
            try:
                if os.path.isdir(item_path):
                    subdirs.append(item)
            except (PermissionError, FileNotFoundError):
                continue
                
        subdirs.sort(key=str.lower)
        
        parent_path = os.path.dirname(abs_path)
        if parent_path == abs_path:
            parent_path = ""
            
        return {
            "current_path": abs_path,
            "parent_path": parent_path,
            "subdirectories": subdirs
        }
    except PermissionError:
        raise HTTPException(status_code=403, detail="Permission denied to access this directory.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Local Brain API Routes
@app.get("/api/brain/status")
async def get_brain_status():
    config = load_settings()
    directory = config.get("brain_directory", "")
    is_indexed = os.path.exists(BRAIN_INDEX_FILE)
    file_count = 0
    chunk_count = 0
    last_indexed = 0.0
    
    if is_indexed:
        try:
            with open(BRAIN_INDEX_FILE, "r") as f:
                data = json.load(f)
                chunk_count = len(data.get("chunks", []))
                file_count = len(set(c["source"] for c in data.get("chunks", [])))
                last_indexed = data.get("last_indexed", 0.0)
        except Exception as e:
            logger.error(f"Error loading brain status: {e}")
            
    return {
        "brain_directory": directory,
        "is_indexed": is_indexed,
        "file_count": file_count,
        "chunk_count": chunk_count,
        "last_indexed": last_indexed
    }

@app.post("/api/brain/index")
async def index_brain():
    config = load_settings()
    directory = config.get("brain_directory", "")
    if not directory or not os.path.exists(directory):
        raise HTTPException(status_code=400, detail="Invalid brain directory path. Configure it in settings first.")
        
    logger.info(f"Indexing brain directory: {directory}")
    supported_extensions = (
        ".txt", ".md", ".py", ".js", ".ts", ".tsx", 
        ".json", ".csv", ".html", ".css", ".pdf"
    )
    
    all_chunks = []
    file_count = 0
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(supported_extensions):
                full_path = os.path.join(root, file)
                relative_path = os.path.relpath(full_path, directory)
                text = extract_text_from_file(full_path)
                if text.strip():
                    chunks = chunk_text(text, full_path, relative_path)
                    all_chunks.extend(chunks)
                    file_count += 1
                    
    brain_db = {
        "chunks": all_chunks,
        "last_indexed": time.time()
    }
    
    try:
        with open(BRAIN_INDEX_FILE, "w") as f:
            json.dump(brain_db, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to write brain.json: {e}")
        raise HTTPException(status_code=500, detail="Failed to write brain index database.")
        
    return {
        "status": "success",
        "file_count": file_count,
        "chunk_count": len(all_chunks)
    }

@app.post("/api/chat")
async def chat(payload: ChatPayload):
    config = load_settings()
    db = load_chats_db()
    
    if payload.chat_id not in db["chats"]:
        raise HTTPException(status_code=404, detail="Chat session not found")
        
    messages_dict = [{"role": m.role, "content": m.content} for m in payload.messages]
    
    # RAG search intercept
    brain_context = ""
    brain_results = []
    if payload.local_brain_enabled and len(messages_dict) > 0:
        last_user_message = messages_dict[-1]
        if last_user_message["role"] == "user":
            if os.path.exists(BRAIN_INDEX_FILE):
                try:
                    with open(BRAIN_INDEX_FILE, "r") as f:
                        brain_data = json.load(f)
                        chunks = brain_data.get("chunks", [])
                        matched_chunks = search_brain_index(last_user_message["content"], chunks)
                        if matched_chunks:
                            formatted_chunks = []
                            for idx, c in enumerate(matched_chunks, 1):
                                formatted_chunks.append(f"[{idx}] Source File: {c['source']}\nContent:\n{c['text']}\n")
                                brain_results.append({
                                    "title": c['source'],
                                    "url": f"file://{c['full_path']}",
                                    "snippet": c['text']
                                })
                            brain_context = "\n".join(formatted_chunks)
                        else:
                            brain_context = "No relevant local documents found."
                except Exception as e:
                    logger.error(f"Failed to read brain index: {e}")
                    brain_context = f"Error reading local brain index: {str(e)}"
            else:
                brain_context = "Local Brain has not been indexed yet. Please configure and run indexing in Settings."
                
            logger.info("Local Brain context retrieved successfully.")

    # Intercept and run Web Search if requested on the last user prompt
    sources_metadata = []
    sources_metadata.extend(brain_results)
    
    if len(messages_dict) > 0:
        last_user_message = messages_dict[-1]
        if last_user_message["role"] == "user":
            if payload.web_search_enabled and payload.local_brain_enabled:
                # Hybrid RAG + Search
                search_query = await generate_search_query(last_user_message["content"], payload.model, config)
                search_context, web_results = await perform_web_search(search_query, config)
                sources_metadata.extend(web_results)
                combined_prompt = f"""[Web Search Results Context]
{search_context}

[Local Brain Context]
{brain_context}

User Query: {last_user_message["content"]}
Please construct your answer using both the Web Search Context and the Local Brain Context chunks above. DO NOT include a list of source links or reference indices (like [1], [2], etc.) in your final response. The user interface displays sources separately. Write your reply cleanly."""
                messages_dict[-1]["content"] = combined_prompt
                logger.info("Hybrid Search & RAG context successfully injected into LLM payload.")
            elif payload.web_search_enabled:
                search_query = await generate_search_query(last_user_message["content"], payload.model, config)
                search_context, web_results = await perform_web_search(search_query, config)
                sources_metadata.extend(web_results)
                context_prompt = f"""[Web Search Results Context]
{search_context}

User Query: {last_user_message["content"]}
Please construct your answer using the search context above. DO NOT include a list of source links, URLs, or reference indices (like [1], [2]) at the end of your response. The interface displays sources separately. Write your reply cleanly."""
                messages_dict[-1]["content"] = context_prompt
                logger.info("Search context successfully injected into LLM payload.")
            elif payload.local_brain_enabled:
                context_prompt = f"""[Local Brain Context]
{brain_context}

User Query: {last_user_message["content"]}
Please construct your answer using the Local Brain Context chunks above. DO NOT include raw source lists or reference indices (like [1], [2]) in your final response. The interface displays sources separately. Write your reply cleanly."""
                messages_dict[-1]["content"] = context_prompt
                logger.info("Local Brain context successfully injected into LLM payload.")

    # Save the updated user message (and context) to the history
    db["chats"][payload.chat_id]["messages"] = messages_dict
    save_chats_db(db)
    
    model_name = payload.model
    is_gemini_model = "gemini" in model_name.lower()
    
    local_models = []
    try:
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{OLLAMA_HOST}/api/tags")
            if res.status_code == 200:
                local_models = [m["name"] for m in res.json().get("models", [])]
    except Exception:
        pass
        
    is_local = model_name in local_models
    
    if is_gemini_model:
        api_key = config.get("gemini_api_key")
        if not api_key:
            raise HTTPException(status_code=400, detail="Gemini API Key not set. Update settings first.")
        return StreamingResponse(
            stream_gemini(api_key, model_name, messages_dict, payload.chat_id, sources=sources_metadata),
            media_type="text/event-stream"
        )
    elif not is_local:
        api_key = config.get("openrouter_api_key")
        if not api_key:
            raise HTTPException(status_code=400, detail="OpenRouter API Key not set. Update settings first.")
        return StreamingResponse(
            stream_openrouter(api_key, model_name, messages_dict, payload.chat_id, sources=sources_metadata),
            media_type="text/event-stream"
        )
    else:
        return StreamingResponse(
            stream_ollama(model_name, messages_dict, payload.chat_id, sources=sources_metadata),
            media_type="text/event-stream"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
