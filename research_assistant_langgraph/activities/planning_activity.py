from temporalio import activity
from temporalio.exceptions import ApplicationError
import uuid

from ..config import Config
from ..schemas.types import ResearchPlanDict, PlanningGraphState, ResearchPlan
from ..utils.graph_builder import GraphBuilder, log_graph_execution

@activity.defn
async def planning_activity_with_langgraph(topic: str, max_sections: int) -> ResearchPlanDict:
    """Planning activity using LangGraph StateGraph with checkpointing"""
    activity.logger.info(f"[Planning] Starting LangGraph-based planning for: {topic}")
    
    try:
        # Import LangChain components inside the activity to avoid sandbox issues
        from langchain_core.messages import HumanMessage
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_core.output_parsers import PydanticOutputParser
        
        def analyze_topic_node(state: PlanningGraphState) -> PlanningGraphState:
            """Analyze the research topic and create initial structure"""
            llm = Config.get_llm()
            log_graph_execution("Planning", "Analyzing topic", state['topic'])
            
            prompt = ChatPromptTemplate.from_template("""
            Analyze this research topic and provide initial insights: {topic}
            
            Consider:
            - What are the main aspects to research?
            - What methodology would be most appropriate?
            - What are the key areas that need coverage?
            
            Provide a structured analysis of the research scope and approach.
            """)
            
            response = llm.invoke([HumanMessage(content=prompt.format(topic=state["topic"]))])
            
            return {
                **state,
                "analysis_complete": True,
                "messages": [response]
            }
        
        def create_plan_node(state: PlanningGraphState) -> PlanningGraphState:
            """Create detailed research plan based on analysis"""
            llm = Config.get_llm()
            parser = PydanticOutputParser(pydantic_object=ResearchPlan)
            
            log_graph_execution("Planning", "Creating plan", f"{state['max_sections']} sections")
            
            # Use previous analysis for context
            analysis_context = state["messages"][-1].content if state["messages"] else ""
            
            prompt = ChatPromptTemplate.from_template("""
            Based on this topic analysis:
            {analysis_context}
            
            Create a detailed research plan for: {topic}
            
            Requirements:
            - Exactly {max_sections} sections
            - Each section should focus on a specific, distinct aspect
            - Sections should be comprehensive and non-overlapping
            - Include appropriate research methodology
            
            {format_instructions}
            """)
            
            formatted_prompt = prompt.format(
                topic=state["topic"],
                max_sections=state["max_sections"],
                analysis_context=analysis_context,
                format_instructions=parser.get_format_instructions()
            )
            
            response = llm.invoke([HumanMessage(content=formatted_prompt)])
            research_plan = parser.parse(response.content)
            
            plan_dict = {
                "topic": research_plan.topic,
                "sections": research_plan.sections[:state["max_sections"]],
                "methodology": research_plan.methodology,
                "estimated_length": research_plan.estimated_length
            }
            
            return {
                **state,
                "research_plan": plan_dict,
                "plan_refined": True,
                "messages": state["messages"] + [response]
            }
        
        # Build the planning graph with checkpointing enabled
        planning_graph = GraphBuilder.create_linear_flow(
            PlanningGraphState,
            [
                ("analyze_topic", analyze_topic_node),
                ("create_plan", create_plan_node)
            ],
            enable_checkpointing=True  # Enable checkpointing for state persistence
        )
        
        # Create a unique thread ID for this planning session
        thread_id = f"planning_{uuid.uuid4().hex[:8]}"
        config = {"configurable": {"thread_id": thread_id}}
        
        # Execute the planning graph with checkpointing
        log_graph_execution("Planning", "Executing planning workflow with checkpointing", f"thread_id: {thread_id}")
        planning_result = planning_graph.invoke({
            "topic": topic,
            "max_sections": max_sections,
            "research_plan": None,
            "analysis_complete": False,
            "plan_refined": False,
            "messages": []
        }, config)
        
        # Log checkpoint information for debugging
        try:
            final_state = planning_graph.get_state(config)
            activity.logger.info(f"[Planning] Checkpoint saved with ID: {final_state.config.get('checkpoint_id', 'unknown')}")
            activity.logger.info(f"[Planning] Final state contains {len(final_state.values.get('messages', []))} messages")
        except Exception as e:
            activity.logger.warning(f"[Planning] Could not retrieve checkpoint info: {e}")
        
        # Extract and return the plan
        final_plan = planning_result["research_plan"]
        
        result = ResearchPlanDict(
            topic=final_plan["topic"],
            sections=final_plan["sections"],
            methodology=final_plan["methodology"],
            estimated_length=final_plan["estimated_length"]
        )
        
        log_graph_execution("Planning", "Completed", f"{len(result['sections'])} sections planned")
        return result
        
    except Exception as e:
        activity.logger.error(f"[Planning Graph] Failed: {e}")
        raise ApplicationError(f"LangGraph planning failed: {str(e)}") 