# Human-in-the-Loop with LangGraph

## Overview

Human-in-the-loop (HITL) allows agent workflows to pause for human approval or input before proceeding with critical actions. This is essential for:

- **High-stakes decisions** - Critical incidents requiring manager approval
- **Compliance requirements** - Regulatory checks before notifications
- **Quality assurance** - Review AI classifications before escalation
- **Learning feedback** - Human corrections to improve future decisions

## LangGraph HITL Concepts

### 1. Interrupts (Breakpoints)

LangGraph supports interrupting workflow execution at specific nodes:

```python
from langgraph.graph import StateGraph

workflow = StateGraph(State)
workflow.add_node("classify", classify_node)
workflow.add_node("notify", notify_node)

# Compile with interrupt before critical action
app = workflow.compile(
    checkpointer=MemorySaver(),
    interrupt_before=["notify"]  # Pause before notifications
)
```

### 2. Checkpointers

Checkpointers persist workflow state, enabling pause/resume:

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver

# In-memory (development)
memory = MemorySaver()

# SQLite (production)
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
```

### 3. Threading

Each incident gets a unique thread for independent workflow tracking:

```python
config = {
    "configurable": {
        "thread_id": incident_id,  # Unique per incident
        "checkpoint_ns": "incident_workflow"
    }
}

# Start workflow
result = app.invoke(initial_state, config=config)

# Resume after approval
result = app.invoke(None, config=config)  # Continues from interrupt
```

## Implementation Pattern

### Step 1: Define Approval State

Add approval fields to workflow state:

```python
class IncidentState(TypedDict):
    incident_id: str
    severity: str
    priority: str
    actions: list[str]
    # HITL fields
    requires_approval: bool
    approved: bool | None
    approval_reason: str | None
    approver_id: str | None
```

### Step 2: Add Approval Logic

Create a conditional edge based on severity:

```python
def should_require_approval(state: IncidentState) -> str:
    """Route critical incidents through approval."""
    if state["severity"] in ["critical", "high"]:
        return "request_approval"
    return "notify"

workflow.add_conditional_edges(
    "classify",
    should_require_approval,
    {
        "request_approval": "approval_gate",
        "notify": "notify"
    }
)
```

### Step 3: Create Approval Gate

Add a node that sets approval requirement:

```python
def approval_gate(state: IncidentState) -> IncidentState:
    """Mark incident as requiring approval."""
    state["requires_approval"] = True
    state["approved"] = None  # Waiting for decision
    logger.info(f"Incident {state['incident_id']} requires approval")
    return state

workflow.add_node("approval_gate", approval_gate)
```

### Step 4: Compile with Interrupt

Pause execution at the approval gate:

```python
app = workflow.compile(
    checkpointer=SqliteSaver.from_conn_string("checkpoints.db"),
    interrupt_before=["notify"]  # Human approves before notification
)
```

### Step 5: API Endpoints for Approval

Create endpoints to manage approvals:

```python
@app.post("/api/v1/incidents/{incident_id}/approve")
async def approve_incident(
    incident_id: str,
    approval: IncidentApproval
):
    """Approve and resume incident workflow."""
    
    # Update state with approval
    config = {"configurable": {"thread_id": incident_id}}
    current_state = app.get_state(config)
    
    current_state.values["approved"] = True
    current_state.values["approver_id"] = approval.approver_id
    current_state.values["approval_reason"] = approval.reason
    
    # Resume workflow
    result = app.invoke(None, config=config)
    
    return {"status": "approved", "result": result}

@app.post("/api/v1/incidents/{incident_id}/reject")
async def reject_incident(
    incident_id: str,
    rejection: IncidentRejection
):
    """Reject incident and halt workflow."""
    
    config = {"configurable": {"thread_id": incident_id}}
    current_state = app.get_state(config)
    
    current_state.values["approved"] = False
    current_state.values["approval_reason"] = rejection.reason
    
    # Workflow stops here - no resume
    return {"status": "rejected", "incident_id": incident_id}

@app.get("/api/v1/incidents/pending-approval")
async def get_pending_approvals():
    """List all incidents awaiting approval."""
    
    # Query checkpointer for interrupted workflows
    pending = []
    for thread_id, state in checkpointer.list():
        if state.get("requires_approval") and state.get("approved") is None:
            pending.append({
                "incident_id": state["incident_id"],
                "severity": state["severity"],
                "priority": state["priority"],
                "actions": state["actions"],
                "paused_at": state.get("timestamp")
            })
    
    return pending
```

## Dashboard Integration

### Approval Queue View

Add a tab in the Streamlit dashboard for pending approvals:

```python
st.subheader("⏸️ Pending Approvals")

pending = requests.get(f"{API_URL}/api/v1/incidents/pending-approval").json()

if pending:
    for incident in pending:
        with st.expander(f"🔴 {incident['incident_id']} - {incident['severity']}"):
            st.write(f"**Priority:** {incident['priority']}")
            st.write(f"**Actions:** {', '.join(incident['actions'][:3])}...")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Approve", key=f"approve_{incident['incident_id']}"):
                    requests.post(
                        f"{API_URL}/api/v1/incidents/{incident['incident_id']}/approve",
                        json={"approver_id": "manager", "reason": "Approved via dashboard"}
                    )
                    st.success("Approved! Workflow resumed.")
                    st.rerun()
            
            with col2:
                if st.button("❌ Reject", key=f"reject_{incident['incident_id']}"):
                    reason = st.text_input("Rejection reason:")
                    if reason:
                        requests.post(
                            f"{API_URL}/api/v1/incidents/{incident['incident_id']}/reject",
                            json={"reason": reason}
                        )
                        st.error("Rejected. Workflow halted.")
                        st.rerun()
else:
    st.info("No incidents pending approval")
```

## Advanced Patterns

### 1. Multi-Level Approval

Different severity levels require different approvers:

```python
def get_required_approver(state: IncidentState) -> str:
    """Determine who must approve."""
    if state["severity"] == "critical":
        return "director"
    elif state["severity"] == "high":
        return "manager"
    return "team_lead"
```

### 2. Time-Based Auto-Approval

Auto-approve if no response within SLA:

```python
import time

def check_approval_timeout(state: IncidentState) -> str:
    """Auto-approve after 1 hour."""
    paused_at = state.get("paused_timestamp")
    if time.time() - paused_at > 3600:  # 1 hour
        state["approved"] = True
        state["approval_reason"] = "Auto-approved after timeout"
        return "notify"
    return "waiting"
```

### 3. Feedback Loop

Collect human corrections to improve classifications:

```python
@app.post("/api/v1/incidents/{incident_id}/correct")
async def correct_classification(
    incident_id: str,
    correction: ClassificationCorrection
):
    """Human corrects AI classification."""
    
    # Store correction for model fine-tuning
    await db.execute("""
        INSERT INTO classification_corrections 
        (incident_id, original_severity, corrected_severity, reason)
        VALUES ($1, $2, $3, $4)
    """, incident_id, correction.original, correction.corrected, correction.reason)
    
    # Update state and resume with corrected classification
    config = {"configurable": {"thread_id": incident_id}}
    current_state = app.get_state(config)
    current_state.values["severity"] = correction.corrected
    
    result = app.invoke(None, config=config)
    return {"status": "corrected", "result": result}
```

## Database Schema

Store approval history:

```sql
CREATE TABLE incident_approvals (
    id SERIAL PRIMARY KEY,
    incident_id VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,  -- 'pending', 'approved', 'rejected'
    approver_id VARCHAR(100),
    approver_role VARCHAR(50),
    reason TEXT,
    approved_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (incident_id) REFERENCES incidents(incident_id)
);

CREATE INDEX idx_approvals_status ON incident_approvals(status);
CREATE INDEX idx_approvals_incident ON incident_approvals(incident_id);
```

## Benefits

1. **Compliance** - Regulatory requirements for human oversight
2. **Risk Management** - Prevent automated errors in critical situations
3. **Learning** - Collect human feedback to improve AI
4. **Accountability** - Clear audit trail of who approved what
5. **Flexibility** - Different approval rules for different scenarios

## Example Workflow

```
┌─────────────┐
│   Submit    │
│  Incident   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Classify   │
│   (AI)      │
└──────┬──────┘
       │
       ▼
    ┌──────┐
    │ High │ NO
    │ Risk?├────────┐
    └───┬──┘        │
        │ YES       │
        ▼           ▼
┌─────────────┐  ┌─────────────┐
│ ⏸️ PAUSE    │  │   Notify    │
│  Approval   │  │  (Auto)     │
│  Required   │  └─────────────┘
└──────┬──────┘
       │
   [Human Reviews]
       │
       ▼
    ┌──────┐
    │Approve│ NO  ┌─────────────┐
    │  ?   ├─────►│   Reject    │
    └───┬──┘      └─────────────┘
        │ YES
        ▼
┌─────────────┐
│   Notify    │
│  (Resume)   │
└─────────────┘
```

## Next Steps

1. Implement checkpointer with SQLite/Postgres
2. Add interrupt points to incident workflow
3. Create approval API endpoints
4. Add approval queue to dashboard
5. Test with realistic scenarios
6. Add metrics for approval times
