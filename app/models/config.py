"""
Configuration management for the Defra AI Agent
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    log_level: str = "INFO"
    
    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4-turbo-preview"
    openai_embedding_model: str = "text-embedding-3-small"
    
    # Neo4j Configuration
    neo4j_uri: str = "bolt://neo4j:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str
    neo4j_database: str = "neo4j"
    
    # PostgreSQL Configuration
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "incident_reporting"
    postgres_user: str = "postgres"
    postgres_password: str
    
    # GOV.UK Notify Configuration
    notify_api_key: str
    notify_email_template_id: str | None = None
    notify_sms_template_id: str | None = None
    notify_test_mode: bool = True
    
    # Agent Configuration
    agent_max_iterations: int = 10
    agent_temperature: float = 0.0
    enable_tracing: bool = True
    
    # Data Paths
    synthetic_data_path: str = "/app/data/synthetic"
    embeddings_path: str = "/app/data/embeddings"
    guidance_docs_path: str = "/app/data/guidance"
    
    # Security
    secret_key: str
    allowed_origins: str = "http://localhost:3000,http://localhost:8000"
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    @property
    def postgres_url(self) -> str:
        """Construct PostgreSQL connection URL"""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse allowed origins into a list"""
        return [origin.strip() for origin in self.allowed_origins.split(",")]


# Create global settings instance
settings = Settings()
