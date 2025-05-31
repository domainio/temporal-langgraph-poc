import asyncio
from temporalio.client import Client
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

from .config import Config
from .workflow import ResearchAssistantWorkflow
from .activities.planning_activity import planning_activity_with_langgraph
from .activities.research_activity import research_section_activity_with_langgraph
from .activities.report_activity import report_generation_activity_with_langgraph

async def run_research_worker() -> None:
    """Run the LangGraph-enabled research assistant worker"""
    client = await Client.connect(Config.TEMPORAL_HOST)
    
    # Configure sandbox to allow LangChain and related imports
    restrictions = SandboxRestrictions.default.with_passthrough_modules(
        "langchain_core",
        "langchain_openai", 
        "langchain_anthropic",
        "langchain_community",
        "langgraph",
        "requests",
        "urllib3",
        "httpx",
        "httpcore",
        "pydantic",
        "openai",
        "anthropic",
        "duckduckgo_search"
    )
    
    worker = Worker(
        client,
        task_queue=Config.RESEARCH_TASK_QUEUE,
        workflows=[ResearchAssistantWorkflow],
        activities=[
            planning_activity_with_langgraph, 
            research_section_activity_with_langgraph, 
            report_generation_activity_with_langgraph
        ],
        workflow_runner=SandboxedWorkflowRunner(restrictions=restrictions)
    )
    
    print(f"🔬 LangGraph-enabled Research Worker started")
    print(f"📡 Temporal Host: {Config.TEMPORAL_HOST}")
    print(f"📋 Task Queue: {Config.RESEARCH_TASK_QUEUE}")
    print(f"🤖 LLM Provider: {Config.DEFAULT_LLM_PROVIDER}")
    print(f"🔍 Search Provider: {Config.DEFAULT_SEARCH_PROVIDER}")
    print(f"🔓 Sandbox: Configured with passthrough modules")
    print("=" * 60)
    
    await worker.run()

if __name__ == "__main__":
    asyncio.run(run_research_worker()) 