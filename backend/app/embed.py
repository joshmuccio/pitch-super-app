import os
from typing import List
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize OpenAI client
client = AsyncOpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

async def embed_chunks(chunks: List[str]) -> List[List[float]]:
    """
    Generate embeddings for a list of text chunks using OpenAI text-embedding-3-large
    with 1536 dimensions for cost/performance optimization.
    
    Args:
        chunks: List of text strings to embed
        
    Returns:
        List of embedding vectors (each vector has 1536 dimensions)
        
    Raises:
        Exception: If OpenAI API call fails
    """
    try:
        # Call OpenAI embedding API
        response = await client.embeddings.create(
            model="text-embedding-3-large",
            input=chunks,
            dimensions=1536  # Reduced from default 3072 for performance
        )
        
        # Extract embeddings from response
        embeddings = [data.embedding for data in response.data]
        
        return embeddings
        
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        raise e

async def embed_single_chunk(text: str) -> List[float]:
    """
    Generate embedding for a single text chunk.
    
    Args:
        text: Text string to embed
        
    Returns:
        Single embedding vector (1536 dimensions)
    """
    embeddings = await embed_chunks([text])
    return embeddings[0]

# Alias for backwards compatibility
create_embedding = embed_single_chunk

def chunk_text(text: str, max_chunk_size: int = 8000) -> List[str]:
    """
    Split text into chunks for embedding processing.
    
    Args:
        text: Input text to chunk
        max_chunk_size: Maximum characters per chunk
        
    Returns:
        List of text chunks
    """
    if len(text) <= max_chunk_size:
        return [text]
    
    chunks = []
    words = text.split()
    current_chunk = []
    current_length = 0
    
    for word in words:
        word_length = len(word) + 1  # +1 for space
        
        if current_length + word_length > max_chunk_size and current_chunk:
            # Add current chunk and start new one
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_length = word_length
        else:
            current_chunk.append(word)
            current_length += word_length
    
    # Add final chunk if any words remain
    if current_chunk:
        chunks.append(' '.join(current_chunk))
    
    return chunks 