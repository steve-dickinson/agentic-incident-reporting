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
- **[Dashboard Guide](dashboard-guide.md)** - Monitor incidents in real-time
- **[Demo Walkthrough](examples/demo_walkthrough.md)** - Example scenarios and testing
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
| **Dashboard** | Streamlit | Real-time monitoring |
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

## Features

### 🤖 AI-Powered Intelligence

- **Smart Classification**: Automatic incident categorization with P1-P4 priority levels
- **Context-Aware Actions**: Generates 8-11 specific actions tailored to each incident type
- **Pattern Recognition**: Identifies similar historical incidents within 25km radius
- **Reasoning Transparency**: Full audit trail of all AI decisions

### 🗺️ Spatial Analysis

- **Protected Sites**: Queries 10 UK SSSIs, SACs, NNRs, and Ramsar sites
- **Water Bodies**: Identifies nearby rivers, lakes, estuaries, and coastal waters
- **Proximity Detection**: Searches within configurable radius (5km for sites, 10km for water)
- **Neo4j Integration**: Graph-based spatial relationships and queries

### 📚 Knowledge Base

- **Semantic Search**: pgvector-powered search over 14 guidance document chunks
- **Regulatory Guidance**: Automated retrieval of relevant legislation and procedures
- **Incident Response**: Best practices for water pollution, air quality, waste dumping
- **OpenAI Embeddings**: High-quality text-embedding-3-small for similarity search

### 📊 Monitoring & Observability

**Real-time Streamlit Dashboard** at http://localhost:8502:

- **Metrics**: Total incidents, P1/P2/P3/P4 counts, completion rates, avg processing time
- **Charts**: Hourly trends, processing time graphs, priority distribution
- **Incident Table**: Searchable/filterable by priority, type, status, location
- **Execution Logs**: Step-by-step agent execution with timing and error details
- **Live Updates**: Configurable auto-refresh for real-time monitoring

**[View Dashboard Guide →](dashboard-guide.md)**

### 🧪 Testing & Quality

- **72 Tests**: Unit and integration tests across all components
- **57% Coverage**: Core logic well-tested with mocked external services
- **Demo Script**: `./demo_test.sh` with 5 realistic scenarios
- **Type Safety**: Modern Python 3.12+ type hints throughout

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

# Access dashboard
open http://localhost:8501

# Verify API
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
