# Quick Reference Card

## 🚀 Quick Commands

### Setup
```bash
# Clone and enter directory
git clone https://github.com/steve-dickinson/agentic-incident-reporting.git
cd agentic-incident-reporting

# Setup environment
cp .env.example .env
# Edit .env with your keys

# Option 1: Docker (fastest)
docker-compose up -d

# Option 2: Local development
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e ".[dev,docs]"
```

### Daily Development
```bash
# Start environment
source .venv/bin/activate  # or docker-compose up -d

# Generate test data
python -m app.tools.synthetic_data

# Run API locally
uvicorn app.api.main:app --reload

# Run tests
pytest --cov=app

# Format & lint
black app/ tests/ && flake8 app/

# Build docs
mkdocs serve  # http://localhost:8001
```

### Docker
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Reset everything
docker-compose down -v
docker-compose up -d
```

## 📂 Key Files

| File | Purpose |
|------|---------|
| `app/api/main.py` | FastAPI application |
| `app/tools/synthetic_data.py` | Test data generator |
| `app/tools/embeddings.py` | Document embedding |
| `app/models/config.py` | Configuration |
| `docker-compose.yml` | Service orchestration |
| `.env.example` | Environment template |
| `pyproject.toml` | Project config |

## 🔗 Important URLs

| Service | URL | Credentials |
|---------|-----|-------------|
| API Docs | http://localhost:8000/docs | - |
| API Health | http://localhost:8000/health | - |
| Neo4j Browser | http://localhost:7474 | neo4j / (from .env) |
| MkDocs | http://localhost:8001 | - |

## 📝 Environment Variables

**Required:**
```bash
OPENAI_API_KEY=sk-your-key-here
NEO4J_PASSWORD=choose-strong-password
POSTGRES_PASSWORD=choose-strong-password
SECRET_KEY=$(openssl rand -hex 32)
```

**Optional:**
```bash
NOTIFY_API_KEY=your-notify-key
NOTIFY_TEST_MODE=true
```

## 🧪 Testing

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific tests
pytest tests/unit/
pytest tests/integration/ -v

# Watch mode
pytest-watch
```

## 🐛 Debugging

```bash
# Check service status
docker-compose ps

# View API logs
docker-compose logs -f api

# Check database
docker exec -it defra-postgres psql -U postgres -d incident_reporting

# Neo4j logs
docker-compose logs neo4j

# Python debugger
import pdb; pdb.set_trace()
```

## 📊 Data Locations

| Data Type | Location |
|-----------|----------|
| Synthetic Incidents | `data/synthetic/test_incidents.json` |
| Example Incidents | `data/synthetic/examples/` |
| Guidance Docs | `data/guidance/` |
| Embeddings | PostgreSQL `documents` table |
| Incident Logs | PostgreSQL `incidents` table |
| Graph Data | Neo4j database |

## 🛠️ Common Tasks

### Generate Test Data
```bash
python -m app.tools.synthetic_data
```

### Load Documents into Vector DB
```bash
# Requires running PostgreSQL and OPENAI_API_KEY
python -m app.tools.embeddings
```

### Submit Test Incident
```bash
curl -X POST http://localhost:8000/api/v1/incidents/submit \
  -H "Content-Type: application/json" \
  -d @data/synthetic/examples/example_1.json
```

### Format Code
```bash
black app/ tests/
```

### Type Check
```bash
mypy app/ --ignore-missing-imports
```

### Build Docker Image
```bash
docker build -t defra-agent:latest .
```

## 📚 Documentation

| Doc | Purpose |
|-----|---------|
| [README.md](https://github.com/steve-dickinson/agentic-incident-reporting#readme) | Project overview |
| [Getting Started](guides/getting_started.md) | Setup guide |
| [Architecture](architecture/system_design.md) | System design |
| [Progress Log](progress.md) | Development status |
| [API Docs](http://localhost:8000/docs) | Interactive API reference |

## 🔍 Troubleshooting

**Port already in use:**
```bash
lsof -i :8000  # Find process
kill -9 <PID>  # Kill process
```

**Database connection failed:**
```bash
# Check if container is running
docker ps | grep postgres

# Check logs
docker logs defra-postgres

# Restart
docker-compose restart postgres
```

**Import errors:**
```bash
# Ensure venv is activated
which python  # Should show .venv/bin/python

# Reinstall dependencies
uv pip install -e ".[dev,docs]"
```

**OpenAI API errors:**
```bash
# Check API key is set
echo $OPENAI_API_KEY

# Test key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer $OPENAI_API_KEY"
```

## 🎯 Git Workflow

```bash
# Create feature branch
git checkout -b feature/your-feature

# Make changes
# ... edit files ...

# Check status
git status

# Stage changes
git add .

# Commit (conventional commits)
git commit -m "feat: add new feature"
git commit -m "fix: resolve bug"
git commit -m "docs: update README"

# Push
git push origin feature/your-feature

# Create PR on GitHub
```

## 🏷️ Conventional Commits

- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation only
- `style:` Formatting, missing semi colons, etc
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Maintenance

## 📦 Package Management

```bash
# Add new dependency
uv pip install package-name

# Update requirements
uv pip freeze > requirements.txt

# Update pyproject.toml manually

# Reinstall all
uv pip install -e ".[dev,docs]"
```

## 🔐 Security Reminders

- Never commit `.env` file
- Use strong passwords for databases
- Rotate API keys regularly
- Don't log sensitive data
- Review secrets before pushing

## 💡 Tips

1. Use `uv` - it's 10-100x faster than pip
2. Enable auto-reload: `uvicorn app.api.main:app --reload`
3. Use Docker for consistent environments
4. Write tests before pushing
5. Format with Black before committing
6. Check docs: `mkdocs serve`
7. Use health endpoint for monitoring
8. Leverage FastAPI /docs for API testing

---

**Quick Help:** `python -m app.tools.synthetic_data --help`  
**Full Docs:** `mkdocs serve` → http://localhost:8001
