# Defra AI Agent Prototype for Environmental Incident Reporting

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> **A technical showcase demonstrating how AI agents, knowledge graphs, and semantic search can enhance environmental incident reporting workflows.**

## 🎯 Overview

This project demonstrates an end-to-end AI-powered system for processing environmental incident reports. It combines:

- **LangChain/LangGraph agents** for intelligent decision-making
- **Neo4j knowledge graph** for spatial and regulatory context
- **PostgreSQL + pgvector** for semantic document search
- **GOV.UK Notify** for automated notifications
- **FastAPI** for a modern, async API layer

The system accepts structured form submissions, classifies incidents, queries relevant context, and takes automated actions—all while maintaining full auditability.

## 🏗️ Architecture

```mermaid
flowchart TD
    Form[Structured Incident Form] --> API[Agent API Service]
    API --> Agent[LangChain Agent + LangGraph]
    Agent --> Graph[Neo4j Knowledge Graph]
    Agent --> Vector[pgvector DB]
    Agent --> Notify[GOV.UK Notify API]
    Agent --> Logger[Audit Log / Output]
```

### Technology Stack

| Component | Technology | Purpose |
|-----------|-----------|---------|
| **API Layer** | FastAPI | Async REST API for incident submission |
| **AI Orchestration** | LangChain + LangGraph | Agent reasoning and workflow control |
| **Knowledge Graph** | Neo4j 5.16 | Spatial relationships and protected sites |
| **Vector Search** | PostgreSQL + pgvector | Semantic search over guidance documents |
| **Notifications** | GOV.UK Notify | Email/SMS alerts to teams and citizens |
| **Embeddings** | OpenAI text-embedding-3-small | Document vectorization |
| **LLM** | OpenAI GPT-4 Turbo | Classification and reasoning |

## 📋 Prerequisites

- **Docker & Docker Compose** (recommended) or
- **Python 3.12+** for local development
- **uv** for fast package management (recommended)
- **OpenAI API key** (for embeddings and LLM)
- **GOV.UK Notify API key** (optional for notifications)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/steve-dickinson/agentic-incident-reporting.git
cd agentic-incident-reporting
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your API keys
```

**Required environment variables:**
- `OPENAI_API_KEY`: Your OpenAI API key (required for embeddings and LLM)
- `NEO4J_PASSWORD`: Password for Neo4j database (choose a strong password)
- `POSTGRES_PASSWORD`: Password for PostgreSQL (choose a strong password)
- `NOTIFY_API_KEY`: GOV.UK Notify API key (optional for testing - can use test mode)
- `SECRET_KEY`: Random secret for security (generate with `openssl rand -hex 32`)

**Example .env setup:**
```bash
OPENAI_API_KEY=sk-your-key-here
NEO4J_PASSWORD=your_secure_password
POSTGRES_PASSWORD=another_secure_password
NOTIFY_API_KEY=your_notify_key-or-leave-empty-for-test-mode
SECRET_KEY=$(openssl rand -hex 32)
```

### 3. Start with Docker Compose

```bash
docker-compose up -d
```

This will start:
- **API service** on http://localhost:8000
- **Neo4j browser** on http://localhost:7475
- **PostgreSQL** with pgvector on port 5433

### 4. Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# View API documentation
open http://localhost:8000/docs
```

## 💻 Local Development Setup

If you prefer to run without Docker:

```bash
# Create virtual environment with uv (recommended - much faster!)
uv venv --python 3.12
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e ".[dev,docs]"

# Generate synthetic test data
python -m app.tools.synthetic_data

# Start PostgreSQL and Neo4j separately, then run the API
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Alternative: Traditional pip/venv
```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 📊 Project Status

### ✅ Phase 1: Setup & Scaffolding (COMPLETED)
- [x] Docker Compose configuration (Neo4j, PostgreSQL, API)
- [x] Environment templates and configuration
- [x] FastAPI application structure with health endpoints
- [x] Database initialization scripts (pgvector enabled)
- [x] Python 3.12+ environment with uv
- [x] Modern type hints (PEP 604 syntax)

### ✅ Phase 2: Synthetic Data Generation (COMPLETED)
- [x] Incident sample generator with UK locations
- [x] 50+ test incidents across all incident types
- [x] Guidance documents (incident response, legislation)
- [x] Document embedding loader with pgvector
- [x] Semantic search implementation

### ✅ Phase 3: LangChain Agent MVP (COMPLETED)
- [x] LangGraph workflow orchestration (classify → spatial → notify → finalize)
- [x] Intelligent incident classification with severity detection
- [x] Priority assignment (P1-P4) based on incident type and keywords
- [x] Context-aware action recommendations (8-11 actions per incident)
- [x] Spatial queries for nearby protected sites and water bodies
- [x] GOV.UK Notify integration (email notifications)
- [x] Tested with multiple incident scenarios (critical, high, medium, low)

### ✅ Phase 4: Neo4j Graph Integration (COMPLETED)
- [x] Graph schema for protected sites (SSSI, SAC, NNR, Ramsar)
- [x] Water bodies (rivers, lakes, estuaries, coastal waters)
- [x] Spatial query tools (nearby sites, water bodies, historical incidents)
- [x] Loaded 10 UK protected sites and 8 major water bodies
- [x] Integrated spatial context into agent workflow
- [x] Tested spatial queries with real coordinates

### 📅 Upcoming Phases
- **Phase 5**: pgvector Integration (semantic search over guidance documents)
- **Phase 6**: Comprehensive Test Suite (unit, integration, end-to-end)
- **Phase 7**: ✅ Documentation & GitHub Pages (COMPLETED)
- **Phase 8**: Demo Walkthrough & Video Tutorial

## 🧪 Testing

```bash
# Activate virtual environment first
source .venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term-missing

# Run specific test suite
pytest tests/unit/ -v
pytest tests/integration/ -v

# Generate test data
python -m app.tools.synthetic_data
```

**Note**: Test suite is currently being developed. Some tests may be placeholder implementations.

## 📚 Documentation

- **[Getting Started Guide](docs/guides/getting_started.md)** - Complete setup walkthrough
- **[System Architecture](docs/architecture/system_design.md)** - Technical deep dive
- **[API Reference](http://localhost:8000/docs)** - Interactive Swagger UI docs
- **[Progress Log](docs/progress.md)** - Development status and decisions
- **[GitHub Pages](https://steve-dickinson.github.io/agentic-incident-reporting/)** - Full documentation site (coming soon)

### Build Documentation Locally

```bash
# Install docs dependencies
uv pip install -e ".[docs]"

# Serve documentation locally
mkdocs serve

# Open http://localhost:8001 in browser

# Build static site
mkdocs build
```

## 🔧 Development Workflow

1. **Create feature branch**: `git checkout -b feature/your-feature`
2. **Activate environment**: `source .venv/bin/activate`
3. **Make changes** with tests
4. **Format code**: `black app/ tests/`
5. **Check linting**: `flake8 app/ tests/`
6. **Type check**: `mypy app/`
7. **Run tests**: `pytest --cov=app`
8. **Commit and push**: Follow [conventional commits](https://www.conventionalcommits.org/)
9. **Create pull request**

### Code Quality Tools

```bash
# Format code
black app/ tests/

# Lint
flake8 app/ --max-line-length=100

# Type checking
mypy app/ --ignore-missing-imports

# Run all quality checks
black app/ tests/ && flake8 app/ && mypy app/ && pytest
```

## 📖 API Usage Example

```python
import requests

incident = {
    "incident_type": "water_pollution",
    "location": "River Thames near Reading",
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

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

**⚠️ Note**: This is a prototype system using synthetic data. Do not use for production incident reporting without proper security, privacy, and compliance reviews.