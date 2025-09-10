# 🤖 Agent Flows & Communication

> **Detailed documentation of agent interactions, workflows, and communication patterns**

## 📋 Table of Contents

- [Agent Communication Overview](#agent-communication-overview)
- [Core Workflows](#core-workflows)
- [Agent Interaction Patterns](#agent-interaction-patterns)
- [Message Flow Diagrams](#message-flow-diagrams)
- [Error Handling & Recovery](#error-handling--recovery)
- [Performance Optimization](#performance-optimization)
- [Debugging & Monitoring](#debugging--monitoring)

## 🌐 Agent Communication Overview

RouteWise AI uses a **hierarchical agent architecture** where the **Team Lead Agent** orchestrates specialized agents through the **Model Context Protocol (MCP)**. Each agent operates independently while maintaining seamless communication through standardized message formats.

### Communication Principles

1. **🎯 Hierarchical Coordination**: Team Lead Agent manages all specialized agents
2. **📨 Asynchronous Messaging**: Non-blocking communication between agents
3. **🔄 Stateless Operations**: Each agent call is independent and stateless
4. **🛡️ Error Isolation**: Agent failures don't cascade to other agents
5. **📊 Observable Interactions**: All communications are logged and traceable

## 🔄 Core Workflows

### 1. Travel Planning Workflow

```mermaid
sequenceDiagram
    participant User
    participant Router
    participant Workflow
    participant TeamLead
    participant Search
    participant Miner
    participant Itinerary
    participant Budget
    participant Visa
    participant Checklist
    
    User->>Router: "Plan 5 days in Japan"
    Router->>Workflow: route_request(query, context)
    Workflow->>TeamLead: orchestrate_workflow(trip_params)
    
    Note over TeamLead: Extract trip parameters
    TeamLead->>TeamLead: parse_trip_requirements()
    
    par Parallel Search Phase
        TeamLead->>Search: search_destinations("Japan travel")
        TeamLead->>Search: search_activities("Tokyo attractions")
        TeamLead->>Search: search_logistics("Japan transportation")
    end
    
    Search-->>TeamLead: consolidated_search_results
    
    TeamLead->>Miner: extract_insights(search_results)
    Miner-->>TeamLead: reality_insights[]
    
    par Specialized Agent Phase
        TeamLead->>Itinerary: generate_itinerary(params, insights)
        TeamLead->>Budget: estimate_costs(params, insights)
        TeamLead->>Visa: check_requirements("Japan", user_country)
        TeamLead->>Checklist: generate_checklist(params, insights)
    end
    
    Itinerary-->>TeamLead: detailed_itinerary
    Budget-->>TeamLead: budget_breakdown
    Visa-->>TeamLead: visa_info
    Checklist-->>TeamLead: travel_checklist
    
    TeamLead->>TeamLead: assemble_final_response()
    TeamLead-->>Workflow: complete_response
    Workflow-->>Router: formatted_output
    Router-->>User: "Here's your Japan travel plan..."
```

### 2. Search-Only Workflow

```mermaid
sequenceDiagram
    participant User
    participant Router
    participant Workflow
    participant TeamLead
    participant Search
    participant Miner
    
    User->>Router: "What are the best ramen shops in Tokyo?"
    Router->>Workflow: route_request(query, context)
    
    Note over Workflow: Detect search-only intent
    Workflow->>TeamLead: search_only_mode(query)
    
    TeamLead->>Search: search_specific("Tokyo ramen shops")
    Search-->>TeamLead: search_results[]
    
    TeamLead->>Miner: extract_insights(results, focus="food")
    Miner-->>TeamLead: food_insights[]
    
    TeamLead->>TeamLead: format_search_response()
    TeamLead-->>Workflow: search_response
    Workflow-->>Router: formatted_output
    Router-->>User: "Here are the best ramen shops..."
```

### 3. Conversational Workflow

```mermaid
sequenceDiagram
    participant User
    participant Router
    participant Workflow
    participant ConvAgent
    participant Memory
    
    User->>Router: "Thanks! Can you modify the budget?"
    Router->>Workflow: route_request(query, context)
    
    Note over Workflow: Detect conversational intent
    Workflow->>Memory: get_conversation_context(session_id)
    Memory-->>Workflow: previous_context
    
    Workflow->>ConvAgent: handle_conversation(query, context)
    ConvAgent->>ConvAgent: analyze_modification_request()
    
    alt Budget Modification
        ConvAgent->>Workflow: trigger_budget_update(params)
        Workflow->>TeamLead: update_budget_only(params)
    else Clarification Needed
        ConvAgent-->>Workflow: clarification_response
    end
    
    Workflow-->>Router: response
    Router-->>User: "I've updated your budget..."
```

## 🤖 Agent Interaction Patterns

### Team Lead Agent Orchestration

```mermaid
graph TD
    A[Team Lead Agent] --> B{Determine Required Agents}
    B -->|Search Needed| C[Search Agent]
    B -->|Insights Needed| D[Reality Miner]
    B -->|Planning Needed| E[Itinerary Agent]
    B -->|Budget Needed| F[Budget Agent]
    B -->|Visa Check| G[Visa Agent]
    B -->|Checklist Needed| H[Checklist Agent]
    B -->|Flight Info| I[Flight Agent]
    
    C --> J[Consolidate Results]
    D --> J
    E --> J
    F --> J
    G --> J
    H --> J
    I --> J
    
    J --> K[Assemble Response]
    K --> L[Save Outputs]
    L --> M[Return to Workflow]
```

### Agent Dependency Chain

```mermaid
flowchart LR
    subgraph "Phase 1: Information Gathering"
        A[Search Agent] --> B[Reality Miner]
    end
    
    subgraph "Phase 2: Content Generation"
        B --> C[Itinerary Agent]
        B --> D[Budget Agent]
        B --> E[Visa Agent]
        B --> F[Checklist Agent]
        B --> G[Flight Agent]
    end
    
    subgraph "Phase 3: Assembly"
        C --> H[Team Lead]
        D --> H
        E --> H
        F --> H
        G --> H
    end
    
    H --> I[Final Response]
```

## 📨 Message Flow Diagrams

### MCP Message Structure

```mermaid
classDiagram
    class MCPRequest {
        +string method
        +dict params
        +string id
        +string jsonrpc
    }
    
    class MCPResponse {
        +dict result
        +dict error
        +string id
        +string jsonrpc
    }
    
    class AgentMessage {
        +string agent_id
        +string message_type
        +dict payload
        +datetime timestamp
    }
    
    MCPRequest --> AgentMessage
    MCPResponse --> AgentMessage
```

### Search Agent Message Flow

```mermaid
sequenceDiagram
    participant TL as Team Lead
    participant SA as Search Agent
    participant DDG as DuckDuckGo
    participant TAV as Tavily
    participant Cache as File Cache
    
    TL->>SA: search_request(query, params)
    
    SA->>Cache: check_cache(query_hash)
    alt Cache Hit
        Cache-->>SA: cached_results
    else Cache Miss
        par Multi-Provider Search
            SA->>DDG: search(query)
            SA->>TAV: search(query)
        end
        
        DDG-->>SA: ddg_results[]
        TAV-->>SA: tavily_results[]
        
        SA->>SA: merge_and_rank_results()
        SA->>Cache: store_results(query_hash, results)
    end
    
    SA-->>TL: SearchResult[]
```

### Reality Miner Message Flow

```mermaid
sequenceDiagram
    participant TL as Team Lead
    participant RM as Reality Miner
    participant Mistral as Mistral AI
    participant Cache as Insight Cache
    
    TL->>RM: extract_insights(content[], focus_areas[])
    
    RM->>Cache: check_insight_cache(content_hash)
    alt Cache Hit
        Cache-->>RM: cached_insights
    else Cache Miss
        loop For Each Content Chunk
            RM->>Mistral: analyze_content(chunk, prompt)
            Mistral-->>RM: raw_insights
        end
        
        RM->>RM: categorize_insights()
        RM->>RM: score_quality()
        RM->>Cache: store_insights(content_hash, insights)
    end
    
    RM-->>TL: Insight[]
```

### Itinerary Agent Message Flow

```mermaid
sequenceDiagram
    participant TL as Team Lead
    participant IA as Itinerary Agent
    participant Gemini as Google Gemini
    participant Memory as Trip Memory
    
    TL->>IA: generate_itinerary(params, insights, context)
    
    IA->>Memory: get_previous_itinerary(session_id)
    Memory-->>IA: previous_version
    
    IA->>IA: prepare_generation_prompt()
    IA->>Gemini: generate(prompt, context)
    Gemini-->>IA: raw_itinerary
    
    IA->>IA: structure_itinerary()
    IA->>IA: validate_logistics()
    IA->>Memory: save_itinerary(session_id, itinerary)
    
    IA-->>TL: structured_itinerary
```

## 🛡️ Error Handling & Recovery

### Error Propagation Strategy

```mermaid
flowchart TD
    A[Agent Error] --> B{Error Type}
    B -->|Timeout| C[Retry with Backoff]
    B -->|API Limit| D[Switch Provider]
    B -->|Invalid Response| E[Fallback Response]
    B -->|Network Error| F[Cache Fallback]
    
    C --> G{Retry Count}
    G -->|< 3| H[Retry Request]
    G -->|>= 3| I[Graceful Degradation]
    
    D --> J[Update Provider Status]
    E --> K[Log Error Details]
    F --> L[Serve Stale Data]
    
    H --> A
    I --> M[Partial Response]
    J --> N[Continue with Backup]
    K --> M
    L --> M
    
    M --> O[Return to Team Lead]
    N --> O
```

### Agent Failure Recovery

```python
# Example error handling in Team Lead Agent
async def handle_agent_failure(self, agent_name: str, error: Exception) -> dict:
    """Handle individual agent failures gracefully"""
    
    fallback_strategies = {
        "search_agent": self._fallback_search,
        "reality_miner": self._fallback_insights,
        "itinerary_agent": self._fallback_itinerary,
        "budget_agent": self._fallback_budget
    }
    
    if agent_name in fallback_strategies:
        logger.warning(f"Agent {agent_name} failed, using fallback")
        return await fallback_strategies[agent_name]()
    
    # If no fallback, continue without this agent's contribution
    logger.error(f"No fallback for {agent_name}, continuing without")
    return {"status": "skipped", "reason": str(error)}
```

### Circuit Breaker Pattern

```mermaid
stateDiagram-v2
    [*] --> Closed
    Closed --> Open : Failure Threshold Reached
    Open --> HalfOpen : Timeout Elapsed
    HalfOpen --> Closed : Success
    HalfOpen --> Open : Failure
    
    Closed : Normal Operation
    Open : Fail Fast
    HalfOpen : Test Recovery
```

## ⚡ Performance Optimization

### Parallel Agent Execution

```python
# Example parallel execution in Team Lead Agent
async def orchestrate_parallel_agents(self, params: dict) -> dict:
    """Execute multiple agents in parallel for better performance"""
    
    tasks = []
    
    # Phase 1: Information gathering (parallel)
    if self._needs_search(params):
        tasks.append(self.search_agent.search(params["query"]))
    
    # Wait for search results before proceeding
    search_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Phase 2: Content generation (parallel)
    content_tasks = []
    if self._needs_itinerary(params):
        content_tasks.append(self.itinerary_agent.generate(params, search_results))
    if self._needs_budget(params):
        content_tasks.append(self.budget_agent.estimate(params, search_results))
    if self._needs_visa(params):
        content_tasks.append(self.visa_agent.check(params))
    
    # Execute content generation in parallel
    content_results = await asyncio.gather(*content_tasks, return_exceptions=True)
    
    return self._assemble_results(search_results, content_results)
```

### Caching Strategy by Agent

| Agent | Cache Duration | Cache Key | Invalidation |
|-------|----------------|-----------|-------------|
| **Search Agent** | 24 hours | `query_hash + provider` | Manual/TTL |
| **Reality Miner** | 7 days | `content_hash + focus` | Manual/TTL |
| **Itinerary Agent** | Session | `params_hash + session` | Session end |
| **Budget Agent** | 12 hours | `destination + duration` | Manual/TTL |
| **Visa Agent** | 30 days | `country_pair` | Manual |
| **Checklist Agent** | 7 days | `trip_type + destination` | Manual/TTL |

### Request Batching

```mermaid
sequenceDiagram
    participant TL as Team Lead
    participant Batcher as Request Batcher
    participant SA as Search Agent
    
    TL->>Batcher: add_request("Tokyo hotels")
    TL->>Batcher: add_request("Tokyo restaurants")
    TL->>Batcher: add_request("Tokyo attractions")
    
    Note over Batcher: Wait for batch window (100ms)
    
    Batcher->>SA: batch_search(["hotels", "restaurants", "attractions"])
    SA-->>Batcher: batch_results[]
    
    Batcher->>TL: distribute_results()
```

## 🔍 Debugging & Monitoring

### Agent Communication Tracing

```python
# Example tracing decorator
def trace_agent_call(agent_name: str):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            trace_id = generate_trace_id()
            start_time = time.time()
            
            logger.info(f"[{trace_id}] Starting {agent_name}.{func.__name__}")
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"[{trace_id}] Completed {agent_name}.{func.__name__} in {duration:.2f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"[{trace_id}] Failed {agent_name}.{func.__name__} after {duration:.2f}s: {e}")
                raise
        return wrapper
    return decorator
```

### Performance Metrics

```mermaid
graph LR
    subgraph "Agent Metrics"
        A[Response Time]
        B[Success Rate]
        C[Cache Hit Rate]
        D[Error Rate]
    end
    
    subgraph "System Metrics"
        E[Memory Usage]
        F[CPU Usage]
        G[Network I/O]
        H[Disk I/O]
    end
    
    subgraph "Business Metrics"
        I[User Satisfaction]
        J[Query Completion Rate]
        K[Feature Usage]
        L[Session Duration]
    end
    
    A --> M[Monitoring Dashboard]
    B --> M
    C --> M
    D --> M
    E --> M
    F --> M
    G --> M
    H --> M
    I --> M
    J --> M
    K --> M
    L --> M
```

### Debug Flow Visualization

```mermaid
journey
    title Agent Communication Debug Flow
    section Request Processing
      User Query: 5: User
      Route Request: 4: Router
      Detect Intent: 3: Workflow
      Start Orchestration: 4: TeamLead
    section Agent Execution
      Search Web: 3: SearchAgent
      Mine Insights: 4: RealityMiner
      Generate Itinerary: 5: ItineraryAgent
      Calculate Budget: 4: BudgetAgent
    section Response Assembly
      Consolidate Results: 4: TeamLead
      Format Response: 5: TeamLead
      Return to User: 5: Router
```

## 🚀 Advanced Patterns

### Event-Driven Communication (Future)

```mermaid
sequenceDiagram
    participant EventBus
    participant TeamLead
    participant SearchAgent
    participant MinerAgent
    
    TeamLead->>EventBus: publish("search.requested", params)
    EventBus->>SearchAgent: notify("search.requested")
    
    SearchAgent->>EventBus: publish("search.completed", results)
    EventBus->>MinerAgent: notify("search.completed")
    EventBus->>TeamLead: notify("search.completed")
    
    MinerAgent->>EventBus: publish("insights.extracted", insights)
    EventBus->>TeamLead: notify("insights.extracted")
```

### Agent Health Monitoring

```python
# Example health check system
class AgentHealthMonitor:
    def __init__(self):
        self.agent_status = {}
        self.health_checks = {
            "search_agent": self._check_search_health,
            "reality_miner": self._check_miner_health,
            "itinerary_agent": self._check_itinerary_health
        }
    
    async def monitor_agents(self):
        """Continuously monitor agent health"""
        while True:
            for agent_name, check_func in self.health_checks.items():
                try:
                    health = await check_func()
                    self.agent_status[agent_name] = health
                except Exception as e:
                    self.agent_status[agent_name] = {"status": "unhealthy", "error": str(e)}
            
            await asyncio.sleep(30)  # Check every 30 seconds
```

---

<div align="center">
  <strong>Orchestrated intelligence through seamless agent communication</strong>
  <br>
  <sub>Building the future of collaborative AI systems</sub>
</div>

## ⏱️ Time-Budgeted Execution

The Team Lead Agent now enforces a time budget per request and a fast mode for development to keep responses snappy:

- Fast Mode (FAST_MODE=1):
  - Caps initial search queries to the top 3-4 based on salience
  - Skips nested refinement search passes
  - Trims mined documents before insight extraction
  - Limits the number of insights passed downstream
- Planner Time Budget (PLANNER_TIME_BUDGET, default 90s, clamped 45–100s):
  - Remaining-time checks gate deeper work
  - Quick inline itinerary fallback when remaining time is low
  - Specialized agents (flights, visa, checklist, budget) only run if enough time remains
  - Saving artifacts is skipped if time is nearly exhausted

High-level flow under time pressure:

```mermaid
sequenceDiagram
    participant TL as Team Lead
    participant Search as Search Agent
    participant Miner as Reality Miner
    participant Plan as Itinerary Agent

    TL->>TL: compute remaining()
    alt FAST_MODE
      TL->>Search: limited queries (top 3-4)
    else Normal
      TL->>Search: full queries (+ optional refinement if time permits)
    end

    Search-->>TL: results
    TL->>Miner: extract insights (trimmed when under pressure)
    Miner-->>TL: insights

    alt low remaining time
      TL->>TL: quick inline itinerary fallback
    else
      TL->>Plan: generate detailed itinerary
    end

    TL->>TL: optionally run flights/visa/checklist/budget if remaining() >= threshold
    TL->>TL: save artifacts only if remaining() >= threshold
```

Notes:
- Frontend dev route sets FAST_MODE=1 by default for responsiveness.
- Time thresholds are conservative to keep requests within the global budget.