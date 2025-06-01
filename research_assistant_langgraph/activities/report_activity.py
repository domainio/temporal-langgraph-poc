import uuid
from temporalio import activity
from temporalio.exceptions import ApplicationError
from typing import List

from ..config import Config
from ..schemas.types import ResearchPlanDict, ResearchSection, ReportGraphState
from ..utils.graph_builder import GraphBuilder, log_graph_execution

@activity.defn
async def report_generation_activity_with_langgraph(plan: ResearchPlanDict, sections: List[ResearchSection]) -> str:
    """Report generation using LangGraph StateGraph with checkpointing"""
    activity.logger.info(f"[Report] Starting LangGraph-based report generation for: {plan['topic']}")
    
    try:
        # Import LangChain components inside the activity to avoid sandbox issues
        from langchain_core.messages import HumanMessage
        from langchain_core.prompts import ChatPromptTemplate
        
        def create_executive_summary_node(state: ReportGraphState) -> ReportGraphState:
            """Create executive summary from all sections"""
            llm = Config.get_llm()
            log_graph_execution("Report", "Creating executive summary")
            
            # Prepare section summaries
            section_summaries = "\n\n".join([
                f"**{section['title']}**: {section['content'][:300]}..."
                for section in state["sections"]
            ])
            
            prompt = ChatPromptTemplate.from_template("""
            Create a comprehensive executive summary for this research report:
            
            Topic: {topic}
            Number of sections: {num_sections}
            
            SECTION CONTENT PREVIEWS:
            {section_summaries}
            
            Create an executive summary that:
            - Captures the key findings across all sections
            - Highlights the most important insights
            - Provides a clear overview of the research scope
            - Is engaging and informative (300-500 words)
            
            Write in a professional, accessible tone.
            """)
            
            response = llm.invoke([HumanMessage(content=prompt.format(
                topic=state["research_plan"]["topic"],
                num_sections=len(state["sections"]),
                section_summaries=section_summaries
            ))])
            
            return {
                **state,
                "executive_summary": response.content,
                "summary_created": True,
                "messages": [response]
            }
        
        def compile_main_content_node(state: ReportGraphState) -> ReportGraphState:
            """Compile main content with proper formatting"""
            log_graph_execution("Report", "Compiling main content")
            
            # Create table of contents
            toc = "\n".join([
                f"{i}. {section['title']}"
                for i, section in enumerate(state["sections"], 1)
            ])
            
            # Compile sections with proper formatting
            main_content = f"""## Table of Contents

{toc}

## Methodology

{state["research_plan"]["methodology"]}

---

"""
            
            # Add all sections
            for i, section in enumerate(state["sections"], 1):
                main_content += f"\n## {i}. {section['title']}\n\n{section['content']}\n\n"
            
            return {
                **state,
                "main_content": main_content,
                "content_compiled": True
            }
        
        def create_conclusion_node(state: ReportGraphState) -> ReportGraphState:
            """Create synthesized conclusion"""
            llm = Config.get_llm()
            log_graph_execution("Report", "Creating conclusion")
            
            # Prepare key points from all sections
            key_points = "\n".join([
                f"- {section['title']}: {section['content'][:200]}..."
                for section in state["sections"]
            ])
            
            prompt = ChatPromptTemplate.from_template("""
            Create a comprehensive conclusion for this research report:
            
            Topic: {topic}
            
            KEY FINDINGS FROM SECTIONS:
            {key_points}
            
            Write a conclusion that:
            - Synthesizes findings across all research areas
            - Identifies patterns and connections
            - Discusses implications and significance
            - Suggests areas for future research
            - Provides a thoughtful wrap-up (400-600 words)
            
            Focus on insights that emerge from connecting the different research areas.
            """)
            
            response = llm.invoke([HumanMessage(content=prompt.format(
                topic=state["research_plan"]["topic"],
                key_points=key_points
            ))])
            
            return {
                **state,
                "conclusion": response.content,
                "conclusion_written": True,
                "messages": state["messages"] + [response]
            }
        
        def compile_sources_node(state: ReportGraphState) -> ReportGraphState:
            """Compile and organize all sources"""
            log_graph_execution("Report", "Compiling sources")
            
            # Collect all sources
            all_sources = []
            for section in state["sections"]:
                all_sources.extend(section['sources'])
            
            unique_sources = list(set([s for s in all_sources if s not in ["Error in research process", ""]]))
            
            # Separate URLs from other sources
            url_sources = [s for s in unique_sources if s.startswith('http')]
            other_sources = [s for s in unique_sources if not s.startswith('http')]
            
            sources_section = "## Sources\n\n"
            
            if url_sources:
                sources_section += "### Web Sources\n"
                for i, source in enumerate(sorted(url_sources), 1):
                    sources_section += f"{i}. {source}\n"
            
            if other_sources:
                sources_section += "\n### Research Sources\n"
                for source in sorted(other_sources):
                    sources_section += f"- {source}\n"
            
            # Add metadata
            sources_section += f"\n\n---\n"
            sources_section += f"*Report generated using Temporal-orchestrated LangGraph research workflow*\n"
            sources_section += f"*Sections researched: {len(state['sections'])}*\n"
            sources_section += f"*Total sources: {len(unique_sources)}*\n"
            sources_section += f"*Total queries executed: {sum(len(s.get('queries_used', [])) for s in state['sections'])}*"
            
            return {
                **state,
                "sources_section": sources_section,
                "sources_compiled": True
            }
        
        def finalize_report_node(state: ReportGraphState) -> ReportGraphState:
            """Combine all parts into final report"""
            log_graph_execution("Report", "Finalizing report")
            
            final_report = f"""# {state["research_plan"]["topic"]} - Comprehensive Research Report

## Executive Summary

{state["executive_summary"]}

{state["main_content"]}

## Conclusion

{state["conclusion"]}

{state["sources_section"]}
"""
            
            return {
                **state,
                "final_report": final_report,
                "report_finalized": True
            }
        
        # Build the report generation graph with checkpointing enabled
        report_graph = GraphBuilder.create_linear_flow(
            ReportGraphState,
            [
                ("create_executive_summary", create_executive_summary_node),
                ("compile_main_content", compile_main_content_node),
                ("create_conclusion", create_conclusion_node),
                ("compile_sources", compile_sources_node),
                ("finalize_report", finalize_report_node)
            ],
            enable_checkpointing=True  # Enable checkpointing for state persistence
        )
        
        # Create a unique thread ID for this report generation session
        thread_id = f"report_{plan['topic'].lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
        config = {"configurable": {"thread_id": thread_id}}
        
        # Execute the report generation graph with checkpointing
        log_graph_execution("Report", "Executing report generation workflow with checkpointing", f"thread_id: {thread_id}")
        report_result = report_graph.invoke({
            "research_plan": plan,
            "sections": sections,
            "executive_summary": "",
            "main_content": "",
            "conclusion": "",
            "sources_section": "",
            "final_report": "",
            "summary_created": False,
            "content_compiled": False,
            "conclusion_written": False,
            "sources_compiled": False,
            "report_finalized": False,
            "messages": []
        }, config)
        
        # Log checkpoint information for debugging
        try:
            final_state = report_graph.get_state(config)
            activity.logger.info(f"[Report] Checkpoint saved with ID: {final_state.config.get('checkpoint_id', 'unknown')}")
            activity.logger.info(f"[Report] Final state contains {len(final_state.values.get('messages', []))} messages")
            activity.logger.info(f"[Report] Report finalized: {final_state.values.get('report_finalized', False)}")
        except Exception as e:
            activity.logger.warning(f"[Report] Could not retrieve checkpoint info: {e}")
        
        # Return final report
        final_report = report_result["final_report"]
        log_graph_execution("Report", "Completed", f"{len(final_report)} characters")
        return final_report
        
    except Exception as e:
        activity.logger.error(f"[Report Graph] Failed: {e}")
        raise ApplicationError(f"LangGraph report generation failed: {str(e)}") 