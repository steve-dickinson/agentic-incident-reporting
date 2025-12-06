# Phase 9: Logging & Dashboard Implementation

## Overview

Added comprehensive structured logging and a real-time Streamlit dashboard to monitor agent execution and system performance.

## New Features

### 1. Structured Execution Logging

**Location**: `app/models/logging.py`

- **AgentLogger class**: PostgreSQL-backed logging system
- **Step-level tracking**: Records each agent step (classify, spatial, guidance, notify)
- **Metrics captured**:
  - Execution status (started, completed, failed)
  - Input/output data for each step
  - Duration in milliseconds
  - Error messages
- **Async implementation**: Non-blocking logging using asyncpg connection pool

### 2. Enhanced Database Schema

**Location**: `config/logging-schema.sql`

**New Tables**:
- `execution_logs`: Detailed step-by-step execution tracking
- `incident_metrics`: Daily aggregated statistics
  
**New Views**:
- `dashboard_summary`: 7-day incident summary with priorities and completion rates
- `recent_incidents_detail`: Recent incidents with execution step counts

**Indexes**: Optimized for dashboard queries on incident_id, step_name, status, created_at

### 3. Dashboard API Endpoints

**Location**: `app/api/dashboard.py`

**Endpoints**:
- `GET /api/v1/dashboard/summary` - Summary statistics (7-day totals, priorities, avg time)
- `GET /api/v1/dashboard/incidents?limit=50` - Recent incidents with execution details
- `GET /api/v1/dashboard/incidents/{id}/logs` - Step-by-step execution logs
- `GET /api/v1/dashboard/metrics?hours=24` - Hourly metrics for charts

### 4. Streamlit Dashboard

**Location**: `dashboard/app.py`

**Features**:

**Metrics Cards**:
- Total incidents (7-day)
- Critical incidents (P1)
- High priority (P2)
- Completion rate
- Average processing time

**Interactive Charts**:
- Incidents over time (24-hour trend)
- Processing time trend
- Priority distribution (pie chart)
- Status overview (completed/failed/processing)

**Recent Incidents Table**:
- Searchable and filterable
- Columns: ID, type, location, severity, priority, status, processing time
- Filters: Priority (P1-P4), Type, Status

**Execution Log Viewer**:
- Select any incident to view step-by-step execution
- Shows input/output data for each step
- Displays duration and error messages
- Color-coded status indicators (✅ ❌ 🔄)

**Auto-refresh**: Configurable refresh interval (5-60 seconds)

## Technical Implementation

### Agent Integration

Modified `app/agents/incident_agent.py` to log each workflow step:

1. **Before each step**: Log "started" status with input data
2. **After success**: Log "completed" status with output data and duration
3. **On failure**: Log "failed" status with error message and duration

Example logging call:
```python
await agent_logger.log_step(
    incident_id=state["incident_id"],
    step_name="classify",
    step_order=1,
    status="completed",
    output_data={"severity": "critical", "priority": "P1"},
    duration_ms=250
)
```

### Docker Deployment

**New Services**:
- **dashboard**: Streamlit app on port 8501
- Dockerfile: `dashboard/Dockerfile`
- Requirements: streamlit, pandas, plotly, requests

**Updated Services**:
- **postgres**: Now runs both `init-db.sql` and `logging-schema.sql` on startup
- **api**: Includes dashboard router

### Database Performance

**Optimizations**:
- BTREE indexes on frequently queried columns
- GIN index on JSONB metadata
- Materialized views for dashboard summary (refresh via cron or trigger)
- Connection pooling (2-10 connections)

## Usage

### Starting the System

```bash
# Start all services including dashboard
docker-compose up -d

# View dashboard
open http://localhost:8501
```

### API Examples

```bash
# Get dashboard summary
curl http://localhost:8000/api/v1/dashboard/summary

# Get recent incidents
curl http://localhost:8000/api/v1/dashboard/incidents?limit=20

# Get execution logs for specific incident
curl http://localhost:8000/api/v1/dashboard/incidents/INC-20231206-001/logs

# Get hourly metrics
curl http://localhost:8000/api/v1/dashboard/metrics?hours=48
```

### Dashboard Features

1. **Auto-refresh**: Enable in sidebar to refresh data automatically
2. **Time range**: Adjust metrics time range (1-168 hours)
3. **Filters**: Filter incidents by priority, type, or status
4. **Drill-down**: Click any incident to view detailed execution logs
5. **Export**: Use DataFrame export features for data analysis

## Benefits

1. **Observability**: Full visibility into agent execution
2. **Debugging**: Step-by-step logs with timing and error details
3. **Performance monitoring**: Track processing times and bottlenecks
4. **Operational insights**: Priority distribution, completion rates
5. **Real-time awareness**: Live dashboard for incident monitoring

## Future Enhancements

- Add alerting for failed incidents or slow processing
- Export dashboard data to CSV/Excel
- Add custom date range selectors
- Implement user authentication
- Add cost tracking (OpenAI API usage)
- Create automated reports

## Files Changed/Added

**New Files**:
- `config/logging-schema.sql` - Logging database schema
- `app/models/logging.py` - AgentLogger class
- `app/api/dashboard.py` - Dashboard API endpoints
- `dashboard/app.py` - Streamlit dashboard
- `dashboard/Dockerfile` - Dashboard container
- `dashboard/requirements.txt` - Dashboard dependencies

**Modified Files**:
- `app/agents/incident_agent.py` - Added logging calls
- `app/api/main.py` - Included dashboard router
- `docker-compose.yml` - Added dashboard service
- `pyproject.toml` - Added asyncpg dependency
- `README.md` - Added dashboard documentation

## Testing

To verify the logging and dashboard:

1. Submit test incidents via API or demo script
2. Check execution_logs table: `SELECT * FROM execution_logs ORDER BY created_at DESC;`
3. View dashboard at http://localhost:8501
4. Verify step-by-step execution in dashboard log viewer
5. Check metrics and charts update in real-time

## Performance Impact

- **Minimal overhead**: Async logging doesn't block agent workflow
- **Database impact**: ~5 rows per incident (1 per step)
- **Memory**: Connection pool uses ~50MB
- **Dashboard**: Refreshes every 5-10 seconds by default
