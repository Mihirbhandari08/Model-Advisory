import asyncio
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from agents.constraint_extractor import ConstraintExtractor

async def main():
    print("🚀 Starting LangSmith verification...")
    
    api_key = os.getenv("LANGCHAIN_API_KEY")
    if not api_key:
        print("❌ LANGCHAIN_API_KEY not found in environment!")
        return

    print(f"✅ Found LANGCHAIN_API_KEY: {api_key[:5]}...")
    
    try:
        extractor = ConstraintExtractor()
        query = "I need a model for text summarization that runs on 16GB VRAM"
        print(f"Testing extraction with query: '{query}'")
        
        # This should trigger a trace
        result = await extractor.extract(query)
        
        print("\n✅ Extraction successful!")
        print(f"Primary Task: {result.primary_task}")
        print("\n✨ Check your LangSmith project 'model-advisory' for the trace!")
        
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")

if __name__ == "__main__":
    asyncio.run(main())
