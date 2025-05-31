import asyncio
import uuid
from temporalio.client import Client

from .config import Config
from .workflow import ResearchAssistantWorkflow
from .schemas.types import ResearchState

async def start_research_workflow(topic: str, max_sections: int = 5, search_depth: int = 3) -> ResearchState:
    """Start LangGraph-enabled research workflow"""
    client = await Client.connect(Config.TEMPORAL_HOST)
    
    print(f"🔬 Starting LangGraph Research for: '{topic}'")
    print(f"📊 Configuration: {max_sections} sections, search depth {search_depth}")
    print(f"📡 Temporal Host: {Config.TEMPORAL_HOST}")
    print(f"📋 Task Queue: {Config.RESEARCH_TASK_QUEUE}")
    print("=" * 80)
    
    try:
        result: ResearchState = await client.execute_workflow(
            ResearchAssistantWorkflow.run,
            args=[topic, max_sections, search_depth],
            id=f"langgraph-research-{topic.replace(' ', '-').lower()}-{uuid.uuid4()}",
            task_queue=Config.RESEARCH_TASK_QUEUE,
        )
        
        print("\n" + "="*80)
        print("🎉 LANGGRAPH RESEARCH COMPLETED!")
        print("="*80)
        
        if result.get("error_message"):
            print(f"❌ Error: {result['error_message']}")
            return result
            
        print(f"📝 Topic: {result['research_topic']}")
        print(f"📈 Phase: {result['current_phase']}")
        
        if result.get("research_plan"):
            plan = result["research_plan"]
            print(f"\n📋 Plan: {len(plan['sections'])} sections")
            for i, section in enumerate(plan["sections"], 1):
                print(f"   {i}. {section}")
        
        print(f"\n📚 Completed: {len(result.get('completed_sections', []))} sections")
        
        if result.get("report_metadata"):
            meta = result["report_metadata"]
            print(f"\n📊 Statistics:")
            print(f"   Word Count: {meta.get('word_count', 0):,}")
            print(f"   Total Sources: {meta.get('total_sources', 0)}")
            print(f"   Total Queries: {meta.get('total_queries', 0)}")
        
        # Save report
        if result.get("final_report"):
            filename = f"langgraph_research_report_{topic.replace(' ', '_').lower()}.md"
            with open(filename, "w") as f:
                f.write(result["final_report"])
            print(f"💾 LangGraph report saved to: {filename}")
        
        return result
        
    except Exception as e:
        print(f"❌ Error: {e}")
        raise

async def main() -> None:
    """Main function for command line usage"""
    import sys
    
    if len(sys.argv) < 2:
        print("LangGraph Research Assistant Usage:")
        print("  python -m research_assistant_langgraph.client \"<topic>\" [max_sections] [search_depth]")
        print("\nExamples:")
        print("  python -m research_assistant_langgraph.client \"quantum computing applications\"")
        print("  python -m research_assistant_langgraph.client \"climate change impacts\" 4 2")
        sys.exit(1)
        
    topic = sys.argv[1]
    max_sections = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    search_depth = int(sys.argv[3]) if len(sys.argv) > 3 else 3
    
    await start_research_workflow(topic, max_sections, search_depth)

if __name__ == "__main__":
    asyncio.run(main()) 