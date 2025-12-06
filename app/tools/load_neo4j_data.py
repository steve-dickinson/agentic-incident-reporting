"""
Load protected sites and water bodies data into Neo4j graph database.

This script initializes the Neo4j database with sample UK environmental data
including protected sites (SSSI, SAC, NNR) and major water bodies.
"""

import json
import os
from pathlib import Path
from neo4j import GraphDatabase
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class Neo4jDataLoader:
    """Load environmental data into Neo4j graph database."""
    
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7688")
        self.user = os.getenv("NEO4J_USER", "neo4j")
        self.password = os.getenv("NEO4J_PASSWORD", "")
        self.driver = None
        self.data_dir = Path(__file__).parent.parent.parent / "data"
        self.config_dir = Path(__file__).parent.parent.parent / "config"
    
    def connect(self):
        """Connect to Neo4j database."""
        print(f"Connecting to Neo4j at {self.uri}...")
        self.driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password)
        )
        self.driver.verify_connectivity()
        print("✓ Connected successfully")
    
    def close(self):
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
    
    def initialize_schema(self):
        """Create constraints and indexes."""
        print("\nInitializing database schema...")
        
        schema_file = self.config_dir / "neo4j_schema.cypher"
        with open(schema_file, 'r') as f:
            schema_statements = f.read()
        
        # Split by semicolon and execute each statement
        statements = [s.strip() for s in schema_statements.split(';') if s.strip() and not s.strip().startswith('//')]
        
        with self.driver.session() as session:
            for statement in statements:
                # Skip comment-only lines
                if statement.startswith('//') or not statement:
                    continue
                try:
                    session.run(statement)
                    print(f"✓ Executed: {statement[:60]}...")
                except Exception:
                    print(f"! Already exists or error: {statement[:60]}...")
        
        print("✓ Schema initialized")
    
    def clear_existing_data(self):
        """Clear all existing nodes and relationships."""
        print("\nClearing existing data...")
        
        with self.driver.session() as session:
            # Delete all relationships and nodes
            session.run("MATCH (n) DETACH DELETE n")
        
        print("✓ Existing data cleared")
    
    def load_protected_sites(self):
        """Load protected sites from JSON file."""
        print("\nLoading protected sites...")
        
        sites_file = self.data_dir / "protected_sites.json"
        with open(sites_file, 'r') as f:
            sites = json.load(f)
        
        query = """
        CREATE (s:ProtectedSite {
            site_id: $site_id,
            name: $name,
            designation_type: $designation_type,
            area_hectares: $area_hectares,
            location: point({latitude: $latitude, longitude: $longitude}),
            features: $features,
            designations: $designations,
            vulnerable_to: $vulnerable_to
        })
        """
        
        with self.driver.session() as session:
            for site in sites:
                session.run(query, site)
                print(f"✓ Loaded: {site['name']} ({site['designation_type']})")
        
        print(f"✓ Loaded {len(sites)} protected sites")
    
    def load_water_bodies(self):
        """Load water bodies from JSON file."""
        print("\nLoading water bodies...")
        
        water_file = self.data_dir / "water_bodies.json"
        with open(water_file, 'r') as f:
            water_bodies = json.load(f)
        
        query = """
        CREATE (w:WaterBody {
            body_id: $body_id,
            name: $name,
            water_type: $water_type,
            location: point({latitude: $latitude, longitude: $longitude}),
            water_quality_status: $water_quality_status,
            protected_sites_nearby: $protected_sites_nearby
        })
        """
        
        with self.driver.session() as session:
            for water in water_bodies:
                # Add optional properties based on water type
                params = {k: v for k, v in water.items() if k not in ['length_km', 'area_km2', 'max_depth_m', 'catchment_area_km2', 'major_tributaries', 'tidal_range_m', 'marine_protected_areas', 'designation']}
                
                session.run(query, params)
                print(f"✓ Loaded: {water['name']} ({water['water_type']})")
        
        print(f"✓ Loaded {len(water_bodies)} water bodies")
    
    def create_relationships(self):
        """Create spatial relationships between nodes."""
        print("\nCreating spatial relationships...")
        
        # Link water bodies to nearby protected sites
        query_water_sites = """
        MATCH (w:WaterBody), (s:ProtectedSite)
        WHERE s.site_id IN w.protected_sites_nearby
        CREATE (w)-[:NEAR {distance_km: 0.5}]->(s)
        """
        
        # Link protected sites that are close to each other
        query_nearby_sites = """
        MATCH (s1:ProtectedSite), (s2:ProtectedSite)
        WHERE s1.site_id < s2.site_id
          AND point.distance(s1.location, s2.location) <= 50000
        WITH s1, s2, round(point.distance(s1.location, s2.location) / 1000.0, 2) as dist
        CREATE (s1)-[:NEAR {distance_km: dist}]->(s2)
        """
        
        with self.driver.session() as session:
            session.run(query_water_sites)
            print("✓ Created water body ↔ protected site relationships")
            
            session.run(query_nearby_sites)
            print("✓ Created nearby protected site relationships")
        
        print("✓ Relationships created")
    
    def verify_data(self):
        """Verify loaded data."""
        print("\nVerifying loaded data...")
        
        queries = {
            "Protected Sites": "MATCH (s:ProtectedSite) RETURN count(s) as count",
            "Water Bodies": "MATCH (w:WaterBody) RETURN count(w) as count",
            "Relationships": "MATCH ()-[r:NEAR]->() RETURN count(r) as count"
        }
        
        with self.driver.session() as session:
            for label, query in queries.items():
                result = session.run(query)
                count = result.single()["count"]
                print(f"✓ {label}: {count}")
    
    def run(self, clear_existing: bool = False):
        """Run the complete data loading process."""
        try:
            self.connect()
            self.initialize_schema()
            
            if clear_existing:
                self.clear_existing_data()
            
            self.load_protected_sites()
            self.load_water_bodies()
            self.create_relationships()
            self.verify_data()
            
            print("\n✅ Neo4j data loading complete!")
            
        except Exception as e:
            print(f"\n❌ Error during data loading: {e}")
            raise
        finally:
            self.close()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Load environmental data into Neo4j")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data before loading"
    )
    args = parser.parse_args()
    
    loader = Neo4jDataLoader()
    loader.run(clear_existing=args.clear)
