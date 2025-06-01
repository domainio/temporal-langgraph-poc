import re
import uuid
from temporalio import activity
from temporalio.exceptions import ApplicationError

from ..config import Config
from ..schemas.types import ResearchSection, ResearchGraphState
from ..utils.graph_builder import GraphBuilder, log_graph_execution, extract_sources_from_search_results

@activity.defn
async def research_section_activity_with_langgraph(section_title: str, topic: str, search_depth: int) -> ResearchSection:
    """Research activity using LangGraph StateGraph with checkpointing"""
    activity.logger.info(f"[Research] Starting LangGraph-based research for: {section_title}")
    
    try:
        # Import LangChain components inside the activity to avoid sandbox issues
        from langchain_core.messages import HumanMessage
        from langchain_core.prompts import ChatPromptTemplate
        
        def generate_queries_node(state: ResearchGraphState) -> ResearchGraphState:
            """Generate targeted search queries"""
            llm = Config.get_llm()
            log_graph_execution("Research", "Generating queries", f"{state['search_depth']} queries for {state['section_title']}")
            
            prompt = ChatPromptTemplate.from_template("""
            Generate {search_depth} specific, diverse search queries for researching this section:
            
            Section: {section_title}
            Main Topic: {topic}
            
            Requirements:
            - Queries should be specific and focused
            - Cover different aspects of the section
            - Use varied terminology and approaches
            - Target different types of information sources
            
            Return only the queries, one per line, without numbers or bullets.
            """)
            
            response = llm.invoke([HumanMessage(content=prompt.format(
                section_title=state["section_title"],
                topic=state["topic"],
                search_depth=state["search_depth"]
            ))])
            
            queries = [q.strip() for q in response.content.split('\n') if q.strip()]
            queries = queries[:state["search_depth"]]
            
            return {
                **state,
                "queries": queries,
                "queries_generated": True,
                "messages": [response]
            }
        
        def conduct_searches_node(state: ResearchGraphState) -> ResearchGraphState:
            """Conduct web searches using generated queries"""
            search_tool = Config.get_search_tool()
            search_results = []
            
            log_graph_execution("Research", "Conducting searches", f"{len(state['queries'])} searches")
            
            for i, query in enumerate(state["queries"]):
                try:
                    activity.logger.info(f"[Research Graph] Search {i+1}/{len(state['queries'])}: {query}")
                    
                    if hasattr(search_tool, 'run'):
                        # DuckDuckGo
                        result = search_tool.run(query)
                        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', result)
                        unique_urls = list(set(urls))[:3]
                        
                        search_results.append({
                            "query": query,
                            "content": result[:Config.MAX_CONTENT_LENGTH],
                            "source": "DuckDuckGo Search",
                            "urls": unique_urls
                        })
                    else:
                        # Tavily
                        results = search_tool.invoke({"query": query})
                        for result in results:
                            search_results.append({
                                "query": query,
                                "content": result.get("content", "")[:Config.MAX_CONTENT_LENGTH],
                                "source": result.get("url", "Unknown"),
                                "title": result.get("title", ""),
                                "urls": [result.get("url", "")]
                            })
                
                except Exception as e:
                    activity.logger.warning(f"[Research Graph] Search failed for '{query}': {e}")
                    search_results.append({
                        "query": query,
                        "content": f"Search failed: {str(e)}",
                        "source": "Error",
                        "urls": []
                    })
            
            return {
                **state,
                "search_results": search_results,
                "searches_completed": True
            }
        
        def synthesize_content_node(state: ResearchGraphState) -> ResearchGraphState:
            """Synthesize research findings into comprehensive content"""
            llm = Config.get_llm()
            
            log_graph_execution("Research", "Synthesizing content", state['section_title'])
            
            # Prepare search summary
            search_summary = "\n\n".join([
                f"Query: {result['query']}\n"
                f"Source: {result['source']}\n"
                f"Content: {result['content'][:1500]}..."
                for result in state["search_results"]
                if result["source"] != "Error"
            ])
            
            prompt = ChatPromptTemplate.from_template("""
            Create a comprehensive, well-researched section based on the search results below.
            
            Section Title: {section_title}
            Main Topic: {topic}
            
            SEARCH RESULTS:
            {search_results}
            
            REQUIREMENTS:
            - Write a detailed, informative section (800-1200 words)
            - Include specific facts, statistics, and findings from the search results
            - Use clear subsections and markdown formatting
            - Cite specific information where possible
            - Provide objective analysis based on the evidence
            - Include concrete examples and case studies if mentioned in sources
            
            STRUCTURE:
            - Brief introduction to the section topic
            - 2-3 detailed subsections covering different aspects
            - Key findings and implications
            - Specific data points and evidence from research
            
            DO NOT use generic phrases like "research indicates" without specific details.
            DO include actual facts, numbers, and specific findings from the sources.
            """)
            
            response = llm.invoke([HumanMessage(content=prompt.format(
                section_title=state["section_title"],
                topic=state["topic"],
                search_results=search_summary
            ))])
            
            # Extract sources using utility function
            unique_sources = extract_sources_from_search_results(state["search_results"])
            
            return {
                **state,
                "section_content": response.content,
                "sources": unique_sources,
                "content_synthesized": True,
                "messages": state["messages"] + [response]
            }
        
        # Build the research graph with checkpointing enabled
        research_graph = GraphBuilder.create_linear_flow(
            ResearchGraphState,
            [
                ("generate_queries", generate_queries_node),
                ("conduct_searches", conduct_searches_node),
                ("synthesize_content", synthesize_content_node)
            ],
            enable_checkpointing=True  # Enable checkpointing for state persistence
        )
        
        # Create a unique thread ID for this research session
        thread_id = f"research_{section_title.lower().replace(' ', '_')}_{uuid.uuid4().hex[:8]}"
        config = {"configurable": {"thread_id": thread_id}}
        
        # Execute the research graph with checkpointing
        log_graph_execution("Research", "Executing research workflow with checkpointing", f"thread_id: {thread_id}")
        research_result = research_graph.invoke({
            "section_title": section_title,
            "topic": topic,
            "search_depth": search_depth,
            "queries": [],
            "search_results": [],
            "section_content": "",
            "sources": [],
            "queries_generated": False,
            "searches_completed": False,
            "content_synthesized": False,
            "messages": []
        }, config)
        
        # Log checkpoint information for debugging
        try:
            final_state = research_graph.get_state(config)
            activity.logger.info(f"[Research] Checkpoint saved with ID: {final_state.config.get('checkpoint_id', 'unknown')}")
            activity.logger.info(f"[Research] Final state contains {len(final_state.values.get('messages', []))} messages")
            activity.logger.info(f"[Research] Searches completed: {final_state.values.get('searches_completed', False)}")
        except Exception as e:
            activity.logger.warning(f"[Research] Could not retrieve checkpoint info: {e}")
        
        # Create final section
        section = ResearchSection(
            title=section_title,
            content=research_result["section_content"],
            sources=research_result["sources"],
            queries_used=research_result["queries"]
        )
        
        log_graph_execution("Research", "Completed", f"{section_title}: {len(section['content'])} chars, {len(section['sources'])} sources")
        return section
        
    except Exception as e:
        activity.logger.error(f"[Research Graph] Failed for {section_title}: {e}")
        return ResearchSection(
            title=section_title,
            content=f"Research for this section encountered an error: {str(e)}",
            sources=["Error in research process"],
            queries_used=[]
        ) 