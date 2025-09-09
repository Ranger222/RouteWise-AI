# 🌍 RouteWise AI

> **Intelligent Travel Planning with Reality-First Insights**

RouteWise AI is an advanced travel planning system that leverages multi-agent orchestration and real-time web intelligence to provide practical, reality-based travel recommendations. Unlike traditional travel planners, RouteWise prioritizes first-hand experiences, local insights, and practical warnings to help travelers make informed decisions.

## ✨ Key Features

- **🔍 Reality-First Intelligence**: Mines real user experiences, scams, and practical challenges from forums and travel communities
- **🤖 Multi-Agent Architecture**: Specialized agents for search, reality mining, itinerary planning, budget estimation, and more
- **💬 Conversational Interface**: Natural language interaction with memory and context awareness
- **🌐 Multiple Interfaces**: CLI, Web UI, and extensible client architecture
- **📊 Smart Orchestration**: Intelligent routing between chat, search, and planning modes
- **🔄 MCP Protocol**: Built on Model Context Protocol for seamless agent communication

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 18+ (for web interface)
- API Keys for:
  - [Mistral AI](https://mistral.ai/) (required)
  - [Google Gemini](https://ai.google.dev/) (required)
  - [Tavily Search](https://tavily.com/) (optional, for enhanced search)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/routewise-ai.git
   cd RouteWise
   ```

2. **Set up Python environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   cd routewise-ai
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

4. **Test the CLI**
   ```bash
   python -m src.main "Delhi to Jaipur, 3 days, budget travel"
   ```

5. **Start the web interface**
   ```bash
   cd web
   npm install
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) in your browser.

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [🏗️ Architecture](./docs/ARCHITECTURE.md) | System design, components, and data flow |
| [🤖 Agent Communication](./docs/AGENT_FLOWS.md) | Multi-agent orchestration and workflows |
| [🔌 API Reference](./docs/API.md) | REST endpoints and integration guide |
| [🚀 Deployment](./docs/DEPLOYMENT.md) | Production setup and configuration |

## 🏗️ System Architecture

```mermaid
graph TB
    User[👤 User] --> WebUI[🌐 Web Interface]
    User --> CLI[💻 CLI Client]
    User --> TG[📱 Telegram Bot]
    
    WebUI --> Router[🎯 MCP Router]
    CLI --> Router
    TG --> Router
    
    Router --> Workflow[⚡ MCP Workflow]
    Workflow --> Memory[🧠 Memory Manager]
    Workflow --> TeamLead[👨‍💼 Team Lead Agent]
    
    TeamLead --> Search[🔍 Search Agent]
    TeamLead --> Miner[⛏️ Reality Miner]
    TeamLead --> Itinerary[📋 Itinerary Agent]
    TeamLead --> Budget[💰 Budget Agent]
    TeamLead --> Flight[✈️ Flight Agent]
    TeamLead --> Visa[📄 Visa Agent]
    TeamLead --> Checklist[✅ Checklist Agent]
    
    Search --> DDG[🦆 DuckDuckGo]
    Search --> Tavily[🔎 Tavily API]
    Miner --> Mistral[🧠 Mistral AI]
    Itinerary --> Gemini[💎 Google Gemini]
```

## 🎯 Usage Examples

### Basic Travel Planning
```bash
# Simple itinerary request
python -m src.main "Tokyo for 5 days, first time visitor"

# Budget-focused planning
python -m src.main "Backpacking Southeast Asia, 3 weeks, $1000 budget"

# Reality-focused insights
python -m src.main "Goa nightlife safety tips and current scene"
```

### Interactive CLI
```bash
# Start interactive session
python -m src.clients.cli_client

# Commands available:
# plan <query>     - Create travel plan
# search <query>   - Search-only mode
# refine <details> - Refine current plan
# show             - Display current itinerary
# memory           - View conversation history
# help             - Show all commands
```

### Web Interface Features
- 💬 **Chat Interface**: Natural conversation with the AI
- 📱 **Responsive Design**: Works on desktop and mobile
- 🔄 **Real-time Updates**: Live response streaming
- 💾 **Session Memory**: Persistent conversation history
- 📋 **Export Options**: Save itineraries as PDF/Markdown

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|----------|
| `MISTRAL_API_KEY` | Mistral AI API key | ✅ | - |
| `GEMINI_API_KEY` | Google Gemini API key | ✅ | - |
| `TAVILY_API_KEY` | Tavily search API key | ❌ | - |
| `SEARCH_PROVIDER` | Search backend | ❌ | `hybrid` |
| `MAX_RESULTS` | Max search results | ❌ | `10` |
| `LOG_LEVEL` | Logging level | ❌ | `INFO` |
| `OUTPUT_DIR` | Output directory | ❌ | `src/data/examples` |
| `CACHE_DIR` | Cache directory | ❌ | `src/data/cache` |

### Search Providers
- **`duckduckgo`**: Free, privacy-focused search
- **`tavily`**: Enhanced search with better travel content
- **`hybrid`**: Combines both for optimal results

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](./docs/DEVELOPMENT.md) for details.

### Development Setup
```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Code formatting
black src/
flake8 src/
```

## 📊 Performance & Scaling

- **Response Time**: ~3-8 seconds for complex itineraries
- **Concurrent Users**: Supports 50+ simultaneous sessions
- **Cache Hit Rate**: ~70% for popular destinations
- **Memory Usage**: ~200MB base + 50MB per active session

## 🔒 Privacy & Security

- **No Personal Data Storage**: Only conversation context is retained
- **API Key Security**: Environment-based configuration
- **Content Filtering**: Safe search and content validation
- **Session Isolation**: Each user session is independent

## 📈 Roadmap

- [ ] **Real-time Pricing**: Live flight and hotel price integration
- [ ] **Mobile App**: Native iOS/Android applications
- [ ] **Offline Mode**: Cached recommendations for offline use
- [ ] **Group Planning**: Multi-user collaborative planning
- [ ] **Booking Integration**: Direct booking through travel partners
- [ ] **Voice Interface**: Voice-activated travel assistant

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Mistral AI** for powerful language understanding
- **Google Gemini** for creative itinerary generation
- **Tavily** for enhanced travel search capabilities
- **MCP Protocol** for seamless agent communication
- **Travel Community** for real-world insights and feedback

## 📞 Support

- 📧 **Email**: support@routewise.ai
- 💬 **Discord**: [Join our community](https://discord.gg/routewise)
- 🐛 **Issues**: [GitHub Issues](https://github.com/your-org/routewise-ai/issues)
- 📖 **Docs**: [Documentation Site](https://docs.routewise.ai)

---

<div align="center">
  <strong>Built with ❤️ for travelers, by travelers</strong>
  <br>
  <sub>Making travel planning intelligent, practical, and delightful</sub>
</div>