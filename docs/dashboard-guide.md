# Dashboard Quick Reference

## Accessing the Dashboard

```bash
# Start the dashboard
docker-compose up -d dashboard

# Open in browser
open http://localhost:8502
```

## Dashboard Sections

### 1. Summary Metrics (Top Row)

| Metric | Description |
|--------|-------------|
| **Total Incidents** | All incidents processed in last 7 days |
| **Critical (P1)** | Priority 1 incidents requiring immediate response |
| **High (P2)** | Priority 2 incidents requiring response within 4 hours |
| **Completed** | Successfully processed incidents |
| **Avg Time** | Average processing time across all incidents |

### 2. Charts

**Incidents Over Time (24h)**
- Line chart showing incident volume by hour
- Separate lines for Total, P1 Critical, P2 High
- Hover for exact counts

**Processing Time Trend**
- Bar chart of average processing time per hour
- Color intensity shows performance (green = faster)
- Identifies bottlenecks and slow periods

**Priority Distribution**
- Donut chart showing P1/P2/P3/P4 breakdown
- Color-coded: Red (P1), Orange (P2), Yellow (P3), Green (P4)

**Status Overview**
- Bar chart: Completed, Failed, Processing
- Shows system health and error rates

### 3. Recent Incidents Table

**Columns**:
- Incident ID
- Type (water_pollution, air_pollution, illegal_dumping, noise_pollution)
- Location
- Severity (critical, high, medium, low)
- Priority (P1, P2, P3, P4)
- Status (processing, completed, failed)
- Processing Time
- Steps Completed ✓
- Steps Failed ✗

**Filters**:
- Priority: Select one or more (P1, P2, P3, P4)
- Type: Filter by incident type
- Status: Filter by processing status

### 4. Incident Details (Bottom Section)

Select any incident from the dropdown to view:

**Execution Steps**: Each step shows:
- Status indicator (✅ Completed / ❌ Failed / 🔄 Processing)
- Step name and order
- Duration in milliseconds
- Input data (JSON)
- Output data (JSON)
- Error message (if failed)

**Workflow Steps**:
1. **Classify**: Incident classification, severity, priority
2. **Spatial**: Protected sites, water bodies nearby
3. **Guidance**: Semantic search for relevant procedures
4. **Notify**: Email notifications sent

## Sidebar Controls

**API Base URL**: Change if API is on different host (default: `http://localhost:8000`)

**Auto-refresh**: Enable to refresh data automatically
- Refresh interval: 5-60 seconds (slider)
- Default: 10 seconds

## Common Use Cases

### Monitoring Active Incidents

1. Enable auto-refresh (10s interval)
2. Watch the "Processing" count in Status Overview
3. Check Recent Incidents table for latest entries

### Debugging Failed Incidents

1. Filter by Status: "failed"
2. Select failed incident from dropdown
3. Review Execution Steps for error messages
4. Check which step failed and why

### Performance Analysis

1. Review "Processing Time Trend" chart
2. Identify hours with slow processing
3. Check "Avg Time" metric
4. Investigate specific slow incidents

### Priority Monitoring

1. Watch P1/P2 metrics in top row
2. Review Priority Distribution chart
3. Filter table by P1 to see critical incidents
4. Ensure P1 incidents are processed quickly

## API Integration

Dashboard calls these API endpoints:

```bash
# Summary stats
curl http://localhost:8000/api/v1/dashboard/summary

# Recent incidents (limit 50)
curl http://localhost:8000/api/v1/dashboard/incidents?limit=50

# Specific incident logs
curl http://localhost:8000/api/v1/dashboard/incidents/INC-20231206-001/logs

# Hourly metrics (24 hours)
curl http://localhost:8000/api/v1/dashboard/metrics?hours=24
```

## Tips & Tricks

**Refresh Data**: Click "Rerun" button in top-right or wait for auto-refresh

**Full Screen**: Click "Settings" → "Wide mode" for more screen space

**Export Data**: Hover over table → Click download icon → Export to CSV

**Dark Mode**: Settings → Theme → Dark (useful for monitoring displays)

**Performance**: Increase refresh interval if dashboard feels slow

**Troubleshooting**: Check API health at http://localhost:8000/health

## Database Queries

Direct database queries for advanced analysis:

```sql
-- Recent execution logs
SELECT * FROM execution_logs 
ORDER BY created_at DESC 
LIMIT 100;

-- Failed steps today
SELECT incident_id, step_name, error_message 
FROM execution_logs 
WHERE status = 'failed' 
AND created_at > CURRENT_DATE;

-- Average processing time by step
SELECT 
    step_name,
    AVG(duration_ms) as avg_ms,
    COUNT(*) as count
FROM execution_logs
WHERE status = 'completed'
GROUP BY step_name;

-- Incidents by priority today
SELECT 
    classification->>'priority' as priority,
    COUNT(*) as count
FROM incidents
WHERE created_at > CURRENT_DATE
GROUP BY priority;
```

## Keyboard Shortcuts

- `R` - Rerun dashboard
- `C` - Clear cache
- `S` - Settings menu
- `/` - Search (in sidebar)

## Support

For issues or questions:
- Check API logs: `docker logs defra-agent-api`
- Check dashboard logs: `docker logs defra-dashboard`
- Review database: `psql -h localhost -p 5433 -U postgres -d incident_reporting`
