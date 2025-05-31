# POC: Temporal + LangGraph Integration 
## Candidate: Deep Research Agent Workflow

A proof-of-concept research assistant that demonstrates how to combine Temporal workflow orchestration with LangGraph's intelligent graph-based workflow management for building robust AI agent workflows.

## Motivation

Building production AI agent workflows requires both **intelligent decision-making** and **distributed reliability**:

- **LangGraph**: Excellent for AI agent logic but **core is not distributed** - runs on single processes without built-in scaling
- **Temporal**: World-class distributed orchestration that can **make any workflow distributed**

This POC shows how **Temporal distributes LangGraph workflows** to achieve **intelligent AND scalable** AI systems:

```
🤖 LangGraph (Intelligence)  +  ⚡ Temporal (Distribution)  =  🚀 Scalable AI Workflows
```

## Architecture

### 🔄 Integration Pattern

**Temporal Level**: Orchestrates three main activities with durable execution, fault tolerance, and parallelization

**LangGraph Level**: Each Temporal activity contains its own StateGraph with nodes, edges, and conditional logic

```mermaid
graph TB
    subgraph "Temporal Workflow Orchestration"
        Start([Research Request]) --> Planning[Planning Activity]
        Planning --> Research[Research Activity]
        Research --> Report[Report Activity]
        Report --> End([Final Report])
    end

    subgraph "Planning Activity (Temporal)"
        Planning --> PG[Planning StateGraph]
        subgraph "LangGraph - Planning"
            PG --> Analyze[analyze_topic_node]
            Analyze --> CreatePlan[create_plan_node]
            CreatePlan --> PlanResult[Research Plan]
        end
    end

    subgraph "Research Activity (Temporal)"
        Research --> RG[Research StateGraph]
        subgraph "LangGraph - Research"
            RG --> GenQueries[generate_queries_node]
            GenQueries --> Conduct[conduct_searches_node]
            Conduct --> Synthesize[synthesize_content_node]
            Synthesize --> SectionResult[Section Content]
        end
        
        subgraph "Parallel Execution"
            RG --> RG1[Section 1 Graph]
            RG --> RG2[Section 2 Graph]
            RG --> RG3[Section N Graph]
            RG1 --> SR1[Section 1 Result]
            RG2 --> SR2[Section 2 Result]
            RG3 --> SR3[Section N Result]
        end
    end

    subgraph "Report Activity (Temporal)"
        Report --> ReportG[Report StateGraph]
        subgraph "LangGraph - Report"
            ReportG --> Summary[create_executive_summary_node]
            Summary --> Compile[compile_main_content_node]
            Compile --> Conclusion[create_conclusion_node]
            Conclusion --> Sources[compile_sources_node]
            Sources --> Finalize[finalize_report_node]
            Finalize --> FinalDoc[Final Report]
        end
    end

    classDef temporal fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef langgraph fill:#f3e5f5,stroke:#4a148c,stroke-width:2px
    classDef parallel fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px

    class Planning,Research,Report temporal
    class PG,RG,ReportG,Analyze,CreatePlan,GenQueries,Conduct,Synthesize,Summary,Compile,Conclusion,Sources,Finalize langgraph
    class RG1,RG2,RG3 parallel
```

## Usage

### 🏃 Quick Start

1. **Setup environment**:
   ```bash
   # Create virtual environment
   uv venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   
   # Install dependencies
   uv pip install -e .
   ```

2. **Configure environment** (create `.env` file):
   ```env
   OPENAI_API_KEY=your_key_here   
   # or
   ANTHROPIC_API_KEY=your_key_here
   TAVILY_API_KEY=your_key_here
   ```

3. **Start Temporal server**:
   ```bash
   # Start Temporal development server
   temporal server start-dev
   ```

4. **Start the worker** (in a separate terminal):
   ```bash
   python -m research_assistant_langgraph worker
   ```

5. **Run research** (in a separate terminal):
   ```bash
   python -m research_assistant_langgraph research "quantum computing applications"
   ```

6. **Inspect the web UI console**:
   ```
   Open http://localhost:8233 in your browser to monitor workflow execution,
   view activity logs, and inspect the research results
   ```

### 🎛️ Advanced Usage

```bash
# Custom sections and search depth
python -m research_assistant_langgraph research "climate change impacts" 4 2

# Using module components directly
python -m research_assistant_langgraph.worker
python -m research_assistant_langgraph.client "artificial intelligence ethics" 3 2
```