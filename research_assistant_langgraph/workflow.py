import asyncio
from datetime import timedelta
from temporalio import workflow
from temporalio.common import RetryPolicy

from .schemas.types import ResearchState
from .activities.planning_activity import planning_activity_with_langgraph
from .activities.research_activity import research_section_activity_with_langgraph
from .activities.report_activity import report_generation_activity_with_langgraph

@workflow.defn
class ResearchAssistantWorkflow:
    """LangGraph-enabled research assistant workflow"""
    
    @workflow.run
    async def run(self, research_topic: str, max_sections: int = 5, search_depth: int = 3) -> ResearchState:
        """Execute the complete research workflow with LangGraph integration"""
        workflow.logger.info(f"Starting LangGraph-enabled research workflow for: {research_topic}")
        
        state: ResearchState = {
            "research_topic": research_topic,
            "max_sections": max_sections,
            "search_depth": search_depth,
            "research_plan": None,
            "plan_approved": False,
            "completed_sections": [],
            "current_section_index": 0,
            "final_report": "",
            "report_metadata": {},
            "current_phase": "planning",
            "error_message": ""
        }
        
        try:
            # Phase 1: LangGraph-based Planning
            workflow.logger.info("Phase 1: LangGraph Planning")
            state["current_phase"] = "planning"
            
            research_plan = await workflow.execute_activity(
                planning_activity_with_langgraph,
                args=[research_topic, max_sections],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(maximum_attempts=2)
            )
            
            state["research_plan"] = research_plan
            state["plan_approved"] = True
            
            # Phase 2: LangGraph-based Research (parallel)
            workflow.logger.info("Phase 2: LangGraph Research")
            state["current_phase"] = "research"
            
            section_activities = []
            for section_title in research_plan["sections"]:
                activity = workflow.execute_activity(
                    research_section_activity_with_langgraph,
                    args=[section_title, research_topic, search_depth],
                    start_to_close_timeout=timedelta(minutes=15),
                    retry_policy=RetryPolicy(maximum_attempts=2)
                )
                section_activities.append(activity)
            
            section_results = await asyncio.gather(*section_activities)
            
            for section_result in section_results:
                state["completed_sections"].append(section_result)
            
            # Phase 3: LangGraph-based Report Generation
            workflow.logger.info("Phase 3: LangGraph Report Generation")
            state["current_phase"] = "writing"
            
            final_report = await workflow.execute_activity(
                report_generation_activity_with_langgraph,
                args=[research_plan, state["completed_sections"]],
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(maximum_attempts=2)
            )
            
            state["final_report"] = final_report
            state["report_metadata"] = {
                "sections_count": len(state["completed_sections"]),
                "total_sources": sum(len(section["sources"]) for section in state["completed_sections"]),
                "word_count": len(final_report.split()),
                "generated_at": workflow.now().isoformat(),
                "total_queries": sum(len(section.get("queries_used", [])) for section in state["completed_sections"])
            }
            
            state["current_phase"] = "complete"
            workflow.logger.info("LangGraph-enabled research workflow completed successfully")
            
        except Exception as e:
            workflow.logger.error(f"LangGraph research workflow failed: {e}")
            state["error_message"] = str(e)
            state["current_phase"] = "complete"
        
        return state 