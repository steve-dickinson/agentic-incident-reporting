# Getting Started Guide

Welcome to the Defra AI Agent for Environmental Incident Reporting! This guide will walk you through setting up and running the system.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker & Docker Compose** (v20.10+ and v2.0+) - [Install Docker](https://docs.docker.com/get-docker/)
- **Python 3.12+** - [Install Python](https://www.python.org/downloads/)
- **uv** (recommended) - [Install uv](https://github.com/astral-sh/uv)
- **Git** - [Install Git](https://git-scm.com/downloads)

## Step 1: Clone the Repository

```bash
git clone https://github.com/steve-dickinson/agentic-incident-reporting.git
cd agentic-incident-reporting
```

## Step 2: Set Up Environment Variables

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` and configure the following **required** variables:

### Required Configuration

```bash
# OpenAI API Key (get from https://platform.openai.com/api-keys)
OPENAI_API_KEY=sk-your-actual-key-here

# Database Passwords (choose strong passwords)
NEO4J_PASSWORD=your_neo4j_password
POSTGRES_PASSWORD=your_postgres_password

# Application Secret (generate with command below)
SECRET_KEY=your_generated_secret_key
```

### Generate Secret Key

```bash
# On Linux/Mac
openssl rand -hex 32

# On Windows (PowerShell)
-join ((48..57) + (97..102) | Get-Random -Count 32 | % {[char]$_})
```

### Optional Configuration

```bash
# GOV.UK Notify (optional - can test without)
NOTIFY_API_KEY=your_notify_key
NOTIFY_TEST_MODE=true  # Set to false in production

# If you don't have a Notify key, the system will run in test mode
```

## Step 3: Choose Your Setup Method

You have two options: **Docker** (recommended for quick start) or **Local Development**.

### Option A: Docker Setup (Recommended)

#### Start All Services

```bash
docker-compose up -d
```

This will start:
- **API Service** on `http://localhost:8000`
- **Neo4j Browser** on `http://localhost:7474`
- **PostgreSQL** on `localhost:5432`

#### Verify Services

```bash
# Check service status
docker-compose ps

# View logs
docker-compose logs -f api

# Test API health
curl http://localhost:8000/health
```

#### Access Neo4j Browser

1. Open `http://localhost:7474` in your browser
2. Connect with:
   - URI: `bolt://localhost:7687`
   - Username: `neo4j`
   - Password: (your `NEO4J_PASSWORD` from `.env`)

### Option B: Local Development Setup

#### 1. Create Virtual Environment

Using **uv** (recommended - fastest):
```bash
uv venv --python 3.12
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev,docs]"
```

Using **pip** (traditional):
```bash
python3.12 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

#### 2. Start Database Services

You'll need to run PostgreSQL and Neo4j separately. You can:

**Option 1**: Use Docker for databases only
```bash
docker-compose up -d postgres neo4j
```

**Option 2**: Install locally
- PostgreSQL 16+ with pgvector extension
- Neo4j 5.16+

#### 3. Run the API

```bash
uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

## Step 4: Generate Test Data

```bash
# Activate your virtual environment first
source .venv/bin/activate  # or venv/bin/activate

# Generate synthetic incidents
python -m app.tools.synthetic_data
```

This creates:
- `data/synthetic/test_incidents.json` - 50 test incidents
- `data/synthetic/examples/` - 5 example incidents

## Step 5: Load Guidance Documents (Optional)

If you have an OpenAI API key configured:

```bash
python -m app.tools.embeddings
```

This will:
1. Load markdown documents from `data/guidance/`
2. Create embeddings using OpenAI
3. Store in PostgreSQL with pgvector
4. Test semantic search functionality

**Note**: This requires a running PostgreSQL instance with the pgvector extension.

## Step 6: Test the API

### Using cURL

```bash
# Health check
curl http://localhost:8000/health

# Submit test incident
curl -X POST http://localhost:8000/api/v1/incidents/submit \
  -H "Content-Type: application/json" \
  -d '{
    "incident_type": "water_pollution",
    "location": "River Thames, Reading",
    "latitude": 51.4543,
    "longitude": -0.9781,
    "description": "Oil spill observed in river",
    "reporter_email": "test@example.com",
    "urgency": "high"
  }'
```

### Using Python

```python
import requests

incident = {
    "incident_type": "water_pollution",
    "location": "River Thames, Reading",
    "latitude": 51.4543,
    "longitude": -0.9781,
    "description": "Oil spill observed in river",
    "reporter_email": "test@example.com",
    "urgency": "high"
}

response = requests.post(
    "http://localhost:8000/api/v1/incidents/submit",
    json=incident
)

print(response.json())
```

### Using the Interactive API Docs

Open `http://localhost:8000/docs` in your browser for an interactive API interface powered by Swagger UI.

## Step 7: Explore the Data

### View Synthetic Incidents

```bash
# View all test incidents
cat data/synthetic/test_incidents.json | jq '.[0]'

# View a specific example
cat data/synthetic/examples/example_1.json | jq '.'
```

### Query Neo4j

Access the Neo4j Browser at `http://localhost:7474` and run:

```cypher
// Once data is loaded, you can query like this:
MATCH (n) RETURN n LIMIT 25
```

### Query PostgreSQL

```bash
# Connect to PostgreSQL
docker exec -it defra-postgres psql -U postgres -d incident_reporting

# List tables
\dt

# View documents
SELECT title, LEFT(content, 100) FROM documents LIMIT 5;
```

## Troubleshooting

### Docker Issues

**Problem**: Containers not starting
```bash
# Check logs
docker-compose logs

# Restart services
docker-compose down
docker-compose up -d
```

**Problem**: Port already in use
```bash
# Find process using port 8000
lsof -i :8000  # Linux/Mac
netstat -ano | findstr :8000  # Windows

# Change port in docker-compose.yml or .env
```

### Python Issues

**Problem**: Import errors
```bash
# Ensure virtual environment is activated
which python  # Should point to .venv/bin/python

# Reinstall dependencies
uv pip install -e ".[dev,docs]"
```

**Problem**: OpenAI API errors
```bash
# Verify API key is set
echo $OPENAI_API_KEY

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

### Database Issues

**Problem**: Cannot connect to PostgreSQL
```bash
# Check if container is running
docker ps | grep postgres

# Check logs
docker logs defra-postgres

# Verify password matches .env
```

**Problem**: pgvector extension not found
```bash
# Recreate database with init script
docker-compose down -v
docker-compose up -d
```

## Next Steps

1. **Explore the codebase**: Check out `app/` directory
2. **Read the documentation**: See `docs/` for architecture and guides
3. **Run tests**: `pytest` (once implemented)
4. **Contribute**: See development workflow in README

## Getting Help

- **Documentation**: `docs/` directory
- **API Reference**: `http://localhost:8000/docs`
- **Issues**: [GitHub Issues](https://github.com/steve-dickinson/agentic-incident-reporting/issues)

## Development Workflow

```bash
# 1. Create feature branch
git checkout -b feature/your-feature

# 2. Make changes
# ... edit files ...

# 3. Format code
black app/ tests/

# 4. Run tests
pytest

# 5. Commit and push
git add .
git commit -m "feat: your feature description"
git push origin feature/your-feature
```

---

**You're all set!** 🎉 The system is ready for development and testing.
