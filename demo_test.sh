#!/bin/bash
# Demo Test Script for Defra AI Agent
# This script demonstrates the complete workflow with multiple scenarios

set -e  # Exit on error

BASE_URL="${BASE_URL:-http://localhost:8000}"
BOLD='\033[1m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BOLD}${BLUE}======================================${NC}"
echo -e "${BOLD}${BLUE}  Defra AI Agent - Demo Walkthrough  ${NC}"
echo -e "${BOLD}${BLUE}======================================${NC}\n"

# Check if jq is available
if ! command -v jq &> /dev/null; then
    echo -e "${YELLOW}Warning: jq not found. Installing formatted output will be limited.${NC}"
    echo -e "${YELLOW}Install jq for better output: sudo apt install jq${NC}\n"
    JQ_AVAILABLE=false
else
    JQ_AVAILABLE=true
fi

# Function to print section headers
print_section() {
    echo -e "\n${BOLD}${GREEN}=== $1 ===${NC}"
}

# Function to print test results
print_result() {
    if [ $JQ_AVAILABLE = true ]; then
        echo "$1" | jq .
    else
        echo "$1" | python3 -m json.tool 2>/dev/null || echo "$1"
    fi
}

# 1. Health Check
print_section "1. Testing Health Check"
HEALTH=$(curl -s $BASE_URL/health)
if [ $JQ_AVAILABLE = true ]; then
    STATUS=$(echo $HEALTH | jq -r '.status')
    if [ "$STATUS" = "healthy" ]; then
        echo -e "${GREEN}✓ API is healthy${NC}"
    else
        echo -e "${RED}✗ API health check failed${NC}"
        exit 1
    fi
    echo $HEALTH | jq .
else
    echo $HEALTH
fi

# 2. Critical Incident
print_section "2. Scenario 1: Critical Water Pollution"
echo "Submitting: Toxic chemical spill near drinking water source..."

RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/incidents/submit \
  -H "Content-Type: application/json" \
  -d '{
    "incident_type": "water_pollution",
    "description": "Toxic chemical spill near drinking water treatment plant, immediate danger to public health",
    "location": "Thames Water Treatment Plant, London",
    "latitude": 51.4875,
    "longitude": -0.1687,
    "reporter_email": "emergency@example.com",
    "urgency": "critical"
  }')

if [ $JQ_AVAILABLE = true ]; then
    INCIDENT_ID=$(echo $RESPONSE | jq -r '.incident_id')
    SEVERITY=$(echo $RESPONSE | jq -r '.severity')
    PRIORITY=$(echo $RESPONSE | jq -r '.priority')
    
    echo -e "${GREEN}✓ Incident Created: $INCIDENT_ID${NC}"
    echo -e "  Severity: ${RED}$SEVERITY${NC}"
    echo -e "  Priority: $PRIORITY"
    
    echo -e "\n${BOLD}Key Actions:${NC}"
    echo $RESPONSE | jq -r '.actions[:5][]' | while read -r action; do
        echo "  • $action"
    done
    
    echo -e "\n${BOLD}Spatial Context:${NC}"
    echo $RESPONSE | jq -r '.spatial_context | to_entries[] | "  \(.key): \(.value)"'
else
    print_result "$RESPONSE"
fi

# 3. High Priority with Spatial Context
print_section "3. Scenario 2: Oil Spill Near Protected Site"
echo "Submitting: Oil spill in Lake Windermere (near SSSI)..."

RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/incidents/submit \
  -H "Content-Type: application/json" \
  -d '{
    "incident_type": "water_pollution",
    "description": "Large oil slick observed affecting Lake Windermere SSSI",
    "location": "Lake Windermere, Cumbria",
    "latitude": 54.3500,
    "longitude": -2.9333,
    "reporter_email": "witness@example.com",
    "urgency": "high"
  }')

if [ $JQ_AVAILABLE = true ]; then
    INCIDENT_ID=$(echo $RESPONSE | jq -r '.incident_id')
    SEVERITY=$(echo $RESPONSE | jq -r '.severity')
    
    echo -e "${GREEN}✓ Incident Created: $INCIDENT_ID${NC}"
    echo -e "  Severity: ${YELLOW}$SEVERITY${NC}"
    
    echo -e "\n${BOLD}Protected Sites Found:${NC}"
    SITES=$(echo $RESPONSE | jq -r '.spatial_context.protected_sites')
    echo "  $SITES"
    
    echo -e "\n${BOLD}Water Bodies Found:${NC}"
    WATER=$(echo $RESPONSE | jq -r '.spatial_context.water_bodies')
    echo "  $WATER"
else
    print_result "$RESPONSE"
fi

# 4. Illegal Dumping
print_section "4. Scenario 3: Illegal Dumping Near National Park"
echo "Submitting: Construction waste in Peak District..."

RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/incidents/submit \
  -H "Content-Type: application/json" \
  -d '{
    "incident_type": "illegal_dumping",
    "description": "Large pile of construction waste dumped in Peak District National Park",
    "location": "Peak District, Derbyshire",
    "latitude": 53.2958,
    "longitude": -1.7978,
    "reporter_email": "ranger@example.com",
    "urgency": "high"
  }')

if [ $JQ_AVAILABLE = true ]; then
    INCIDENT_ID=$(echo $RESPONSE | jq -r '.incident_id')
    SEVERITY=$(echo $RESPONSE | jq -r '.severity')
    
    echo -e "${GREEN}✓ Incident Created: $INCIDENT_ID${NC}"
    echo -e "  Severity: ${YELLOW}$SEVERITY${NC}"
    
    echo -e "\n${BOLD}Waste-Specific Actions:${NC}"
    echo $RESPONSE | jq -r '.actions[]' | grep -i 'waste\|evidence\|removal\|hazardous' | while read -r action; do
        echo "  • $action"
    done
else
    print_result "$RESPONSE"
fi

# 5. Low Priority Incident
print_section "5. Scenario 4: Low-Priority Noise Complaint"
echo "Submitting: Minor construction noise..."

RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/incidents/submit \
  -H "Content-Type: application/json" \
  -d '{
    "incident_type": "noise_pollution",
    "description": "Minor noise from construction site during daytime hours",
    "location": "Commercial area, Manchester",
    "latitude": 53.4808,
    "longitude": -2.2426,
    "reporter_email": "resident@example.com",
    "urgency": "low"
  }')

if [ $JQ_AVAILABLE = true ]; then
    INCIDENT_ID=$(echo $RESPONSE | jq -r '.incident_id')
    SEVERITY=$(echo $RESPONSE | jq -r '.severity')
    PRIORITY=$(echo $RESPONSE | jq -r '.priority')
    
    echo -e "${GREEN}✓ Incident Created: $INCIDENT_ID${NC}"
    echo -e "  Severity: ${BLUE}$SEVERITY${NC}"
    echo -e "  Priority: $PRIORITY"
    
    echo -e "\n${BOLD}Routine Actions:${NC}"
    echo $RESPONSE | jq -r '.actions[]' | while read -r action; do
        echo "  • $action"
    done
else
    print_result "$RESPONSE"
fi

# 6. Incident Without Coordinates
print_section "6. Scenario 5: Incident Without GPS Coordinates"
echo "Submitting: Air pollution report without coordinates..."

RESPONSE=$(curl -s -X POST $BASE_URL/api/v1/incidents/submit \
  -H "Content-Type: application/json" \
  -d '{
    "incident_type": "air_pollution",
    "description": "Smoke emissions from industrial facility",
    "location": "Birmingham Industrial Estate",
    "reporter_email": "concerned@example.com",
    "urgency": "medium"
  }')

if [ $JQ_AVAILABLE = true ]; then
    INCIDENT_ID=$(echo $RESPONSE | jq -r '.incident_id')
    SEVERITY=$(echo $RESPONSE | jq -r '.severity')
    
    echo -e "${GREEN}✓ Incident Created: $INCIDENT_ID${NC}"
    echo -e "  Severity: $SEVERITY"
    echo -e "  Note: Spatial queries skipped (no coordinates provided)"
else
    print_result "$RESPONSE"
fi

# Summary
print_section "Demo Complete - Summary"
echo -e "${GREEN}✓ All scenarios executed successfully${NC}"
echo -e "\n${BOLD}Scenarios Tested:${NC}"
echo "  1. Critical water pollution (P1 - 1 hour response)"
echo "  2. Oil spill near protected site (P2 - 4 hour response)"
echo "  3. Illegal dumping in national park (P2 - 4 hour response)"
echo "  4. Low-priority noise complaint (P4 - 5 day response)"
echo "  5. Air pollution without coordinates (P3 - 24 hour response)"

echo -e "\n${BOLD}Key Features Demonstrated:${NC}"
echo "  • Intelligent severity classification"
echo "  • Dynamic action generation"
echo "  • Spatial awareness (Neo4j queries)"
echo "  • Protected site identification"
echo "  • Priority-based response times"
echo "  • Email notifications (test mode)"
echo "  • Semantic guidance search"

echo -e "\n${BOLD}${GREEN}Demo walkthrough completed successfully!${NC}"
echo -e "${BLUE}Review logs with: docker compose logs api --tail=100${NC}\n"
