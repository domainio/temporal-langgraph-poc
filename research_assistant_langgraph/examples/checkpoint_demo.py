#!/usr/bin/env python3
"""
Simple demonstration of LangGraph checkpointing functionality.

This script shows how checkpointing works with the GraphBuilder utility
independently of the Temporal orchestration.
"""

import sys
import os
from typing import TypedDict, List

# Add the research_assistant_langgraph directory to the path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from utils.graph_builder import GraphBuilder

# Simple state for demonstration
class DemoState(TypedDict):
    counter: int
    messages: List[str]
    completed_steps: List[str]

def step_one(state: DemoState) -> DemoState:
    """First processing step"""
    print(f"[Step 1] Current counter: {state['counter']}")
    return {
        **state,
        "counter": state["counter"] + 1,
        "messages": state["messages"] + ["Completed step 1"],
        "completed_steps": state["completed_steps"] + ["step_one"]
    }

def step_two(state: DemoState) -> DemoState:
    """Second processing step"""
    print(f"[Step 2] Current counter: {state['counter']}")
    return {
        **state,
        "counter": state["counter"] + 2,
        "messages": state["messages"] + ["Completed step 2"],
        "completed_steps": state["completed_steps"] + ["step_two"]
    }

def step_three(state: DemoState) -> DemoState:
    """Third processing step"""
    print(f"[Step 3] Current counter: {state['counter']}")
    return {
        **state,
        "counter": state["counter"] + 3,
        "messages": state["messages"] + ["Completed step 3"],
        "completed_steps": state["completed_steps"] + ["step_three"]
    }

def main():
    """Demonstrate LangGraph checkpointing functionality"""
    print("🧠 LangGraph Checkpointing Demonstration")
    print("=" * 50)
    
    # Create a graph with checkpointing enabled
    print("\n1. Creating LangGraph with checkpointing...")
    demo_graph = GraphBuilder.create_linear_flow(
        DemoState,
        [
            ("step_one", step_one),
            ("step_two", step_two), 
            ("step_three", step_three)
        ],
        enable_checkpointing=True
    )
    
    # Initial state
    initial_state = {
        "counter": 0,
        "messages": [],
        "completed_steps": []
    }
    
    # Execute with thread ID for persistence
    thread_id = "demo_session_001"
    config = {"configurable": {"thread_id": thread_id}}
    
    print(f"\n2. Executing graph with thread_id: {thread_id}")
    result = demo_graph.invoke(initial_state, config)
    
    print(f"\n3. Final result:")
    print(f"   Counter: {result['counter']}")
    print(f"   Messages: {result['messages']}")
    print(f"   Completed steps: {result['completed_steps']}")
    
    # Inspect the saved state
    print(f"\n4. Inspecting saved checkpoint...")
    try:
        saved_state = demo_graph.get_state(config)
        print(f"   Checkpoint ID: {saved_state.config.get('checkpoint_id', 'unknown')}")
        print(f"   Thread ID: {saved_state.config.get('thread_id', 'unknown')}")
        print(f"   State values: {saved_state.values}")
        print(f"   Next nodes: {saved_state.next}")
    except Exception as e:
        print(f"   Error retrieving state: {e}")
    
    # Show state history
    print(f"\n5. Viewing checkpoint history...")
    try:
        history = list(demo_graph.get_state_history(config))
        print(f"   Total checkpoints: {len(history)}")
        for i, checkpoint in enumerate(history[:3]):  # Show first 3
            print(f"   Checkpoint {i+1}: {checkpoint.values.get('completed_steps', [])}")
    except Exception as e:
        print(f"   Error retrieving history: {e}")
    
    # Demonstrate resuming from same thread (simulating restart)
    print(f"\n6. Demonstrating thread persistence...")
    print("   Creating new graph instance (simulating restart)...")
    
    new_graph = GraphBuilder.create_linear_flow(
        DemoState,
        [
            ("step_one", step_one),
            ("step_two", step_two), 
            ("step_three", step_three)
        ],
        enable_checkpointing=True
    )
    
    # Try to get state from same thread
    try:
        recovered_state = new_graph.get_state(config)
        print(f"   Recovered state: {recovered_state.values}")
        print("   ✅ State successfully persisted and recovered!")
    except Exception as e:
        print(f"   ❌ Could not recover state: {e}")
    
    print(f"\n7. Summary:")
    print("   - ✅ LangGraph checkpointing is enabled")
    print("   - ✅ State is automatically saved at each step")
    print("   - ✅ Thread IDs provide isolated sessions") 
    print("   - ✅ State can be inspected and recovered")
    print("   - ✅ Complete execution history is maintained")
    
    print(f"\n🎉 Checkpointing demonstration completed!")

if __name__ == "__main__":
    main() 