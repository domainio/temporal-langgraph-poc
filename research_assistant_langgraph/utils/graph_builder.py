from typing import TypeVar, Callable, Dict, Any, Optional
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import InMemorySaver
from temporalio import activity

StateType = TypeVar('StateType')
NodeFunction = Callable[[StateType], StateType]

class GraphBuilder:
    """Utility class for building LangGraph StateGraphs with common patterns"""
    
    def __init__(self, state_type: type):
        self.state_type = state_type
        self.graph = StateGraph(state_type)
        self.nodes: Dict[str, NodeFunction] = {}
        
    def add_node(self, name: str, func: NodeFunction) -> 'GraphBuilder':
        """Add a node to the graph"""
        self.nodes[name] = func
        self.graph.add_node(name, func)
        return self
    
    def add_edge(self, from_node: str, to_node: str) -> 'GraphBuilder':
        """Add an edge between nodes"""
        self.graph.add_edge(from_node, to_node)
        return self
    
    def add_conditional_edge(self, from_node: str, condition_func: Callable, node_mapping: Dict[str, str]) -> 'GraphBuilder':
        """Add a conditional edge"""
        self.graph.add_conditional_edges(from_node, condition_func, node_mapping)
        return self
    
    def set_entry_point(self, node_name: str) -> 'GraphBuilder':
        """Set the entry point of the graph"""
        self.graph.set_entry_point(node_name)
        return self
    
    def compile(self, checkpointer=None):
        """Compile and return the graph with optional checkpointing"""
        if checkpointer is not None:
            return self.graph.compile(checkpointer=checkpointer)
        return self.graph.compile()
    
    @staticmethod
    def create_memory_checkpointer():
        """Create a simple in-memory checkpointer for basic persistence"""
        return InMemorySaver()
    
    @staticmethod
    def create_linear_flow(state_type: type, nodes: list[tuple[str, NodeFunction]], enable_checkpointing: bool = False) -> StateGraph:
        """
        Create a simple linear flow graph where nodes execute in sequence
        
        Args:
            state_type: The TypedDict class for state
            nodes: List of (name, function) tuples
            enable_checkpointing: Whether to enable memory checkpointing
        
        Returns:
            Compiled StateGraph
        """
        builder = GraphBuilder(state_type)
        
        # Add all nodes
        for name, func in nodes:
            builder.add_node(name, func)
        
        # Set entry point to first node
        if nodes:
            builder.set_entry_point(nodes[0][0])
            
            # Create linear edges
            for i in range(len(nodes) - 1):
                builder.add_edge(nodes[i][0], nodes[i + 1][0])
            
            # Connect last node to END
            builder.add_edge(nodes[-1][0], END)
        
        # Compile with optional checkpointing
        checkpointer = GraphBuilder.create_memory_checkpointer() if enable_checkpointing else None
        return builder.compile(checkpointer=checkpointer)
    
    @staticmethod
    def create_conditional_flow(
        state_type: type, 
        entry_node: tuple[str, NodeFunction],
        conditional_nodes: Dict[str, NodeFunction],
        condition_func: Callable,
        end_node: tuple[str, NodeFunction] = None,
        enable_checkpointing: bool = False
    ) -> StateGraph:
        """
        Create a conditional flow where execution path depends on state
        
        Args:
            state_type: The TypedDict class for state
            entry_node: (name, function) for entry point
            conditional_nodes: Dict of condition_result -> node_function
            condition_func: Function that returns which path to take
            end_node: Optional final node, if None goes directly to END
            enable_checkpointing: Whether to enable memory checkpointing
        
        Returns:
            Compiled StateGraph
        """
        builder = GraphBuilder(state_type)
        
        # Add entry node
        builder.add_node(entry_node[0], entry_node[1])
        builder.set_entry_point(entry_node[0])
        
        # Add conditional nodes
        for name, func in conditional_nodes.items():
            builder.add_node(name, func)
        
        # Create condition mapping
        condition_mapping = {result: name for result, name in conditional_nodes.items()}
        if end_node is None:
            condition_mapping.update({name: END for name in conditional_nodes.keys()})
        
        # Add conditional edge from entry
        builder.add_conditional_edge(entry_node[0], condition_func, condition_mapping)
        
        # Add end node if specified
        if end_node:
            builder.add_node(end_node[0], end_node[1])
            for name in conditional_nodes.keys():
                builder.add_edge(name, end_node[0])
            builder.add_edge(end_node[0], END)
        
        # Compile with optional checkpointing
        checkpointer = GraphBuilder.create_memory_checkpointer() if enable_checkpointing else None
        return builder.compile(checkpointer=checkpointer)

def log_graph_execution(phase: str, step: str, details: str = ""):
    """Helper function for consistent logging across graph executions"""
    activity.logger.info(f"[{phase} Graph] {step}{f': {details}' if details else ''}")

def create_message_summary(messages: list, max_length: int = 1000) -> str:
    """Create a summary of messages for context passing"""
    if not messages:
        return ""
    
    # Get the last message content
    last_message = messages[-1]
    content = getattr(last_message, 'content', str(last_message))
    
    # Truncate if too long
    if len(content) > max_length:
        content = content[:max_length] + "..."
    
    return content

def extract_sources_from_search_results(search_results: list) -> list[str]:
    """Extract and deduplicate sources from search results"""
    sources = []
    for result in search_results:
        if result.get("source") not in ["Error", "DuckDuckGo Search"]:
            sources.append(result["source"])
        elif result.get("source") == "DuckDuckGo Search" and result.get("urls"):
            sources.extend(result["urls"])
    
    # Add generic source if no specific URLs found
    if not sources and any(result.get("source") == "DuckDuckGo Search" for result in search_results):
        sources.append("DuckDuckGo Search Results")
    
    return list(set(sources))  # Remove duplicates 