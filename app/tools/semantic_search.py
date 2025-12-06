"""
Semantic search tool for querying guidance documents using pgvector.
"""

from langchain_core.tools import tool
from app.tools.embeddings import SemanticSearch


_search_instance = SemanticSearch()


@tool
def search_guidance_documents(query: str, top_k: int = 3) -> str:
    """
    Search environmental guidance documents for relevant information.
    
    Use this tool to find regulations, procedures, and best practices
    for handling environmental incidents. The database includes:
    - Incident response procedures
    - UK environmental legislation
    - Protected site regulations
    - Classification criteria
    
    Args:
        query: Search query describing what information you need
        top_k: Number of relevant documents to return (default: 3)
    
    Returns:
        Relevant guidance document excerpts with similarity scores
    """
    try:
        results = _search_instance.search(query, top_k=top_k, similarity_threshold=0.6)
        
        if not results:
            return f"No relevant guidance found for query: '{query}'"
        
        formatted_results = []
        for i, result in enumerate(results, 1):
            formatted_results.append(
                f"**Result {i}** (similarity: {result['similarity']:.2f}):\n"
                f"{result['content']}\n"
            )
        
        return "\n---\n".join(formatted_results)
        
    except Exception as e:
        return f"Error searching guidance documents: {str(e)}"
