"""
Document embedding and loading utilities for semantic search.

This module handles loading guidance documents, creating embeddings,
and storing them in the pgvector database.
"""

from pathlib import Path
import json
from typing import Any
import hashlib

from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain.schema import Document
import psycopg2
from psycopg2.extras import execute_values

from app.models.config import settings


class DocumentEmbedder:
    """Handle document loading and embedding creation"""
    
    def __init__(self):
        """Initialize embedder with OpenAI embeddings"""
        self.embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            openai_api_key=settings.openai_api_key
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    def load_documents(self, directory: str | Path) -> list[Document]:
        """Load all markdown documents from a directory"""
        directory = Path(directory)
        
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        # Load markdown files
        loader = DirectoryLoader(
            str(directory),
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"}
        )
        
        documents = loader.load()
        print(f"Loaded {len(documents)} documents from {directory}")
        
        return documents
    
    def split_documents(self, documents: list[Document]) -> list[Document]:
        """Split documents into chunks for embedding"""
        chunks = self.text_splitter.split_documents(documents)
        print(f"Split into {len(chunks)} chunks")
        return chunks
    
    def embed_documents(self, documents: list[Document]) -> list[tuple[Document, list[float]]]:
        """Create embeddings for document chunks"""
        texts = [doc.page_content for doc in documents]
        embeddings = self.embeddings.embed_documents(texts)
        
        print(f"Created embeddings for {len(documents)} chunks")
        return list(zip(documents, embeddings))
    
    def get_db_connection(self):
        """Get PostgreSQL database connection"""
        return psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password
        )
    
    def store_embeddings(
        self,
        doc_embeddings: list[tuple[Document, list[float]]]
    ) -> int:
        """
        Store document embeddings in PostgreSQL with pgvector
        
        Returns:
            Number of documents stored
        """
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        stored_count = 0
        
        try:
            for doc, embedding in doc_embeddings:
                # Create unique title from source and chunk
                source = doc.metadata.get("source", "unknown")
                title = Path(source).stem
                
                # Create content hash to avoid duplicates
                content_hash = hashlib.md5(doc.page_content.encode()).hexdigest()
                metadata = {
                    **doc.metadata,
                    "content_hash": content_hash,
                    "chunk_length": len(doc.page_content)
                }
                
                # Check if document already exists
                cursor.execute(
                    "SELECT id FROM documents WHERE metadata->>'content_hash' = %s",
                    (content_hash,)
                )
                
                if cursor.fetchone():
                    print(f"Skipping duplicate: {title}")
                    continue
                
                # Insert document with embedding
                cursor.execute(
                    """
                    INSERT INTO documents (title, content, metadata, embedding)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (title, doc.page_content, json.dumps(metadata), embedding)
                )
                stored_count += 1
            
            conn.commit()
            print(f"Stored {stored_count} new document chunks in database")
            
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()
            conn.close()
        
        return stored_count
    
    def load_and_embed_directory(self, directory: str | Path) -> int:
        """
        Complete pipeline: load, split, embed, and store documents
        
        Returns:
            Number of documents stored
        """
        documents = self.load_documents(directory)
        chunks = self.split_documents(documents)
        doc_embeddings = self.embed_documents(chunks)
        count = self.store_embeddings(doc_embeddings)
        
        return count


class SemanticSearch:
    """Perform semantic search over embedded documents"""
    
    def __init__(self):
        """Initialize semantic search"""
        self.embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            openai_api_key=settings.openai_api_key
        )
    
    def get_db_connection(self):
        """Get PostgreSQL database connection"""
        return psycopg2.connect(
            host=settings.postgres_host,
            port=settings.postgres_port,
            database=settings.postgres_db,
            user=settings.postgres_user,
            password=settings.postgres_password
        )
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        similarity_threshold: float = 0.7
    ) -> list[dict[str, Any]]:
        """
        Perform semantic search for relevant documents
        
        Args:
            query: Search query text
            top_k: Number of top results to return
            similarity_threshold: Minimum similarity score (0-1)
        
        Returns:
            List of relevant document chunks with metadata
        """
        # Create query embedding
        query_embedding = self.embeddings.embed_query(query)
        
        conn = self.get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Perform vector similarity search using cosine distance
            cursor.execute(
                """
                SELECT 
                    id,
                    title,
                    content,
                    metadata,
                    1 - (embedding <=> %s::vector) as similarity
                FROM documents
                WHERE 1 - (embedding <=> %s::vector) > %s
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_embedding, query_embedding, similarity_threshold, query_embedding, top_k)
            )
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row[0],
                    "title": row[1],
                    "content": row[2],
                    "metadata": row[3],
                    "similarity": float(row[4])
                })
            
            return results
            
        finally:
            cursor.close()
            conn.close()


def load_guidance_documents() -> int:
    """Load all guidance documents into the database"""
    embedder = DocumentEmbedder()
    guidance_path = Path(settings.guidance_docs_path)
    
    if not guidance_path.exists():
        guidance_path.mkdir(parents=True, exist_ok=True)
        print(f"Created guidance directory: {guidance_path}")
        return 0
    
    count = embedder.load_and_embed_directory(guidance_path)
    return count


if __name__ == "__main__":
    # Load guidance documents
    print("Loading guidance documents...")
    count = load_guidance_documents()
    print(f"\nSuccessfully processed and stored {count} document chunks")
    
    # Test semantic search
    print("\n--- Testing Semantic Search ---")
    searcher = SemanticSearch()
    
    test_queries = [
        "What should I do for a water pollution incident?",
        "How do I handle illegal waste dumping?",
        "What are the rules for protected sites?",
    ]
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        results = searcher.search(query, top_k=2)
        for i, result in enumerate(results, 1):
            print(f"  {i}. {result['title']} (similarity: {result['similarity']:.3f})")
            print(f"     {result['content'][:100]}...")
