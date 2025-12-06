"""
Synthetic data generator for environmental incident reports.

This module creates realistic test data for the AI agent system without
using any real personal or sensitive information.
"""

from faker import Faker
from datetime import datetime, timedelta
import json
import random
from pathlib import Path

fake = Faker('en_GB')  # UK locale for realistic addresses


class IncidentGenerator:
    """Generate synthetic environmental incident reports"""
    
    INCIDENT_TYPES = [
        "water_pollution",
        "air_pollution",
        "illegal_waste_dumping",
        "wildlife_harm",
        "noise_pollution",
        "chemical_spill",
        "oil_spill",
        "habitat_destruction",
        "fly_tipping",
        "agricultural_runoff",
    ]
    
    URGENCY_LEVELS = ["low", "medium", "high", "critical"]
    
    WATER_POLLUTION_DESCRIPTIONS = [
        "Oil slick observed in {location}",
        "Discolored water noticed in {location}, possibly chemical contamination",
        "Dead fish found in {location}",
        "Foam and unusual smell detected in {location}",
        "Industrial discharge seen entering {location}",
        "Sewage overflow into {location}",
    ]
    
    AIR_POLLUTION_DESCRIPTIONS = [
        "Strong chemical odor reported near {location}",
        "Black smoke emissions from {location}",
        "Dust pollution affecting {location}",
        "Burning smell and haze at {location}",
    ]
    
    WASTE_DESCRIPTIONS = [
        "Large quantity of household waste dumped at {location}",
        "Construction waste illegally deposited in {location}",
        "Commercial waste bags abandoned at {location}",
        "Hazardous materials found dumped at {location}",
        "Vehicle parts and tires fly-tipped at {location}",
    ]
    
    UK_LOCATIONS = [
        {"name": "River Thames", "lat": 51.5074, "lon": -0.1278},
        {"name": "Lake District", "lat": 54.4609, "lon": -3.0886},
        {"name": "Peak District", "lat": 53.3678, "lon": -1.8297},
        {"name": "Norfolk Broads", "lat": 52.6309, "lon": 1.3089},
        {"name": "Dartmoor", "lat": 50.5719, "lon": -3.9892},
        {"name": "Yorkshire Dales", "lat": 54.2043, "lon": -2.0914},
        {"name": "Brecon Beacons", "lat": 51.8838, "lon": -3.4361},
        {"name": "River Severn", "lat": 52.1929, "lon": -2.2219},
        {"name": "Snowdonia", "lat": 53.0679, "lon": -3.9180},
        {"name": "New Forest", "lat": 50.8617, "lon": -1.6051},
    ]
    
    def __init__(self, seed: int | None = None):
        """Initialize generator with optional seed for reproducibility"""
        if seed:
            Faker.seed(seed)
            random.seed(seed)
    
    def generate_incident(self) -> dict[str, any]:
        """Generate a single synthetic incident report"""
        incident_type = random.choice(self.INCIDENT_TYPES)
        location = random.choice(self.UK_LOCATIONS)
        
        # Select description template based on incident type
        if "pollution" in incident_type and "water" in incident_type:
            description_template = random.choice(self.WATER_POLLUTION_DESCRIPTIONS)
        elif "pollution" in incident_type and "air" in incident_type:
            description_template = random.choice(self.AIR_POLLUTION_DESCRIPTIONS)
        elif "waste" in incident_type or "tipping" in incident_type:
            description_template = random.choice(self.WASTE_DESCRIPTIONS)
        else:
            description_template = f"{incident_type.replace('_', ' ').title()} incident at {{location}}"
        
        description = description_template.format(location=location["name"])
        
        # Add some location variance
        lat_offset = random.uniform(-0.01, 0.01)
        lon_offset = random.uniform(-0.01, 0.01)
        
        urgency = random.choice(self.URGENCY_LEVELS)
        
        incident = {
            "incident_type": incident_type,
            "location": f"{location['name']}, {fake.city()}",
            "latitude": round(location["lat"] + lat_offset, 6),
            "longitude": round(location["lon"] + lon_offset, 6),
            "description": description,
            "urgency": urgency,
            "additional_info": {
                "reported_at": datetime.now().isoformat(),
                "weather": random.choice(["sunny", "rainy", "cloudy", "windy"]),
                "visibility": random.choice(["good", "moderate", "poor"]),
            }
        }
        
        # Randomly include contact information (50% of cases)
        if random.random() > 0.5:
            incident["reporter_email"] = fake.email()
            
        if random.random() > 0.7:
            incident["reporter_phone"] = fake.phone_number()
            
        return incident
    
    def generate_batch(self, count: int) -> list[dict[str, any]]:
        """Generate multiple incident reports"""
        return [self.generate_incident() for _ in range(count)]
    
    def save_to_file(self, incidents: list[dict[str, any]], filepath: str | Path) -> None:
        """Save incidents to JSON file"""
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(incidents, f, indent=2, default=str)
        
        print(f"Saved {len(incidents)} incidents to {filepath}")


def generate_test_dataset(output_dir: str | Path = "data/synthetic", count: int = 50) -> None:
    """Generate and save a test dataset"""
    generator = IncidentGenerator(seed=42)  # Reproducible
    incidents = generator.generate_batch(count)
    
    output_path = Path(output_dir) / "test_incidents.json"
    generator.save_to_file(incidents, output_path)
    
    # Also create individual examples
    examples_dir = Path(output_dir) / "examples"
    examples_dir.mkdir(parents=True, exist_ok=True)
    
    for idx, incident in enumerate(incidents[:5]):
        example_path = examples_dir / f"example_{idx + 1}.json"
        with open(example_path, 'w') as f:
            json.dump(incident, f, indent=2, default=str)
    
    print(f"Generated {count} synthetic incidents")
    print(f"Saved 5 examples to {examples_dir}")


if __name__ == "__main__":
    generate_test_dataset()
