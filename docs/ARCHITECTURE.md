# 🏗️ RouteWise AI Architecture

> **Comprehensive guide to the system design, components, and data flow**

## 📋 Table of Contents

- [System Overview](#system-overview)
- [Core Components](#core-components)
- [Agent Architecture](#agent-architecture)
- [Data Flow](#data-flow)
- [MCP Protocol Integration](#mcp-protocol-integration)
- [Memory Management](#memory-management)
- [Search & Reality Mining](#search--reality-mining)
- [Performance Considerations](#performance-considerations)

## 🌐 System Overview

RouteWise AI is built on a **multi-agent architecture** using the **Model Context Protocol (MCP)** for seamless communication between specialized agents. The system prioritizes **reality-first intelligence** by mining real user experiences and practical insights from travel communities.

### Key Architectural Principles

1. **🔄 Agent Orchestration**: Specialized agents handle specific domains (search, reality mining, itinerary planning)
2. **🧠 Context Awareness**: Persistent memory and conversation history across sessions
3. **⚡ Intelligent Routing**: Dynamic routing between chat, search, and planning modes
4. **🎯 Reality-First**: Prioritizes practical, first-hand travel experiences over generic content
5. **🔌 Extensible Design**: Modular architecture for easy addition of new agents and capabilities

## 🏛️ Core Components

```mermaid
graph TB
    subgraph "Client Layer"
        WebUI[🌐 Next.js Web UI]
        CLI[💻 CLI Client]
        TG[📱 Telegram Bot]
        API[🔌 REST API]
    end
    
    subgraph "Orchestration Layer"
        Router[🎯 MCP Router]
        Workflow[⚡ MCP Workflow]
        Memory[🧠 Memory Manager]
        ConvAgent[💬 Conversational Agent]
    end
    
    subgraph "Agent Layer"
        TeamLead[👨‍💼 Team Lead Agent]
        Search[🔍 Search Agent]
        Miner[⛏️ Reality Miner Agent]
        Itinerary[📋 Itinerary Agent]
        Budget[💰 Budget Agent]
        Flight[✈️ Flight Agent]
        Visa[📄 Visa Agent]
        Checklist[✅ Checklist Agent]
    end
    
    subgraph "External Services"
        Mistral[🧠 Mistral AI]
        Gemini[💎 Google Gemini]
        DDG[🦆 DuckDuckGo]
        Tavily[🔎 Tavily API]
    end
    
    subgraph "Storage Layer"
        SQLite[(🗄️ SQLite DB)]
        Cache[📦 File Cache]
        Files[📁 Output Files]
    end
    
    WebUI --> Router
    CLI --> Router
    TG --> Router
    API --> Router
    
    Router --> Workflow
    Workflow --> Memory
    Workflow --> ConvAgent
    Workflow --> TeamLead
    
    TeamLead --> Search
    TeamLead --> Miner
    TeamLead --> Itinerary
    TeamLead --> Budget
    TeamLead --> Flight
    TeamLead --> Visa
    TeamLead --> Checklist
    
    Search --> DDG
    Search --> Tavily
    Miner --> Mistral
    Itinerary --> Gemini
    Budget --> Mistral
    Flight --> Mistral
    Visa --> Mistral
    Checklist --> Mistral
    
    Memory --> SQLite
    Search --> Cache
    TeamLead --> Files
```

### Component Responsibilities

| Component | Purpose | Technology |
|-----------|---------|------------|
| **MCP Router** | Routes requests to appropriate workflow | Python |
| **MCP Workflow** | Orchestrates agent interactions | Python + MCP |
| **Memory Manager** | Handles conversation history and context | SQLite |
| **Team Lead Agent** | Coordinates specialized agents | Python + MCP |
| **Search Agent** | Web search and content extraction | DuckDuckGo + Tavily |
| **Reality Miner** | Extracts practical insights from content | Mistral AI |
| **Itinerary Agent** | Generates detailed travel plans | Google Gemini |
| **Budget Agent** | Estimates costs and budget breakdowns | Mistral AI |

## 🤖 Agent Architecture

### Agent Communication Pattern

```mermaid
sequenceDiagram
    participant User
    participant Router
    participant Workflow
    participant TeamLead
    participant Search
    participant Miner
    participant Itinerary
    
    User->>Router: "Plan 3 days in Tokyo"
    Router->>Workflow: route_request()
    Workflow->>TeamLead: orchestrate_workflow()
    
    TeamLead->>Search: search_travel_info()
    Search-->>TeamLead: search_results[]
    
    TeamLead->>Miner: extract_insights()
    Miner-->>TeamLead: reality_insights[]
    
    TeamLead->>Itinerary: synthesize_plan()
    Itinerary-->>TeamLead: detailed_itinerary
    
    TeamLead-->>Workflow: final_response
    Workflow-->>Router: formatted_output
    Router-->>User: "Here's your Tokyo plan..."
```

### Agent Specialization

#### 🔍 Search Agent
- **Purpose**: Web search and content extraction
- **Capabilities**:
  - Multi-provider search (DuckDuckGo, Tavily)
  - Content extraction with Trafilatura
  - Reality-first result ranking
  - Intelligent caching

#### ⛏️ Reality Miner Agent
- **Purpose**: Extract practical insights from web content
- **Capabilities**:
  - Scam and warning detection
  - Cost and timing insights
  - Local tips and hacks
  - Safety recommendations

#### 📋 Itinerary Agent
- **Purpose**: Generate detailed travel plans
- **Capabilities**:
  - Day-by-day planning
  - Activity clustering
  - Time optimization
  - Preference adaptation

#### 💰 Budget Agent
- **Purpose**: Cost estimation and budget planning
- **Capabilities**:
  - Regional cost analysis
  - Budget breakdown by category
  - Cost-saving recommendations
  - Currency conversion

## 🔄 Data Flow

### Request Processing Flow

```mermaid
flowchart TD
    A[User Input] --> B{Intent Detection}
    B -->|Chat| C[Conversational Response]
    B -->|Search| D[Search-Only Mode]
    B -->|Planning| E[Full Orchestration]
    
    E --> F[Extract Trip Parameters]
    F --> G[Generate Search Queries]
    G --> H[Execute Multi-Agent Search]
    H --> I[Mine Reality Insights]
    I --> J[Synthesize Itinerary]
    J --> K[Assemble Final Response]
    
    K --> L{Save Results?}
    L -->|Yes| M[Save to Files]
    L -->|No| N[Return Response]
    M --> N
    
    C --> N
    D --> N
    N --> O[Update Memory]
    O --> P[Return to User]
```

### Memory and Context Flow

```mermaid
graph LR
    subgraph "Session Context"
        A[User Message] --> B[Trip Context]
        B --> C[Conversation History]
        C --> D[Extracted Requirements]
    end
    
    subgraph "Processing Context"
        E[Search Results] --> F[Reality Insights]
        F --> G[Generated Content]
    end
    
    subgraph "Persistent Storage"
        H[(SQLite Database)]
        I[File Cache]
        J[Output Files]
    end
    
    B --> H
    C --> H
    E --> I
    G --> J
```

## 🔌 MCP Protocol Integration

### MCP Server Architecture

Each agent runs as an independent MCP server, enabling:

- **🔄 Standardized Communication**: Consistent message format across agents
- **🔌 Hot-Swappable Agents**: Add/remove agents without system restart
- **📊 Resource Management**: Independent scaling and monitoring
- **🛡️ Error Isolation**: Agent failures don't cascade

```python
# Example MCP Server Structure
class SearchMCPServer:
    def __init__(self, settings: Settings):
        self.tools = SearchTools(settings)
        
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        if request.method == "search":
            results = self.tools.search(request.params["query"])
            return MCPResponse(content=results)
```

### Agent Registration

```mermaid
graph TB
    subgraph "MCP Registry"
        Registry[Agent Registry]
    end
    
    subgraph "Agent Servers"
        Search[Search Server]
        Miner[Miner Server]
        Itinerary[Itinerary Server]
        Budget[Budget Server]
    end
    
    Search --> Registry
    Miner --> Registry
    Itinerary --> Registry
    Budget --> Registry
    
    Registry --> TeamLead[Team Lead Agent]
```

## 🧠 Memory Management

### Conversation Memory

```mermaid
erDiagram
    CONVERSATION {
        string session_id PK
        datetime created_at
        datetime updated_at
        json metadata
    }
    
    MESSAGE {
        string id PK
        string session_id FK
        string role
        string content
        string message_type
        datetime timestamp
        json metadata
    }
    
    TRIP_CONTEXT {
        string session_id PK
        string query
        json destinations
        int duration_days
        string budget_range
        json preferences
        text current_itinerary
        json refinements
    }
    
    CONVERSATION ||--o{ MESSAGE : contains
    CONVERSATION ||--|| TRIP_CONTEXT : has
```

### Context Retrieval Strategy

1. **Recent Context**: Last 5 messages for immediate context
2. **Trip Context**: Current trip parameters and preferences
3. **Refinement History**: Previous modifications and feedback
4. **Insight Cache**: Relevant reality insights for the destination

## 🔍 Search & Reality Mining

### Search Strategy

```mermaid
flowchart TD
    A[User Query] --> B[Generate Search Queries]
    B --> C{Search Provider}
    C -->|Primary| D[DuckDuckGo Search]
    C -->|Enhanced| E[Tavily Search]
    C -->|Hybrid| F[Combined Results]
    
    D --> G[Extract Content]
    E --> G
    F --> G
    
    G --> H[Reality-First Ranking]
    H --> I[Cache Results]
    I --> J[Return to Agent]
```

### Reality Mining Pipeline

```mermaid
flowchart LR
    A[Raw Content] --> B[Content Preprocessing]
    B --> C[Mistral AI Analysis]
    C --> D[Insight Extraction]
    D --> E[Categorization]
    E --> F[Quality Scoring]
    F --> G[Final Insights]
    
    subgraph "Insight Categories"
        H[Scams & Warnings]
        I[Cost Insights]
        J[Timing Tips]
        K[Local Hacks]
        L[Safety Info]
    end
    
    G --> H
    G --> I
    G --> J
    G --> K
    G --> L
```

## ⚡ Performance Considerations

### Caching Strategy

- **Search Results**: 24-hour cache for popular queries
- **Reality Insights**: 7-day cache for destination-specific insights
- **Generated Content**: Session-based cache for refinements

### Optimization Techniques

1. **Parallel Agent Execution**: Multiple agents run concurrently
2. **Intelligent Query Batching**: Combine related searches
3. **Content Deduplication**: Remove duplicate search results
4. **Lazy Loading**: Load additional content only when needed

### Scalability Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Response Time | < 5s | ~3-8s |
| Concurrent Users | 100+ | 50+ |
| Cache Hit Rate | 80% | ~70% |
| Memory Usage | < 1GB | ~500MB |

## 🔧 Configuration Management

### Environment-Based Configuration

```python
@dataclass
class Settings:
    # API Keys
    mistral_api_key: str
    gemini_api_key: str
    tavily_api_key: Optional[str] = None
    
    # Search Configuration
    search_provider: Literal["duckduckgo", "tavily", "hybrid"] = "hybrid"
    max_results: int = 10
    
    # Performance
    request_timeout: int = 20
    cache_ttl: int = 86400  # 24 hours
    
    # Storage
    output_dir: str = "src/data/examples"
    cache_dir: str = "src/data/cache"
    db_path: str = "src/data/memory.db"
```

### Agent Configuration

Each agent can be configured independently:

```yaml
# config/agents.yaml
search_agent:
  providers: ["duckduckgo", "tavily"]
  max_results: 15
  content_extraction: true
  
reality_miner:
  model: "mistral-large"
  insight_types: ["scam", "warning", "hack", "cost"]
  confidence_threshold: 0.7
  
itinerary_agent:
  model: "gemini-pro"
  max_days: 30
  activity_clustering: true
```

## 🚀 Future Architecture Enhancements

### Planned Improvements

1. **🔄 Event-Driven Architecture**: Move to event-based communication
2. **📊 Real-Time Analytics**: Live performance monitoring
3. **🤖 ML-Based Routing**: Intelligent request routing based on patterns
4. **🌐 Distributed Agents**: Scale agents across multiple servers
5. **🔒 Enhanced Security**: OAuth integration and rate limiting

### Technology Roadmap

```mermaid
timeline
    title Architecture Evolution
    
    Q1 2024 : MCP Integration
           : Multi-Agent Foundation
           : Basic Memory Management
    
    Q2 2024 : Reality Mining
           : Advanced Search
           : Web Interface
    
    Q3 2024 : Event-Driven Architecture
           : Real-Time Analytics
           : Mobile API
    
    Q4 2024 : Distributed Agents
           : ML-Based Routing
           : Advanced Caching
```

---

<div align="center">
  <strong>Architecture designed for scale, built for intelligence</strong>
  <br>
  <sub>Enabling the next generation of travel planning</sub>
</div>