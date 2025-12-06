# Defra AI Agent for Environmental Incident Reporting

Welcome to the documentation for the Defra AI Agent prototype system.

## Overview

This system demonstrates how AI agents, knowledge graphs, and semantic search can enhance environmental incident reporting workflows. It's designed as a technical showcase and learning tool for public sector digital services.

## Key Features

✨ **AI-Powered Classification** - Automatically categorizes and prioritizes incidents  
🔍 **Semantic Search** - Finds relevant guidance and regulations  
🗺️ **Spatial Analysis** - Identifies nearby protected sites and water bodies  
📊 **Knowledge Graph** - Tracks relationships and historical patterns  
📧 **Automated Notifications** - Alerts teams and citizens via GOV.UK Notify  
📝 **Full Auditability** - Complete logging of all agent decisions

## Quick Links

- **[Getting Started Guide](guides/getting_started.md)** - Set up and run the system
- **[System Architecture](architecture/system_design.md)** - Technical deep dive
- **[API Documentation](http://localhost:8000/docs)** - Interactive API reference
- **[GitHub Repository](https://github.com/steve-dickinson/agentic-incident-reporting)** - Source code

## System Architecture

```mermaid
flowchart TD
    Form[Incident Form] --> API[FastAPI Service]
    API --> Agent[LangChain Agent]
    Agent --> Graph[Neo4j Graph]
    Agent --> Vector[PostgreSQL + pgvector]
    Agent --> Notify[GOV.UK Notify]
    Agent --> Logger[Audit Log]
```

## Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API** | FastAPI + Python 3.12 | RESTful API layer |
| **AI Agent** | LangChain + LangGraph | Decision orchestration |
| **Graph DB** | Neo4j 5.16 | Spatial & relational data |
| **Vector Store** | PostgreSQL + pgvector | Semantic search |
| **Notifications** | GOV.UK Notify | Email/SMS alerts |
| **LLM** | OpenAI GPT-4 Turbo | Classification & reasoning |

## Use Cases

### 1. Water Pollution Incident

A citizen reports oil in a river:

1. **Intake**: System receives structured form data
2. **Classification**: AI identifies as water pollution, high priority
3. **Context**: Finds nearby protected sites and relevant regulations
4. **Decision**: Determines immediate response required
5. **Action**: Alerts Environment Agency duty officer, logs to knowledge graph

### 2. Illegal Waste Dumping

Fly-tipping reported near protected woodland:

1. **Classification**: Categorized as illegal waste dumping
2. **Spatial Query**: Identifies Site of Special Scientific Interest (SSSI) nearby
3. **Priority Escalation**: Elevated to high priority due to protected site
4. **Notification**: Alerts both Environment Agency and Natural England
5. **Evidence Logging**: Records for potential prosecution

### 3. Air Quality Complaint

Industrial emissions affecting residents:

1. **Pattern Analysis**: Checks for similar recent incidents
2. **Permit Check**: Queries if facility has air quality permits
3. **Threshold Assessment**: Compares to regulatory limits
4. **Action**: Schedules inspection and issues warning letter

## Project Status

**Current Phase**: Phase 3 Complete - Agent MVP Operational  
**Next Phase**: Neo4j Graph Integration (Phase 4)  
**Target**: Q1 2026 for full demonstration

### Completed ✅

- [x] Docker infrastructure setup with Neo4j, PostgreSQL, FastAPI
- [x] Python 3.12 environment with modern type hints
- [x] FastAPI application with health and incident submission endpoints
- [x] Synthetic data generator (50+ test incidents)
- [x] Guidance documents and legislation reference
- [x] LangChain agent with LangGraph workflow orchestration
- [x] Intelligent incident classification with severity detection (P1-P4 priorities)
- [x] Context-aware action recommendations
- [x] Neo4j graph database with 10 UK protected sites and 8 water bodies
- [x] Spatial query tools (nearby sites within 5km, water bodies within 10km)
- [x] Historical incident pattern detection (similar incidents within 25km)
- [x] pgvector semantic search over 14 guidance document chunks
- [x] Automated retrieval of relevant regulations and procedures
- [x] GOV.UK Notify integration (email notifications)
- [x] Comprehensive documentation and GitHub Pages

### In Progress 🚧

- [ ] Comprehensive automated test suite
- [ ] CI/CD pipeline with GitHub Actions

### Planned 📅

- [ ] Advanced spatial queries
- [ ] Historical pattern analysis
- [ ] Multi-modal input (images, voice)
- [ ] Real-time dashboard
- [ ] Production deployment guide

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Python 3.12+
- OpenAI API key
- uv (recommended for Python package management)

### Quick Start

```bash
# Clone repository
git clone https://github.com/steve-dickinson/agentic-incident-reporting.git
cd agentic-incident-reporting

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start services
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

**[Full installation guide →](guides/getting_started.md)**

## Example API Usage

```python
import requests

incident = {
    "incident_type": "water_pollution",
    "location": "River Thames, Reading",
    "latitude": 51.4543,
    "longitude": -0.9781,
    "description": "Oil spill observed in river",
    "reporter_email": "citizen@example.com",
    "urgency": "high"
}

response = requests.post(
    "http://localhost:8000/api/v1/incidents/submit",
    json=incident
)

print(response.json())
```

## Contributing

This is a prototype/showcase project. Contributions for educational purposes are welcome!

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - See [LICENSE](https://github.com/steve-dickinson/agentic-incident-reporting/blob/main/LICENSE) on GitHub for details

⚠️ **Note**: This is a prototype using synthetic data. Not for production use without proper security, privacy, and compliance review.
