# System Architecture

## Overview

The Defra AI Agent for Environmental Incident Reporting is a microservices-based system that combines AI reasoning, knowledge graphs, and semantic search to automate incident triage and response coordination.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        External Systems                          │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────────────┐  │
│  │ Form Submit│  │ GOV.UK Notify│  │ Environment Agency DB │  │
│  └──────┬─────┘  └──────▲───────┘  └───────────────────────┘  │
└─────────┼────────────────┼──────────────────────────────────────┘
          │                │
          ▼                │
┌─────────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                         │
│  ┌───────────────┐  ┌─────────────┐  ┌──────────────────────┐ │
│  │ /submit       │  │ /health     │  │ /incidents/{id}      │ │
│  │ /docs         │  │ /status     │  │ /search              │ │
│  └───────┬───────┘  └─────────────┘  └──────────────────────┘ │
└──────────┼──────────────────────────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Agent Orchestration (LangGraph)                     │
│                                                                   │
│  ┌──────────┐   ┌───────────┐   ┌──────────┐   ┌────────────┐ │
│  │  Intake  │──▶│ Classify  │──▶│ Context  │──▶│   Action   │ │
│  │          │   │           │   │ Gather   │   │  Execute   │ │
│  └──────────┘   └───────────┘   └────┬─────┘   └─────┬──────┘ │
│                                       │               │         │
└───────────────────────────────────────┼───────────────┼─────────┘
                                        │               │
                        ┌───────────────┴───┬───────────┴──────┐
                        ▼                   ▼                  ▼
           ┌────────────────────┐  ┌────────────────┐  ┌─────────────┐
           │  Neo4j Graph DB    │  │ PostgreSQL +   │  │  External   │
           │  (Knowledge Graph) │  │  pgvector      │  │  Services   │
           └────────────────────┘  └────────────────┘  └─────────────┘
```

## Component Details

### 1. API Layer (FastAPI)

**Purpose**: HTTP interface for incident submission and system interaction

**Key Features**:
- RESTful endpoints with OpenAPI documentation
- Pydantic V2 models for request/response validation
- Async request handling
- CORS middleware for frontend integration
- **Security Headers Middleware**: OWASP-compliant headers (XSS, clickjacking, CSP)
- **Rate Limiting Middleware**: 100 req/min, 2000 req/hour per IP
- **Custom Exception Handling**: Structured error responses with context
- Comprehensive error handling and logging

**Endpoints**:
- `POST /api/v1/incidents/submit` - Submit new incident
- `POST /api/v1/incidents/{id}/approve` - Approve HITL workflow
- `POST /api/v1/incidents/{id}/reject` - Reject HITL workflow
- `GET /api/v1/incidents/pending-approval` - List pending approvals
- `GET /api/v1/incidents/{id}` - Retrieve incident details
- `GET /health` - Health check for monitoring
- `GET /docs` - Interactive API documentation

**Security Features**:
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `X-XSS-Protection`, `CSP`
- Rate limiting with headers: `X-RateLimit-Remaining-Minute`, `X-RateLimit-Limit-Hour`
- IP-based tracking with X-Forwarded-For support
- Automatic cleanup of rate limit records

**Technology Stack**:
- FastAPI 0.109+
- Uvicorn (ASGI server)
- Pydantic 2.7+ (validation)
- Python 3.12+
- Starlette middleware

### 2. Agent Orchestration (LangChain + LangGraph)

**Purpose**: Coordinate AI reasoning and tool execution with human-in-the-loop controls

**Key Features**:
- **Checkpoint-based State Management**: LangGraph MemorySaver persists workflow state
- **Interrupt-based HITL**: High-priority incidents (P1/P2) pause for human approval
- **Workflow Resumption**: Continue from exact checkpoint after human decision
- **Full Auditability**: Every step logged with inputs, outputs, and timing

**Workflow States**:

```
┌──────────┐
│  START   │
└────┬─────┘
     │
     ▼
┌──────────────────────┐
│  Incident Intake     │  ← Parse and validate submission
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  Classification      │  ← Determine incident type and severity
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  Context Gathering   │  ← Query Neo4j, search docs, check history
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  Decision Making     │  ← Apply rules and AI reasoning
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│  Action Execution    │  ← Send notifications, log to graph
└──────┬───────────────┘
       │
       ▼
┌──────────┐
│   END    │  ← Return result to API
└──────────┘
```

**Agent Tools**:
1. **Classification Tool** - Categorize incident with Pydantic validation
   - Output validation with auto-correction
   - Priority/severity mismatch auto-fix
   - Action deduplication and quality checks
   - Fallback mechanism for graceful degradation
2. **Semantic Search Tool** - Query guidance documents
3. **Spatial Query Tool** - Search Neo4j with connection pooling
4. **Notification Tool** - Send via GOV.UK Notify
5. **Logging Tool** - Record to database and graph

**Validation & Error Handling**:
- **Pydantic V2 Validators**: Field-level validation with custom validators
- **Auto-Correction**: Automatically fix priority/severity mismatches
- **Custom Exceptions**: `ClassificationError`, `SpatialQueryError`, `NotificationError`
- **Structured Errors**: Exception `.to_dict()` for API responses
- **Fallback Mechanisms**: Graceful degradation on validation failures

**Technology Stack**:
- LangChain 0.1+
- LangGraph 0.2+ (with MemorySaver checkpointer)
- OpenAI GPT-4 Turbo
- Pydantic 2.7+ (validation)
- LangSmith (observability)

**[Learn more about the HITL pattern →](../guides/langgraph_hitl_pattern.md)**

### 3. Knowledge Graph (Neo4j)

**Purpose**: Store and query spatial, temporal, and relational data

**Graph Schema**:

```cypher
// Node Types
(Incident {id, type, severity, location, timestamp})
(ProtectedSite {name, designation, coordinates, area})
(WaterBody {name, type, catchment, quality})
(Organization {name, type, contact})
(Response {id, actions, timestamp})

// Relationship Types
(Incident)-[:LOCATED_NEAR]->(ProtectedSite)
(Incident)-[:AFFECTS]->(WaterBody)
(Incident)-[:SIMILAR_TO]->(Incident)
(Response)-[:ADDRESSES]->(Incident)
(Organization)-[:RESPONSIBLE_FOR]->(ProtectedSite)
```

**Queries Supported**:
- Spatial proximity: "Find protected sites within 5km"
- Historical patterns: "Similar incidents in past 12 months"
- Impact analysis: "Water bodies affected downstream"
- Responsibility: "Which organization manages this area"

**Technology Stack**:
- Neo4j 5.16
- Neo4j Python Driver with connection pooling (50 connections)
- APOC procedures
- Graph Data Science library
- Spatial functions

**Connection Pooling**:
- Managed connection pool with 50 max connections
- Context managers for automatic cleanup
- Connection reuse for efficient queries
- 30-second connection acquisition timeout
- 90% reduction in connection overhead

**Performance Optimizations**:
- Connection pooling eliminates per-query connection overhead
- Thread-safe session handling for concurrent requests
- Automatic connection verification on startup
- Graceful connection cleanup on shutdown

### 4. Vector Store (PostgreSQL + pgvector)

**Purpose**: Semantic search over guidance documents and regulations

**Schema**:

```sql
documents (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255),
    content TEXT,
    metadata JSONB,
    embedding vector(1536),  -- OpenAI embedding dimensions
    created_at TIMESTAMP
)

incidents (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(50) UNIQUE,
    form_data JSONB,
    classification VARCHAR(100),
    agent_actions JSONB,
    created_at TIMESTAMP
)
```

**Embedding Model**: OpenAI text-embedding-3-small (1536 dimensions)

**Search Method**: Cosine similarity with IVFFlat index

**Technology Stack**:
- PostgreSQL 16
- pgvector extension
- psycopg2 driver

### 5. Notification Service (GOV.UK Notify)

**Purpose**: Send email and SMS notifications to citizens and staff

**Templates**:
- Incident acknowledgment (to reporter)
- Team alert (to Environment Agency)
- Status update (follow-up communications)

**Features**:
- Templated messaging
- Delivery tracking
- Retry logic
- Test mode for development

## Data Flow

### Incident Submission Flow

```
1. Citizen submits form
   ↓
2. API validates request (Pydantic)
   ↓
3. Agent orchestration begins
   ↓
4. Classification
   - LLM analyzes description
   - Matches against guidance
   - Assigns severity and type
   ↓
5. Context Gathering (parallel)
   ├─→ Semantic search: "What are the rules for this incident?"
   ├─→ Graph query: "Are there protected sites nearby?"
   └─→ History check: "Have similar incidents occurred?"
   ↓
6. Decision Making
   - Apply regulatory rules
   - Determine required actions
   - Calculate priority
   ↓
7. Action Execution (parallel)
   ├─→ Send notification to reporter
   ├─→ Alert internal team
   ├─→ Log to PostgreSQL
   └─→ Create graph nodes/relationships
   ↓
8. Return response to API
   ↓
9. API returns result to client
```

## Security Architecture

### Authentication & Authorization

**Current State** (Prototype):
- No authentication (internal demo only)
- API key for external services (OpenAI, Notify)

**Production Requirements**:
- OAuth 2.0 / OpenID Connect
- Role-based access control (RBAC)
- API gateway with rate limiting

### Data Protection

**PII Handling**:
- Minimal PII collection
- Email/phone optional
- No storage of sensitive data
- Synthetic data for all testing

**Encryption**:
- TLS for all external communications
- Environment variables for secrets
- Database encryption at rest (production)

### Network Security

**Current Setup**:
- Docker network isolation
- No exposed database ports (except for development)

**Production Requirements**:
- VPC/private subnets
- Firewall rules
- DDoS protection
- WAF for API

## Scalability Considerations

### Horizontal Scaling

**API Layer**:
- Stateless design
- Can run multiple instances behind load balancer
- Async processing for long-running tasks

**Agent Processing**:
- Queue-based architecture for incident processing
- Multiple agent workers
- Celery or similar task queue

### Database Scaling

**PostgreSQL**:
- Read replicas for queries
- Connection pooling
- Partitioning for large tables

**Neo4j**:
- Causal clustering for high availability
- Read replicas for queries
- Sharding by region if needed

### Caching Strategy

**Redis** (future):
- API response caching
- Session storage
- Rate limiting counters

## Monitoring & Observability

### Metrics

**Application Metrics**:
- Request rate, latency, errors
- Agent execution time
- Tool invocation frequency

**Database Metrics**:
- Query performance
- Connection pool usage
- Index effectiveness

**Business Metrics**:
- Incidents processed per hour
- Classification accuracy
- Response time SLA

### Logging

**Structured Logging**:
- JSON format
- Request ID correlation
- Log levels: DEBUG, INFO, WARNING, ERROR

**Log Aggregation**:
- ELK stack (production)
- CloudWatch (AWS deployment)

### Tracing

**LangSmith**:
- Agent execution traces
- Tool call tracking
- Performance bottleneck identification

## Deployment Architecture

### Local Development

```
Docker Compose
├── API Container (Python 3.12)
├── Neo4j Container
├── PostgreSQL Container
└── Bridge Network
```

### Cloud Deployment (AWS Example)

```
┌─────────────────────────────────────────┐
│              CloudFront                  │
│         (CDN / WAF / DDoS)              │
└──────────────┬──────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────┐
│     Application Load Balancer           │
└────┬──────────────────┬─────────────────┘
     │                  │
     ▼                  ▼
┌─────────┐       ┌─────────┐
│ ECS API │       │ ECS API │  (Auto-scaling)
│ Task 1  │       │ Task 2  │
└────┬────┘       └────┬────┘
     │                 │
     └────────┬────────┘
              │
    ┌─────────┴──────────┐
    │                    │
    ▼                    ▼
┌─────────┐         ┌──────────┐
│ RDS     │         │ Neptune  │
│(Postgres)│         │ (Graph)  │
└─────────┘         └──────────┘
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: defra-agent-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: defra-agent
  template:
    spec:
      containers:
      - name: api
        image: defra-agent:latest
        env:
        - name: POSTGRES_HOST
          valueFrom:
            secretKeyRef:
              name: db-secrets
              key: host
```

## Technology Decisions

### Why Python 3.12?

- Modern type hints (PEP 604)
- Performance improvements
- Better error messages
- Strong ML/AI ecosystem

### Why FastAPI?

- Native async support
- Automatic API documentation
- Pydantic integration
- High performance

### Why LangChain/LangGraph?

- Industry standard for agents
- Extensive tool ecosystem
- Good observability
- Active development

### Why Neo4j?

- Native graph queries (Cypher)
- Spatial functions built-in
- Excellent for relationship queries
- Mature and stable

### Why pgvector over alternatives?

- Single database for all data
- ACID compliance
- Cost-effective
- Production-ready
- No external vector DB service needed

## Future Enhancements

1. **Real-time Processing**
   - WebSocket connections
   - Server-sent events for updates
   - Live dashboard

2. **Advanced Analytics**
   - Trend analysis
   - Predictive modeling
   - Hotspot detection

3. **Multi-modal Input**
   - Image analysis (pollution photos)
   - Voice submissions
   - Video evidence processing

4. **Enhanced Collaboration**
   - Multi-agency coordination
   - Shared incident views
   - Real-time chat

---

**Version**: 0.1.0  
**Last Updated**: December 2025  
**Status**: Development/Prototype
