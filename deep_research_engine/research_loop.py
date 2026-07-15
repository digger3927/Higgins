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
        decomposition_prompt = f"Given the main goal: '{prompt}', and current findings: {state.findings}, what is the next single best search query to find missing information? Return ONLY the query string, or say 'DONE' if no more information is needed."
        next_query = inference_engine.generate(decomposition_prompt).strip()
        
        if next_query == "DONE" or not next_query:
            print("Model indicated no further queries needed.")
            state.is_complete = True
            break
            
        print(f"Next query identified: {next_query}")
        state.queries.append(next_query)
        
        # 2. Run search
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
    synthesis_prompt = f"Synthesize a comprehensive report for the goal '{prompt}' based on these findings: {json.dumps(state.findings)}. Provide a well-structured markdown report."
    state.synthesis = inference_engine.generate(synthesis_prompt)
    state.is_complete = True
    state.save()
    
    return state
