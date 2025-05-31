from typing import TypedDict, Annotated, List, Dict, Any, Optional, Literal
import operator
from pydantic import BaseModel, Field

# Temporal State schemas
class ResearchSection(TypedDict):
    title: str
    content: str
    sources: List[str]
    queries_used: List[str]

class ResearchPlanDict(TypedDict):
    topic: str
    sections: List[str]
    methodology: str
    estimated_length: int

class ResearchState(TypedDict):
    research_topic: str
    max_sections: int
    search_depth: int
    research_plan: Optional[ResearchPlanDict]
    plan_approved: bool
    completed_sections: Annotated[List[ResearchSection], operator.add]
    current_section_index: int
    final_report: str
    report_metadata: Dict[str, Any]
    current_phase: Literal["planning", "research", "writing", "complete"]
    error_message: str

# LangGraph State schemas
class PlanningGraphState(TypedDict):
    topic: str
    max_sections: int
    research_plan: Optional[Dict[str, Any]]
    analysis_complete: bool
    plan_refined: bool
    messages: Annotated[List, operator.add]

class ResearchGraphState(TypedDict):
    section_title: str
    topic: str
    search_depth: int
    queries: List[str]
    search_results: List[Dict[str, Any]]
    section_content: str
    sources: List[str]
    queries_generated: bool
    searches_completed: bool
    content_synthesized: bool
    messages: Annotated[List, operator.add]

class ReportGraphState(TypedDict):
    research_plan: ResearchPlanDict
    sections: List[ResearchSection]
    executive_summary: str
    main_content: str
    conclusion: str
    sources_section: str
    final_report: str
    summary_created: bool
    content_compiled: bool
    conclusion_written: bool
    sources_compiled: bool
    report_finalized: bool
    messages: Annotated[List, operator.add]

# Pydantic models
class ResearchPlan(BaseModel):
    topic: str = Field(description="The research topic")
    sections: List[str] = Field(description="List of section titles")
    methodology: str = Field(description="Research methodology")
    estimated_length: int = Field(description="Estimated word count") 