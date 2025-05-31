"""
Main entry point for research_assistant_langgraph package

Usage:
    python -m research_assistant_langgraph worker
    python -m research_assistant_langgraph research "topic" [sections] [depth]
"""

import asyncio
import sys

async def main() -> None:
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("LangGraph Research Assistant Usage:")
        print("  python -m research_assistant_langgraph worker")
        print("  python -m research_assistant_langgraph research \"<topic>\" [max_sections] [search_depth]")
        print("\nExamples:")
        print("  python -m research_assistant_langgraph worker")
        print("  python -m research_assistant_langgraph research \"quantum computing applications\"")
        print("  python -m research_assistant_langgraph research \"climate change impacts\" 4 2")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "worker":
        from .worker import run_research_worker
        await run_research_worker()
        
    elif command == "research":
        if len(sys.argv) < 3:
            print("Error: Please provide a research topic")
            sys.exit(1)
            
        topic = sys.argv[2]
        max_sections = int(sys.argv[3]) if len(sys.argv) > 3 else 5
        search_depth = int(sys.argv[4]) if len(sys.argv) > 4 else 3
        
        from .client import start_research_workflow
        await start_research_workflow(topic, max_sections, search_depth)
        
    else:
        print(f"Unknown command: {command}")
        print("Available commands: worker, research")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 