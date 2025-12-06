"""
Neo4j spatial query tools for environmental incident analysis.

Provides tools for querying protected sites, water bodies, and historical
incidents using Neo4j's spatial capabilities.
"""

from langchain_core.tools import tool
from neo4j import GraphDatabase
import os


class Neo4jConnection:
    """Manage Neo4j database connection."""
    
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7688")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "")
        self.driver = None
    
    def connect(self):
        """Establish connection to Neo4j."""
        if not self.driver:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.user, self.password)
            )
        return self.driver
    
    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            self.driver = None
    
    def execute_query(self, query: str, parameters: dict | None = None) -> list[dict]:
        """Execute a Cypher query and return results."""
        driver = self.connect()
        with driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]


# Global connection instance
_neo4j_conn = Neo4jConnection()


@tool
def find_nearby_protected_sites(
    latitude: float,
    longitude: float,
    radius_km: float = 5.0
) -> str:
    """
    Find protected sites (SSSI, SAC, NNR, Ramsar) near incident location.
    
    Args:
        latitude: Incident latitude
        longitude: Incident longitude
        radius_km: Search radius in kilometers (default: 5km)
    
    Returns:
        JSON string with nearby protected sites and their distances
    """
    query = """
    MATCH (s:ProtectedSite)
    WHERE point.distance(
        s.location,
        point({latitude: $lat, longitude: $lon})
    ) <= $radius * 1000
    RETURN s.site_id as site_id,
           s.name as name,
           s.designation_type as type,
           s.area_hectares as area,
           s.features as features,
           s.vulnerable_to as vulnerable_to,
           round(point.distance(
               s.location,
               point({latitude: $lat, longitude: $lon})
           ) / 1000.0, 2) as distance_km
    ORDER BY distance_km
    """
    
    try:
        results = _neo4j_conn.execute_query(
            query,
            {"lat": latitude, "lon": longitude, "radius": radius_km}
        )
        
        if not results:
            return f"No protected sites found within {radius_km}km of location ({latitude}, {longitude})"
        
        sites_info = []
        for site in results:
            sites_info.append(
                f"- {site['name']} ({site['type']}): {site['distance_km']}km away, "
                f"{site['area']} hectares, vulnerable to: {', '.join(site['vulnerable_to'])}"
            )
        
        return (
            f"Found {len(results)} protected site(s) within {radius_km}km:\n" +
            "\n".join(sites_info)
        )
    except Exception as e:
        return f"Error querying protected sites: {str(e)}"


@tool
def find_nearby_water_bodies(
    latitude: float,
    longitude: float,
    radius_km: float = 10.0
) -> str:
    """
    Find water bodies (rivers, lakes, coastal waters) near incident location.
    
    Args:
        latitude: Incident latitude
        longitude: Incident longitude
        radius_km: Search radius in kilometers (default: 10km)
    
    Returns:
        JSON string with nearby water bodies and their details
    """
    query = """
    MATCH (w:WaterBody)
    WHERE point.distance(
        w.location,
        point({latitude: $lat, longitude: $lon})
    ) <= $radius * 1000
    RETURN w.body_id as body_id,
           w.name as name,
           w.water_type as type,
           w.water_quality_status as quality,
           round(point.distance(
               w.location,
               point({latitude: $lat, longitude: $lon})
           ) / 1000.0, 2) as distance_km
    ORDER BY distance_km
    """
    
    try:
        results = _neo4j_conn.execute_query(
            query,
            {"lat": latitude, "lon": longitude, "radius": radius_km}
        )
        
        if not results:
            return f"No water bodies found within {radius_km}km of location ({latitude}, {longitude})"
        
        water_info = []
        for water in results:
            water_info.append(
                f"- {water['name']} ({water['type']}): {water['distance_km']}km away, "
                f"quality status: {water['quality']}"
            )
        
        return (
            f"Found {len(results)} water body/bodies within {radius_km}km:\n" +
            "\n".join(water_info)
        )
    except Exception as e:
        return f"Error querying water bodies: {str(e)}"


@tool
def check_similar_incidents(
    incident_type: str,
    latitude: float,
    longitude: float,
    days_back: int = 90,
    radius_km: float = 25.0
) -> str:
    """
    Find similar incidents in the same area within specified timeframe.
    
    Args:
        incident_type: Type of incident to search for
        latitude: Incident latitude
        longitude: Incident longitude
        days_back: How many days to look back (default: 90)
        radius_km: Search radius in kilometers (default: 25km)
    
    Returns:
        Information about similar historical incidents
    """
    query = """
    MATCH (i:Incident)
    WHERE i.incident_type = $incident_type
      AND point.distance(
          i.location,
          point({latitude: $lat, longitude: $lon})
      ) <= $radius * 1000
      AND i.reported_at >= datetime() - duration({days: $days_back})
    RETURN i.incident_id as incident_id,
           i.severity as severity,
           i.description as description,
           i.reported_at as reported_at,
           round(point.distance(
               i.location,
               point({latitude: $lat, longitude: $lon})
           ) / 1000.0, 2) as distance_km
    ORDER BY i.reported_at DESC
    LIMIT 10
    """
    
    try:
        results = _neo4j_conn.execute_query(
            query,
            {
                "incident_type": incident_type,
                "lat": latitude,
                "lon": longitude,
                "radius": radius_km,
                "days_back": days_back
            }
        )
        
        if not results:
            return (
                f"No similar {incident_type} incidents found within {radius_km}km "
                f"in the last {days_back} days"
            )
        
        incidents_info = []
        for inc in results:
            incidents_info.append(
                f"- {inc['severity'].upper()} severity incident {inc['distance_km']}km away "
                f"on {inc['reported_at']}"
            )
        
        return (
            f"Found {len(results)} similar {incident_type} incident(s):\n" +
            "\n".join(incidents_info) +
            "\n\nThis may indicate a pattern or recurring issue in the area."
        )
    except Exception as e:
        return f"Error querying historical incidents: {str(e)}"


@tool
def get_site_regulations(site_id: str) -> str:
    """
    Get environmental regulations and protections for a specific site.
    
    Args:
        site_id: Protected site identifier (e.g., 'SSSI-001')
    
    Returns:
        Regulatory information and protection details
    """
    query = """
    MATCH (s:ProtectedSite {site_id: $site_id})
    OPTIONAL MATCH (s)-[:PROTECTED_BY]->(r:Regulation)
    RETURN s.name as name,
           s.designation_type as type,
           s.designations as designations,
           collect(r.name) as regulations
    """
    
    try:
        results = _neo4j_conn.execute_query(query, {"site_id": site_id})
        
        if not results or not results[0].get("name"):
            return f"Protected site {site_id} not found in database"
        
        site = results[0]
        designations = ", ".join(site["designations"])
        
        response = (
            f"{site['name']} ({site['type']})\n"
            f"Designations: {designations}\n"
        )
        
        if site["regulations"]:
            response += f"Protected by: {', '.join(site['regulations'])}"
        else:
            response += "Protected under general UK environmental legislation"
        
        return response
    except Exception as e:
        return f"Error querying site regulations: {str(e)}"


def close_neo4j_connection():
    """Close the global Neo4j connection. Call on application shutdown."""
    _neo4j_conn.close()
