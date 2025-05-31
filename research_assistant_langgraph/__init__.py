"""
Research Assistant with LangGraph Integration

A modular research assistant that combines Temporal workflow orchestration
with LangGraph's intelligent graph-based workflow management.

Key Components:
- Temporal: Provides distributed orchestration, fault tolerance, and scaling
- LangGraph: Provides intelligent workflow logic and conditional flows

Usage:
    # Start worker
    python -m research_assistant_langgraph.worker
    
    # Run research
    python -m research_assistant_langgraph.client "your research topic"
"""

from .config import Config
from .workflow import ResearchAssistantWorkflow
from .worker import run_research_worker
from .client import start_research_workflow

__version__ = "1.0.0"
__all__ = [
    "Config",
    "ResearchAssistantWorkflow", 
    "run_research_worker",
    "start_research_workflow"
] 