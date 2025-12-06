// Neo4j Graph Schema for Environmental Incident Reporting
// Run this script to initialize the graph database schema

// Create constraints and indexes
CREATE CONSTRAINT protected_site_id IF NOT EXISTS FOR (s:ProtectedSite) REQUIRE s.site_id IS UNIQUE;
CREATE CONSTRAINT water_body_id IF NOT EXISTS FOR (w:WaterBody) REQUIRE w.body_id IS UNIQUE;
CREATE CONSTRAINT incident_id IF NOT EXISTS FOR (i:Incident) REQUIRE i.incident_id IS UNIQUE;
CREATE CONSTRAINT location_id IF NOT EXISTS FOR (l:Location) REQUIRE l.location_id IS UNIQUE;

// Create indexes for efficient spatial and text queries
CREATE INDEX protected_site_name IF NOT EXISTS FOR (s:ProtectedSite) ON (s.name);
CREATE INDEX protected_site_type IF NOT EXISTS FOR (s:ProtectedSite) ON (s.designation_type);
CREATE INDEX water_body_name IF NOT EXISTS FOR (w:WaterBody) ON (w.name);
CREATE INDEX incident_type IF NOT EXISTS FOR (i:Incident) ON (i.incident_type);
CREATE INDEX incident_date IF NOT EXISTS FOR (i:Incident) ON (i.reported_at);
CREATE INDEX incident_severity IF NOT EXISTS FOR (i:Incident) ON (i.severity);

// Create point property indexes for spatial queries
CREATE POINT INDEX protected_site_location IF NOT EXISTS FOR (s:ProtectedSite) ON (s.location);
CREATE POINT INDEX water_body_location IF NOT EXISTS FOR (w:WaterBody) ON (s.location);
CREATE POINT INDEX incident_location IF NOT EXISTS FOR (i:Incident) ON (i.location);

// Node Labels:
// - ProtectedSite: SAC, SSSI, NNR, Ramsar sites
// - WaterBody: Rivers, lakes, coastal waters
// - Incident: Environmental incidents
// - Location: Geographic locations for grouping
// - Species: Protected wildlife species
// - Regulation: Environmental regulations and permits

// Relationship Types:
// - NEAR: Spatial proximity (with distance property)
// - AFFECTS: Incident impacts protected site
// - FLOWS_THROUGH: Water body flows through location
// - PROTECTED_BY: Site protected by regulation
// - HABITAT_FOR: Site provides habitat for species
// - SIMILAR_TO: Historical pattern matching
// - OCCURRED_AT: Incident occurred at location
