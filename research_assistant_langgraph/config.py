import os
from dotenv import load_dotenv

# Load environment variables at module level
load_dotenv()

class Config:
    """Configuration settings for the research assistant"""
    
    # LLM Configuration
    DEFAULT_LLM_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
    DEFAULT_LLM_MODEL = os.getenv("DEFAULT_LLM_MODEL", "gpt-4o-mini")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    
    # Search Configuration
    DEFAULT_SEARCH_PROVIDER = os.getenv("DEFAULT_SEARCH_PROVIDER", "duckduckgo")
    TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")
    MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", "2000"))
    
    # Temporal Configuration
    TEMPORAL_HOST = os.getenv("TEMPORAL_HOST", "localhost:7233")
    RESEARCH_TASK_QUEUE = "research-assistant-langgraph-queue"
    
    @classmethod
    def get_llm(cls):
        """Get configured LLM instance"""
        # Import inside method to avoid Temporal sandbox issues
        from langchain_openai import ChatOpenAI
        from langchain_anthropic import ChatAnthropic
        
        if cls.ANTHROPIC_API_KEY and cls.DEFAULT_LLM_PROVIDER == "anthropic":
            return ChatAnthropic(
                model="claude-3-5-sonnet-20241022", 
                api_key=cls.ANTHROPIC_API_KEY, 
                temperature=0.1
            )
        elif cls.OPENAI_API_KEY:
            return ChatOpenAI(
                model=cls.DEFAULT_LLM_MODEL, 
                api_key=cls.OPENAI_API_KEY, 
                temperature=0.1
            )
        else:
            raise ValueError("No LLM API keys configured!")
    
    @classmethod
    def get_search_tool(cls):
        """Get configured search tool"""
        # Import inside method to avoid Temporal sandbox issues
        from langchain_community.tools.tavily_search import TavilySearchResults
        from langchain_community.tools import DuckDuckGoSearchRun
        
        if cls.DEFAULT_SEARCH_PROVIDER == "tavily" and cls.TAVILY_API_KEY:
            return TavilySearchResults(
                api_key=cls.TAVILY_API_KEY, 
                max_results=cls.MAX_SEARCH_RESULTS
            )
        else:
            return DuckDuckGoSearchRun() 