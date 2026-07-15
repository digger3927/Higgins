from enum import Enum
from dataclasses import dataclass
from typing import Optional

class RunMode(Enum):
    ONLINE = "online"
    OFFLINE = "offline"

class LLMProvider(Enum):
    OLLAMA = "ollama"
    CLOUD = "cloud"

class OutputFormat(Enum):
    HTML = "html"
    PDF = "pdf"
    BOTH = "both"

@dataclass
class Config:
    """
    Configuration for the Deep Research Tool.
    """
    RUN_MODE: RunMode = RunMode.ONLINE
    MAX_ITERATIONS: int = 5
    LLM_PROVIDER: LLMProvider = LLMProvider.CLOUD
    OUTPUT_FORMAT: OutputFormat = OutputFormat.BOTH
    OLLAMA_MODEL: str = "llama3"
    CLOUD_API_KEY: Optional[str] = None
    CLOUD_API_URL: str = "https://api.openai.com/v1/chat/completions" # Default placeholder
    OUTPUT_DIR: str = "output"
    STATE_FILE: str = "research_state.json"
    
    @classmethod
    def load(cls) -> 'Config':
        """
        Load configuration from environment variables or a configuration file.
        Returns a Config instance with defaults for now.
        """
        return cls()

config = Config.load()
