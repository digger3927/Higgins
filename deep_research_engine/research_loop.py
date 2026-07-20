import json
import os
from typing import List, Dict, Any
from deep_research_engine.config import config
from deep_research_engine.engine_router import search_engine, inference_engine

class ResearchState:
    def __init__(self, prompt: str):
        self.prompt = prompt
        self.iteration = 0
        self.queries: List[str] = []
        self.findings: List[Dict[str, str]] = []
        self.synthesis = ""
        self.is_complete = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "prompt": self.prompt,
            "iteration": self.iteration,
            "queries": self.queries,
            "findings": self.findings,
            "synthesis": self.synthesis,
            "is_complete": self.is_complete
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ResearchState':
        state = cls(data["prompt"])
        state.iteration = data["iteration"]
        state.queries = data["queries"]
        state.findings = data["findings"]
        state.synthesis = data["synthesis"]
        state.is_complete = data["is_complete"]
        return state

    def save(self):
        with open(config.STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4)

def run_research(prompt: str, progress_callback=None) -> ResearchState:
    print(f"Starting research for: {prompt}")
    state = ResearchState(prompt)
    state.save()
    if progress_callback:
        progress_callback(state)

    while state.iteration < config.MAX_ITERATIONS and not state.is_complete:
        print(f"--- Iteration {state.iteration + 1}/{config.MAX_ITERATIONS} ---")
        
        # 1. Decompose prompt into sub-queries
        decomposition_prompt = f"Given the main goal: '{prompt}', and current findings: {json.dumps(state.findings)}, analyze what information is still missing. Then, provide the next 3 best search queries to find that missing information. Return ONLY a JSON object in this format:\n{{\n  \"analysis\": \"what is missing\",\n  \"queries\": [\"query1\", \"query2\", \"query3\"]\n}}\nIf completely done and no more info is needed, return {{\n  \"analysis\": \"done\",\n  \"queries\": [\"DONE\"]\n}}.\nNEVER return DONE on the first iteration (when findings is empty)."
        response = inference_engine.generate(decomposition_prompt).strip()
        try:
            if "{" in response and "}" in response:
                response = response[response.find("{"):response.rfind("}")+1]
                parsed = json.loads(response)
                print(f"Agent Analysis: {parsed.get('analysis', '')}")
                next_queries = parsed.get("queries", [])
            else:
                next_queries = []
        except Exception as e:
            print(f"Error parsing next queries: {e}")
            next_queries = []
        
        if "DONE" in next_queries or not next_queries:
            print("Model indicated no further queries needed.")
            state.is_complete = True
            break
            
        print(f"Next queries identified: {next_queries}")
        state.queries.extend(next_queries)
        
        # 2. Run search for each query
        for next_query in next_queries:
            if next_query == "DONE": continue
            print(f"Processing query: {next_query}")
            results = search_engine.search(next_query)
            
            # 3. Extract and process
            iteration_findings = ""
            for res in results:
                content = search_engine.fetch_page(res['url'])
                if content:
                    iteration_findings += f"Source: {res['url']}\nContent: {content}\n\n"
                else:
                    iteration_findings += f"Source: {res['url']}\nSnippet: {res['snippet']}\n\n"
            
            # Extract useful info
            extraction_prompt = f"Extract all relevant facts, statistics, and insightful quotes answering '{next_query}' from the following text. Be extremely detailed and comprehensive:\n{iteration_findings}"
            extracted_facts = inference_engine.generate(extraction_prompt)
            
            state.findings.append({"query": next_query, "facts": extracted_facts})
            
        state.iteration += 1
        state.save()
        if progress_callback:
            progress_callback(state)
        
    print("Research loop complete. Synthesizing final report...")
    synthesis_prompt = f"Synthesize a comprehensive report for the goal '{prompt}' based on these findings: {json.dumps(state.findings)}. Provide a well-structured HTML report. Include <img> tags to fetch relevant images from pollinations.ai (e.g. <img src=\"https://image.pollinations.ai/prompt/description%20of%20image\" alt=\"...\">). ONLY return HTML, no markdown."
    state.synthesis = inference_engine.generate(synthesis_prompt)
    state.is_complete = True
    state.save()
    
    return state
