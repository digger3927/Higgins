import os
import json
import logging
import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple, Set
import httpx
from bs4 import BeautifulSoup
import google.generativeai as genai

logger = logging.getLogger("higgins-deep-research")

# Path to store historical research sessions
RESEARCH_SESSIONS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "research_sessions.json")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")

# Global in-memory registry of active/recent research sessions
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

# Load sessions on startup
try:
    _sessions_registry = load_research_sessions().get("sessions", {})
except Exception as e:
    logger.error(f"Failed to load sessions on module load: {e}")


class DeepResearcher:
    def __init__(self, session_id: str, query: str, model_name: str, max_rounds: int, config: Dict[str, Any]):
        self.session_id = session_id
        self.query = query
        self.model_name = model_name
        self.max_rounds = max_rounds
        self.config = config
        self.current_round = 0
        self.logs: List[Dict[str, Any]] = []
        self.sources: List[Dict[str, str]] = []
        self.visited_urls: Set[str] = set()
        self.evolving_report = ""
        self.research_plan = ""
        self.status = "running"
        self.error = None

    def log(self, message: str, log_type: str = "info", data: Any = None):
        logger.info(f"[{self.session_id}] {message}")
        event = {
            "timestamp": time.time(),
            "type": log_type,
            "message": message,
            "data": data
        }
        self.logs.append(event)
        self._update_registry()

    def _update_registry(self):
        # Update the active session in-memory and write to disk
        session_data = {
            "id": self.session_id,
            "query": self.query,
            "model_name": self.model_name,
            "max_rounds": self.max_rounds,
            "current_round": self.current_round,
            "status": self.status,
            "logs": self.logs,
            "sources": self.sources,
            "evolving_report": self.evolving_report,
            "research_plan": self.research_plan,
            "error": self.error,
            "started_at": _sessions_registry.get(self.session_id, {}).get("started_at", time.time()),
            "completed_at": time.time() if self.status in ["done", "failed", "cancelled"] else None
        }
        _sessions_registry[self.session_id] = session_data
        
        # Save entire db
        db = load_research_sessions()
        db["sessions"] = _sessions_registry
        save_research_sessions(db)

    async def call_llm(self, prompt: str, system_instruction: str = "") -> str:
        """Helper to hit Gemini, OpenRouter, or Ollama depending on configuration."""
        try:
            if "gemini" in self.model_name.lower():
                api_key = self.config.get("gemini_api_key")
                if not api_key:
                    raise ValueError("Gemini API key is missing in Settings")
                genai.configure(api_key=api_key)
                # Parse actual model name
                clean_model = self.model_name
                if clean_model.startswith("google/"):
                    clean_model = clean_model.replace("google/", "")
                
                model = genai.GenerativeModel(
                    model_name=clean_model,
                    system_instruction=system_instruction if system_instruction else None
                )
                response = await model.generate_content_async(prompt)
                return response.text or ""
            
            elif "openrouter" in self.model_name.lower() or "/" in self.model_name:
                api_key = self.config.get("openrouter_api_key")
                if not api_key:
                    raise ValueError("OpenRouter API key is missing in Settings")
                
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})

                async with httpx.AsyncClient() as client:
                    res = await client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {api_key}",
                            "Content-Type": "application/json"
                        },
                        json={
                            "model": self.model_name,
                            "messages": messages,
                            "temperature": 0.2
                        },
                        timeout=30.0
                    )
                    if res.status_code == 200:
                        data = res.json()
                        return data["choices"][0]["message"]["content"]
                    else:
                        raise ValueError(f"OpenRouter API error: {res.status_code} - {res.text}")
            
            else:
                # Local Ollama model fallback
                messages = []
                if system_instruction:
                    messages.append({"role": "system", "content": system_instruction})
                messages.append({"role": "user", "content": prompt})

                async with httpx.AsyncClient() as client:
                    res = await client.post(
                        f"{OLLAMA_HOST}/api/chat",
                        json={
                            "model": self.model_name,
                            "messages": messages,
                            "stream": False
                        },
                        timeout=60.0
                    )
                    if res.status_code == 200:
                        data = res.json()
                        return data.get("message", {}).get("content", "")
                    else:
                        raise ValueError(f"Ollama returned error: {res.status_code} - {res.text}")

        except Exception as e:
            logger.error(f"LLM call failed in Deep Research: {e}")
            raise e

    async def crawl_and_parse_url(self, url: str) -> Optional[str]:
        """Fetch the HTML of a webpage and scrape its text content."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"
        }
        try:
            async with httpx.AsyncClient(follow_redirects=True, headers=headers) as client:
                res = await client.get(url, timeout=10.0)
                if res.status_code != 200:
                    return None
                
                # Check content type is HTML
                content_type = res.headers.get("content-type", "").lower()
                if "text/html" not in content_type:
                    return None
                
                soup = BeautifulSoup(res.text, "html.parser")
                
                # Strip style/script elements
                for element in soup(["script", "style", "noscript", "header", "footer", "nav", "iframe", "aside"]):
                    element.decompose()
                
                # Get text
                text = soup.get_text(separator="\n")
                
                # Clean up white space
                lines = (line.strip() for line in text.splitlines())
                chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                clean_text = "\n".join(chunk for chunk in chunks if chunk)
                
                # Return limited preview length
                return clean_text[:12000]
        except Exception as e:
            logger.warning(f"Crawling failed for {url}: {e}")
            return None

    async def perform_search(self, query: str) -> List[Dict[str, str]]:
        """Run search queries via the configured provider."""
        from main import perform_web_search
        try:
            _, results = await perform_web_search(query, self.config)
            return results
        except Exception as e:
            self.log(f"Search API error for '{query}': {e}", "error")
            return []

    async def check_cancelled(self) -> bool:
        # Check database directly for cancellation status change
        session_entry = _sessions_registry.get(self.session_id)
        if session_entry and session_entry.get("status") == "cancelled":
            return True
        return False

    async def run(self):
        try:
            self.log(f"Starting Deep Research for query: '{self.query}'", "info")
            
            # Step 1: Create a research plan
            if await self.check_cancelled():
                self.status = "cancelled"
                self.log("Research cancelled by user.", "info")
                return

            self.log("Analyzing topic and designing research plan...", "info")
            plan_prompt = f"""You are a research strategist. Before searching, analyze this question and create a research plan.

Question: {self.query}

Break this question down:
1. What are the key sub-topics that need to be covered for a comprehensive answer?
2. What specific data points, facts, or perspectives should we look for?
3. What would a complete, high-quality answer include?

Return a JSON object with:
- "sub_questions": Array of 3-5 specific sub-questions to investigate
- "key_topics": Array of key topics/angles to cover
- "success_criteria": One sentence describing what a complete answer looks like

Return ONLY valid JSON.
Example:
{{
  "sub_questions": ["What is the cost of living in X?", "How is the healthcare system?"],
  "key_topics": ["economy", "healthcare", "safety"],
  "success_criteria": "A balanced comparison covering cost and quality of life."
}}"""

            plan_res = await self.call_llm(plan_prompt, "You are a precise research planner. Return ONLY the JSON requested.")
            try:
                # Clean prompt formatting like ```json ... ```
                cleaned_plan_res = plan_res.strip()
                if cleaned_plan_res.startswith("```"):
                    lines = cleaned_plan_res.split("\n")
                    if lines[0].startswith("```json") or lines[0].startswith("```"):
                        cleaned_plan_res = "\n".join(lines[1:-1])
                plan_json = json.loads(cleaned_plan_res.strip())
                self.research_plan = cleaned_plan_res
                self.log(f"Research plan created. Success Criteria: {plan_json.get('success_criteria', 'Comprehensive report')}", "plan", plan_json)
            except Exception as e:
                self.log("Failed to parse plan JSON. Proceeding with raw plan.", "warning")
                self.research_plan = plan_res
                plan_json = {"sub_questions": [self.query], "key_topics": []}

            # Step 2: Begin Iterative Rounds
            self.evolving_report = f"# Research Report: {self.query}\n\n*Draft evolving...*\n"
            
            for round_idx in range(1, self.max_rounds + 1):
                self.current_round = round_idx
                if await self.check_cancelled():
                    self.status = "cancelled"
                    self.log("Research cancelled by user.", "info")
                    return

                self.log(f"Starting research round {round_idx} of {self.max_rounds}...", "info")

                # Generate search queries
                query_prompt = f"""You are a research assistant planning web searches to answer the user query.

Original question: {self.query}

Research plan:
{self.research_plan}

Current report progress:
{self.evolving_report}

Round: {round_idx}

Generate 2-3 focused search queries that will help fill gaps in the report. Avoid querying things we already have complete data for.

Return ONLY a JSON array of query strings.
Example: ["query one", "query two"]"""

                query_res = await self.call_llm(query_prompt, "You are a search assistant. Return ONLY a JSON list of search queries.")
                queries = []
                try:
                    cleaned_query_res = query_res.strip()
                    if cleaned_query_res.startswith("```"):
                        lines = cleaned_query_res.split("\n")
                        if lines[0].startswith("```json") or lines[0].startswith("```"):
                            cleaned_query_res = "\n".join(lines[1:-1])
                    queries = json.loads(cleaned_query_res.strip())
                    if not isinstance(queries, list):
                        queries = [str(queries)]
                except Exception:
                    self.log(f"Failed to parse query generator JSON. Using heuristic search.", "warning")
                    queries = [self.query]

                self.log(f"Generated queries for Round {round_idx}: {queries}", "query", queries)

                # Execute searches and compile URLs
                round_results = []
                for q in queries:
                    if await self.check_cancelled():
                        self.status = "cancelled"
                        self.log("Research cancelled by user.", "info")
                        return
                    
                    self.log(f"Searching: '{q}'", "info")
                    results = await self.perform_search(q)
                    round_results.extend(results)

                # Keep unique and unvisited URLs (top 3 per round)
                new_urls_to_crawl = []
                for r in round_results:
                    url = r.get("url")
                    if url and url not in self.visited_urls:
                        new_urls_to_crawl.append(r)
                        self.visited_urls.add(url)
                        if len(new_urls_to_crawl) >= 3:
                            break

                if not new_urls_to_crawl:
                    self.log("No new relevant sources found in this round.", "info")
                else:
                    self.log(f"Crawling and analyzing {len(new_urls_to_crawl)} new sources...", "info")
                    
                    extracted_findings = []
                    for src in new_urls_to_crawl:
                        if await self.check_cancelled():
                            self.status = "cancelled"
                            self.log("Research cancelled by user.", "info")
                            return

                        url = src.get("url")
                        title = src.get("title", url)
                        self.log(f"Crawling: {url}...", "info")
                        
                        page_text = await self.crawl_and_parse_url(url)
                        if page_text:
                            # Save to self.sources list
                            self.sources.append({
                                "title": title,
                                "url": url,
                                "snippet": src.get("snippet", "")
                            })
                            self.log(f"Successfully scraped content from {title} ({len(page_text)} chars)", "info")
                            
                            # Extract facts from page content
                            extraction_prompt = f"""You are a research analyst extracting information from a website page.

User Query: {self.query}
Research Plan Questions:
{self.research_plan}

Website Title: {title}
Website URL: {url}

Website Text Content:
{page_text}

Extract any facts, statistics, numbers, quotes, or findings from this website that help answer the User Query and sub-questions. 
Ensure you ground your answers directly in the page text. Do not invent details. Provide source URL inline.
Return ONLY bullet points of findings."""
                            
                            findings = await self.call_llm(extraction_prompt, "You are a factual research analyst.")
                            extracted_findings.append(f"### Findings from [{title}]({url}):\n{findings}\n")
                            self.log(f"Extracted findings from {title}", "info")
                        else:
                            self.log(f"Could not scrape {title}, falling back to search snippet.", "info")
                            self.sources.append({
                                "title": title,
                                "url": url,
                                "snippet": src.get("snippet", "")
                            })
                            extracted_findings.append(f"### Snippet from [{title}]({url}):\n- {src.get('snippet', 'No content available.')}\n")

                    # Step 3: Synthesize findings into the evolving report
                    self.log("Synthesizing new findings into evolving report...", "info")
                    new_findings_text = "\n".join(extracted_findings)
                    
                    synth_prompt = f"""You are updating an evolving research report.

Original question: {self.query}

Current report progress:
{self.evolving_report}

New findings to integrate:
{new_findings_text}

Integrate the new findings into the existing report. Produce an updated, well-organized report that answers the original question as completely as possible.
- Group similar topics.
- Remove redundancy.
- Maintain source URLs as inline Markdown links.
- Write only the updated report — no preamble or meta-commentary."""

                    self.evolving_report = await self.call_llm(synth_prompt, "You are a reports writer. Output ONLY the updated markdown report.")
                    self.log(f"Round {round_idx} report synthesis complete.", "synthesize")

                # Step 4: Evaluate if report is comprehensive enough to stop early
                if round_idx >= 2:  # Wait at least 2 rounds
                    self.log("Evaluating report completeness...", "info")
                    stop_prompt = f"""You are deciding whether a research report is comprehensive enough.

Original question: {self.query}

Current report:
{self.evolving_report}

Rounds completed: {round_idx} of {self.max_rounds}

Based on the report so far, do we have enough information to answer the question comprehensively? 
Consider:
- Are all sub-questions in the research plan addressed?
- Are there major gaps?
- Do we have sufficient details?

Reply with ONLY "YES" or "NO" followed by a brief one-sentence reason.
Example: YES - The report covers all aspects with cited evidence."""

                    stop_res = await self.call_llm(stop_prompt, "Return ONLY YES or NO followed by a reason.")
                    if stop_res.strip().upper().startswith("YES"):
                        self.log(f"Stopping early: {stop_res.strip()}", "info")
                        break
                    else:
                        self.log(f"Continuing research: {stop_res.strip()}", "info")

            # Final Step: Compile magazine-quality final report
            self.log("Compiling final magazine-quality research report...", "info")
            final_prompt = f"""Write a detailed, comprehensive, magazine-quality final research report answering this question:

Question: {self.query}

All collected evidence and draft notes:
{self.evolving_report}

Requirements:
- Write a thorough, comprehensive report.
- Organize into logical sections with clear ## headings and ### subheadings.
- Synthesize the info: explain WHY things matter, make comparisons, provide context.
- Include specific numbers, statistics, and dates.
- Keep source URLs as inline Markdown links.
- Add an Executive Summary at the top and a clear Conclusion answering the query.
- Write only the final report markdown. Do not include introductory notes or final commentary."""

            final_report = await self.call_llm(final_prompt, "You are a professional research report compiler. Return only the Markdown report.")
            self.evolving_report = final_report
            self.status = "done"
            self.log("Research successfully completed!", "done")

        except Exception as e:
            logger.error(f"Error in deep research task runner: {e}", exc_info=True)
            self.status = "failed"
            self.error = str(e)
            self.log(f"Research failed: {e}", "error")

async def run_deep_research_task(session_id: str, query: str, model_name: str, max_rounds: int, config: Dict[str, Any]):
    researcher = DeepResearcher(session_id, query, model_name, max_rounds, config)
    # Add to active tasks list
    _sessions_registry[session_id] = {
        "id": session_id,
        "query": query,
        "model_name": model_name,
        "max_rounds": max_rounds,
        "current_round": 0,
        "status": "running",
        "logs": [],
        "sources": [],
        "evolving_report": "",
        "research_plan": "",
        "error": None,
        "started_at": time.time(),
        "completed_at": None
    }
    await researcher.run()
