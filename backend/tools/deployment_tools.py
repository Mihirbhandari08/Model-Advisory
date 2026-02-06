"""Deployment Tools for ML System Design Expert."""
from typing import Dict, List, Any, Optional


class DeploymentTools:
    """Tooling for deployment and infrastructure recommendations."""

    def generate_docker_template(
        self,
        model_id: str,
        framework: str = "transformers",
        gpu: bool = False,
        port: int = 8000
    ) -> Dict[str, str]:
        """
        Generate Dockerfile and docker-compose for model serving.
        
        Args:
            model_id: Hugging Face model ID
            framework: transformers, vllm, ollama, tgi
            gpu: Whether to include GPU support
            port: Port to expose
            
        Returns:
            Dict with dockerfile and docker_compose content
        """
        base_image = "nvidia/cuda:12.1-runtime-ubuntu22.04" if gpu else "python:3.10-slim"
        
        if framework == "vllm":
            dockerfile = f"""FROM {base_image}

WORKDIR /app

RUN pip install vllm

ENV MODEL_ID="{model_id}"

EXPOSE {port}

CMD ["python", "-m", "vllm.entrypoints.openai.api_server", "--model", "$MODEL_ID", "--port", "{port}"]
"""
        elif framework == "tgi":
            dockerfile = f"""# Use Text Generation Inference
FROM ghcr.io/huggingface/text-generation-inference:latest

ENV MODEL_ID="{model_id}"

EXPOSE {port}
"""
        else:  # transformers (default)
            torch_line = 'torch==2.1.0+cu121 -f https://download.pytorch.org/whl/torch_stable.html' if gpu else 'torch'
            dockerfile = f"""FROM {base_image}

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir transformers {torch_line} fastapi uvicorn accelerate

# Copy application
COPY app.py .

ENV MODEL_ID="{model_id}"
ENV TRANSFORMERS_CACHE=/app/cache

EXPOSE {port}

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "{port}"]
"""

        # Build GPU deployment section separately
        gpu_deploy_section = """    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]""" if gpu else ""

        docker_compose = f"""version: '3.8'

services:
  model-server:
    build: .
    ports:
      - "{port}:{port}"
    environment:
      - MODEL_ID={model_id}
      - TRANSFORMERS_CACHE=/app/cache
    volumes:
      - ./cache:/app/cache
{gpu_deploy_section}
"""

        model_name_safe = model_id.replace("/", "_")
        app_py = f'''"""FastAPI model server for {model_id}."""
import os
from fastapi import FastAPI
from pydantic import BaseModel
from transformers import pipeline

app = FastAPI(title="Model Server", version="1.0.0")

# Load model on startup
model_id = os.getenv("MODEL_ID", "{model_id}")
pipe = None

@app.on_event("startup")
async def load_model():
    global pipe
    pipe = pipeline("feature-extraction", model=model_id)

class PredictRequest(BaseModel):
    text: str

@app.post("/predict")
async def predict(request: PredictRequest):
    result = pipe(request.text)
    return {{"result": result}}

@app.get("/health")
async def health():
    return {{"status": "healthy", "model": model_id}}
'''

        return {
            "dockerfile": dockerfile,
            "docker_compose": docker_compose,
            "app_py": app_py
        }

    def get_quantization_options(
        self,
        model_id: str,
        target_device: str = "cpu",
        model_size_mb: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Return quantization options and trade-offs.
        
        Args:
            model_id: Model identifier
            target_device: cpu, gpu, mobile, edge (raspberry pi, etc.)
            model_size_mb: Original model size in MB
            
        Returns:
            Dict with options, recommendations, and code samples
        """
        options = []
        model_short = model_id.split('/')[-1] if '/' in model_id else model_id
        
        # GGUF for CPU/edge
        if target_device in ["cpu", "edge", "mobile"]:
            gguf_code = f"""# Convert to GGUF using llama.cpp
# 1. Install llama.cpp
git clone https://github.com/ggerganov/llama.cpp
cd llama.cpp && make

# 2. Convert model
python convert.py {model_id} --outtype q4_k_m

# 3. Run with llama.cpp or Ollama
ollama run {model_short}"""
            options.append({
                "method": "GGUF (llama.cpp)",
                "description": "4-bit quantization for CPU inference",
                "size_reduction": "~4x smaller",
                "speed_improvement": "2-4x faster on CPU",
                "quality_impact": "Minor quality loss, good for most tasks",
                "best_for": ["CPU inference", "Edge devices", "Limited RAM"],
                "code": gguf_code
            })
        
        # INT8 for GPU
        if target_device in ["gpu", "cpu"]:
            int8_code = f"""from transformers import AutoModelForCausalLM
import torch

# Load with 8-bit quantization
model = AutoModelForCausalLM.from_pretrained(
    "{model_id}",
    load_in_8bit=True,
    device_map="auto"
)"""
            options.append({
                "method": "INT8 (bitsandbytes)",
                "description": "8-bit quantization for GPU inference",
                "size_reduction": "~2x smaller",
                "speed_improvement": "1.5-2x faster",
                "quality_impact": "Minimal quality loss",
                "best_for": ["GPU with limited VRAM", "Production servers"],
                "code": int8_code
            })
        
        # ONNX for all
        onnx_code = f"""from optimum.onnxruntime import ORTModelForSequenceClassification

# Convert and load ONNX model
model = ORTModelForSequenceClassification.from_pretrained(
    "{model_id}",
    export=True
)

# Or convert manually
from optimum.exporters.onnx import main_export
main_export("{model_id}", output="./model_onnx/")"""
        options.append({
            "method": "ONNX Runtime",
            "description": "Cross-platform optimized inference",
            "size_reduction": "~1x (same size, faster inference)",
            "speed_improvement": "1.5-3x faster",
            "quality_impact": "No quality loss",
            "best_for": ["Production", "Cross-platform", "CPU optimization"],
            "code": onnx_code
        })
        
        # 4-bit for GPU
        if target_device == "gpu":
            fourbit_code = f"""from transformers import AutoModelForCausalLM, BitsAndBytesConfig
import torch

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True  # Nested quantization
)

model = AutoModelForCausalLM.from_pretrained(
    "{model_id}",
    quantization_config=bnb_config,
    device_map="auto"
)"""
            options.append({
                "method": "4-bit (bitsandbytes NF4)",
                "description": "4-bit quantization using NormalFloat4",
                "size_reduction": "~4x smaller",
                "speed_improvement": "2-3x faster, much less VRAM",
                "quality_impact": "Some quality loss, use QLoRA for fine-tuning",
                "best_for": ["Consumer GPUs", "Fine-tuning large models"],
                "code": fourbit_code
            })
        
        # Recommendation based on device
        recommendations = {
            "cpu": "GGUF or ONNX for best CPU performance",
            "gpu": "INT8 for minimal quality loss, 4-bit for maximum VRAM savings",
            "edge": "GGUF with Q4_K_M for best size/quality balance",
            "mobile": "ONNX with quantization, or Core ML for iOS"
        }
        
        return {
            "model_id": model_id,
            "target_device": target_device,
            "original_size_mb": model_size_mb,
            "options": options,
            "recommendation": recommendations.get(target_device, "ONNX for general use"),
        }

    def recommend_vector_db(
        self,
        use_case: str,
        scale: str = "small",  # small (<100K), medium (<10M), large (>10M)
        features: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Recommend vector database with comparison.
        
        Args:
            use_case: Description of the use case
            scale: small, medium, large
            features: Required features (hybrid search, filtering, etc.)
            
        Returns:
            Dict with recommendations and comparison
        """
        features = features or []
        
        databases = [
            {
                "name": "ChromaDB",
                "type": "Local/Embedded",
                "best_for": "Development, prototyping, small scale",
                "max_scale": "~1M vectors",
                "cost": "Free (open source)",
                "pros": ["Easy setup", "No infrastructure", "Python native"],
                "cons": ["Not for production scale", "Single machine only"],
                "setup_code": """import chromadb

client = chromadb.Client()
collection = client.create_collection("my_collection")

# Add embeddings
collection.add(
    embeddings=[[1.0, 2.0, 3.0]],
    documents=["doc1"],
    ids=["id1"]
)

# Query
results = collection.query(query_embeddings=[[1.0, 2.0, 3.0]], n_results=5)"""
            },
            {
                "name": "Pinecone",
                "type": "Managed Cloud",
                "best_for": "Production, serverless, easy scaling",
                "max_scale": "Billions of vectors",
                "cost": "Free tier available, then ~$70/month+",
                "pros": ["Fully managed", "Fast", "Great DX", "Serverless"],
                "cons": ["Vendor lock-in", "Can get expensive at scale"],
                "setup_code": """from pinecone import Pinecone

pc = Pinecone(api_key="your-api-key")
index = pc.Index("my-index")

# Upsert vectors
index.upsert(vectors=[
    {"id": "id1", "values": [1.0, 2.0, 3.0], "metadata": {"text": "doc1"}}
])

# Query
results = index.query(vector=[1.0, 2.0, 3.0], top_k=5, include_metadata=True)"""
            },
            {
                "name": "Weaviate",
                "type": "Self-hosted or Cloud",
                "best_for": "Hybrid search, GraphQL, multi-modal",
                "max_scale": "Billions of vectors",
                "cost": "Free (self-hosted) or cloud pricing",
                "pros": ["Hybrid search", "GraphQL", "Multi-modal", "Built-in vectorization"],
                "cons": ["More complex setup", "Resource intensive"],
                "setup_code": """import weaviate

client = weaviate.Client("http://localhost:8080")

# Create schema
client.schema.create_class({
    "class": "Document",
    "vectorizer": "text2vec-transformers"
})

# Add data
client.data_object.create({"content": "doc1"}, "Document")

# Query (hybrid search)
results = client.query.get("Document", ["content"]).with_hybrid(query="search").do()"""
            },
            {
                "name": "Qdrant",
                "type": "Self-hosted or Cloud",
                "best_for": "High performance, Rust-based, filtering",
                "max_scale": "Billions of vectors",
                "cost": "Free (self-hosted) or cloud pricing",
                "pros": ["Very fast", "Rich filtering", "Rust performance", "Easy to scale"],
                "cons": ["Newer, smaller community"],
                "setup_code": """from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

client = QdrantClient("localhost", port=6333)

# Create collection
client.create_collection(
    collection_name="my_collection",
    vectors_config=VectorParams(size=768, distance=Distance.COSINE)
)

# Insert
client.upsert(collection_name="my_collection", points=[
    {"id": 1, "vector": [0.1]*768, "payload": {"text": "doc1"}}
])

# Search with filters
results = client.search(
    collection_name="my_collection",
    query_vector=[0.1]*768,
    limit=5
)"""
            },
            {
                "name": "pgvector",
                "type": "PostgreSQL Extension",
                "best_for": "Existing Postgres users, SQL integration",
                "max_scale": "Millions of vectors",
                "cost": "Free (extension)",
                "pros": ["SQL integration", "Use existing Postgres", "ACID compliance"],
                "cons": ["Slower than dedicated DBs", "Limited scale"],
                "setup_code": """-- Enable extension
CREATE EXTENSION vector;

-- Create table
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT,
    embedding vector(768)
);

-- Insert
INSERT INTO documents (content, embedding) VALUES ('doc1', '[0.1, 0.2, ...]');

-- Query
SELECT * FROM documents ORDER BY embedding <=> '[0.1, 0.2, ...]' LIMIT 5;"""
            }
        ]
        
        # Score and rank based on requirements
        def score_db(db):
            score = 0
            
            # Scale matching
            if scale == "small" and db["name"] in ["ChromaDB", "pgvector"]:
                score += 3
            elif scale == "medium":
                score += 2 if db["name"] in ["Qdrant", "Weaviate", "Pinecone"] else 1
            elif scale == "large":
                score += 3 if db["name"] in ["Pinecone", "Qdrant", "Weaviate"] else 0
            
            # Feature matching
            if "hybrid" in features and db["name"] == "Weaviate":
                score += 2
            if "serverless" in features and db["name"] == "Pinecone":
                score += 2
            if "sql" in features and db["name"] == "pgvector":
                score += 2
            if "self-hosted" in features and db["name"] in ["Qdrant", "Weaviate", "ChromaDB"]:
                score += 2
                
            return score
        
        ranked = sorted(databases, key=score_db, reverse=True)
        
        features_str = ", ".join(features) if features else ""
        reason = f"Best match for {scale} scale"
        if features_str:
            reason += f" with {features_str}"
        
        return {
            "use_case": use_case,
            "scale": scale,
            "features": features,
            "recommendation": ranked[0]["name"],
            "recommendation_reason": reason,
            "all_options": ranked,
            "comparison_table": {
                "headers": ["Database", "Type", "Best For", "Cost"],
                "rows": [[db["name"], db["type"], db["best_for"], db["cost"]] for db in ranked]
            }
        }

    def calculate_hosting_costs(
        self,
        model_size_mb: float,
        requests_per_month: int = 100000,
        avg_latency_target_ms: int = 200
    ) -> Dict[str, Any]:
        """
        Calculate estimated hosting costs across providers.
        
        Args:
            model_size_mb: Model size in MB
            requests_per_month: Expected monthly requests
            avg_latency_target_ms: Target latency in ms
            
        Returns:
            Dict with cost estimates for different providers
        """
        # Estimate GPU needs based on model size
        if model_size_mb < 500:
            gpu_tier = "cpu_or_small_gpu"
            min_gpu = "None (CPU viable)"
            recommended_gpu = "T4 or CPU"
        elif model_size_mb < 2000:
            gpu_tier = "mid_gpu"
            min_gpu = "T4 (16GB)"
            recommended_gpu = "A10G (24GB)"
        elif model_size_mb < 8000:
            gpu_tier = "large_gpu"
            min_gpu = "A10G (24GB)"
            recommended_gpu = "A100 (40GB)"
        else:
            gpu_tier = "multi_gpu"
            min_gpu = "A100 (40GB)"
            recommended_gpu = "A100 (80GB) or multi-GPU"
        
        # Cost estimates (approximate, varies by region and commitment)
        providers = [
            {
                "provider": "Modal.com",
                "type": "Serverless GPU",
                "pricing_model": "Pay per second",
                "cpu_cost": "$0.000016/sec (~$0.06/hr)",
                "gpu_cost": {
                    "T4": "$0.000164/sec (~$0.59/hr)",
                    "A10G": "$0.000306/sec (~$1.10/hr)",
                    "A100": "$0.001036/sec (~$3.73/hr)"
                },
                "estimated_monthly": self._estimate_modal_cost(requests_per_month, model_size_mb, avg_latency_target_ms),
                "pros": ["No cold start after warm", "Auto-scaling", "Simple deployment"],
                "cons": ["Cold starts for infrequent use", "Less control"],
                "best_for": "Variable workloads, quick deployment"
            },
            {
                "provider": "Replicate",
                "type": "Serverless GPU",
                "pricing_model": "Pay per second",
                "cpu_cost": "N/A",
                "gpu_cost": {
                    "T4": "~$0.00055/sec (~$2/hr)",
                    "A40": "~$0.00115/sec (~$4.14/hr)",
                    "A100": "~$0.0023/sec (~$8.28/hr)"
                },
                "estimated_monthly": self._estimate_replicate_cost(requests_per_month, model_size_mb, avg_latency_target_ms),
                "pros": ["Large model library", "Easy to use"],
                "cons": ["More expensive", "Cold starts"],
                "best_for": "Pre-built models, prototyping"
            },
            {
                "provider": "AWS (SageMaker)",
                "type": "Managed ML",
                "pricing_model": "Per instance hour",
                "cpu_cost": "ml.t3.medium: ~$0.05/hr",
                "gpu_cost": {
                    "ml.g4dn.xlarge (T4)": "~$0.74/hr",
                    "ml.g5.xlarge (A10G)": "~$1.41/hr",
                    "ml.p4d.24xlarge (A100)": "~$37/hr"
                },
                "estimated_monthly": self._estimate_aws_cost(gpu_tier, requests_per_month),
                "pros": ["Enterprise ready", "Full AWS integration", "Managed scaling"],
                "cons": ["Complex setup", "Can be expensive"],
                "best_for": "Enterprise, AWS ecosystem"
            },
            {
                "provider": "RunPod",
                "type": "GPU Cloud",
                "pricing_model": "Per hour (spot or on-demand)",
                "cpu_cost": "N/A",
                "gpu_cost": {
                    "RTX 4090": "~$0.44-0.74/hr",
                    "A100 (40GB)": "~$1.64-2.19/hr",
                    "H100": "~$3.29-4.39/hr"
                },
                "estimated_monthly": self._estimate_runpod_cost(gpu_tier, requests_per_month),
                "pros": ["Cheapest GPUs", "Spot pricing", "Community models"],
                "cons": ["Less managed", "Spot can be preempted"],
                "best_for": "Budget conscious, development"
            },
            {
                "provider": "Hugging Face Inference Endpoints",
                "type": "Managed ML",
                "pricing_model": "Per hour",
                "cpu_cost": "~$0.06/hr",
                "gpu_cost": {
                    "T4": "~$0.60/hr",
                    "A10G": "~$1.30/hr", 
                    "A100": "~$4.00/hr"
                },
                "estimated_monthly": self._estimate_hf_cost(gpu_tier, requests_per_month),
                "pros": ["Easy Transformers integration", "Auto-scaling option"],
                "cons": ["Limited customization"],
                "best_for": "HuggingFace models, quick deployment"
            }
        ]
        
        # Sort by estimated monthly cost
        providers.sort(key=lambda x: x["estimated_monthly"]["mid"])
        
        return {
            "model_size_mb": model_size_mb,
            "requests_per_month": requests_per_month,
            "latency_target_ms": avg_latency_target_ms,
            "hardware_requirements": {
                "minimum_gpu": min_gpu,
                "recommended_gpu": recommended_gpu
            },
            "providers": providers,
            "recommendation": providers[0]["provider"],
            "recommendation_reason": f"Best value for {requests_per_month:,} requests/month"
        }

    def _estimate_modal_cost(self, requests: int, model_size_mb: float, latency_ms: int) -> Dict[str, float]:
        """Estimate Modal.com monthly cost."""
        # Simplified estimation
        seconds_per_request = latency_ms / 1000 + 0.1  # Add overhead
        total_seconds = requests * seconds_per_request
        
        if model_size_mb < 500:
            rate = 0.06 / 3600  # CPU rate per second
        elif model_size_mb < 2000:
            rate = 0.59 / 3600  # T4 rate
        else:
            rate = 1.10 / 3600  # A10G rate
            
        cost = total_seconds * rate
        return {"low": cost * 0.7, "mid": cost, "high": cost * 1.5}

    def _estimate_replicate_cost(self, requests: int, model_size_mb: float, latency_ms: int) -> Dict[str, float]:
        """Estimate Replicate monthly cost."""
        seconds_per_request = latency_ms / 1000 + 0.2
        total_seconds = requests * seconds_per_request
        
        if model_size_mb < 2000:
            rate = 0.00055
        else:
            rate = 0.00115
            
        cost = total_seconds * rate
        return {"low": cost * 0.7, "mid": cost, "high": cost * 1.5}

    def _estimate_aws_cost(self, gpu_tier: str, requests: int) -> Dict[str, float]:
        """Estimate AWS SageMaker monthly cost."""
        # Assume always-on for simplicity
        hours_per_month = 730
        
        rates = {
            "cpu_or_small_gpu": 0.74,
            "mid_gpu": 1.41,
            "large_gpu": 3.5,
            "multi_gpu": 15
        }
        
        cost = hours_per_month * rates.get(gpu_tier, 1.41)
        return {"low": cost * 0.8, "mid": cost, "high": cost * 1.2}

    def _estimate_runpod_cost(self, gpu_tier: str, requests: int) -> Dict[str, float]:
        """Estimate RunPod monthly cost."""
        hours_per_month = 730
        
        # Spot pricing
        rates = {
            "cpu_or_small_gpu": 0.25,
            "mid_gpu": 0.44,
            "large_gpu": 1.64,
            "multi_gpu": 3.29
        }
        
        cost = hours_per_month * rates.get(gpu_tier, 0.44)
        return {"low": cost * 0.6, "mid": cost, "high": cost * 1.5}

    def _estimate_hf_cost(self, gpu_tier: str, requests: int) -> Dict[str, float]:
        """Estimate Hugging Face Inference Endpoints cost."""
        hours_per_month = 730
        
        rates = {
            "cpu_or_small_gpu": 0.06,
            "mid_gpu": 0.60,
            "large_gpu": 1.30,
            "multi_gpu": 4.00
        }
        
        cost = hours_per_month * rates.get(gpu_tier, 0.60)
        return {"low": cost * 0.8, "mid": cost, "high": cost * 1.2}

    def generate_modal_config(self, model_id: str, gpu: str = "T4") -> str:
        """Generate Modal.com deployment configuration."""
        model_short = model_id.split('/')[-1] if '/' in model_id else model_id
        return f'''"""Modal.com deployment for {model_id}."""
import modal

# Define the image with dependencies
image = modal.Image.debian_slim().pip_install(
    "transformers",
    "torch",
    "accelerate"
)

app = modal.App("{model_short}-server")

@app.cls(
    image=image,
    gpu="{gpu}",
    secrets=[modal.Secret.from_name("huggingface-token")],  # If needed
    container_idle_timeout=300,  # Keep warm for 5 minutes
)
class Model:
    @modal.enter()
    def load_model(self):
        from transformers import pipeline
        self.pipe = pipeline("feature-extraction", model="{model_id}")
    
    @modal.method()
    def predict(self, text: str):
        return self.pipe(text)

@app.local_entrypoint()
def main():
    model = Model()
    result = model.predict.remote("Hello, world!")
    print(result)

# Deploy with: modal deploy {model_short}_modal.py
# Run locally: modal run {model_short}_modal.py
'''

    def generate_rag_pipeline(
        self,
        embedding_model: str,
        vector_db: str = "chromadb",
        framework: str = "langchain"
    ) -> str:
        """Generate LangChain/LlamaIndex RAG pipeline code."""
        if framework == "langchain":
            if vector_db == "chromadb":
                return f'''"""RAG Pipeline using LangChain + ChromaDB + {embedding_model}."""
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# 1. Initialize embeddings
embeddings = HuggingFaceEmbeddings(model_name="{embedding_model}")

# 2. Load and split documents
loader = TextLoader("your_document.txt")
documents = loader.load()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
splits = text_splitter.split_documents(documents)

# 3. Create vector store
vectorstore = Chroma.from_documents(
    documents=splits,
    embedding=embeddings,
    persist_directory="./chroma_db"
)

# 4. Create retriever
retriever = vectorstore.as_retriever(search_kwargs={{"k": 5}})

# 5. Create RAG chain (add your LLM here)
# from langchain_openai import ChatOpenAI
# llm = ChatOpenAI(model="gpt-4")

template = """Answer based on the following context:
{{context}}

Question: {{question}}
"""
prompt = ChatPromptTemplate.from_template(template)

# rag_chain = (
#     {{"context": retriever, "question": RunnablePassthrough()}}
#     | prompt
#     | llm
#     | StrOutputParser()
# )

# Query
# result = rag_chain.invoke("Your question here")
results = retriever.invoke("Your question here")
print(results)
'''
            elif vector_db == "pinecone":
                return f'''"""RAG Pipeline using LangChain + Pinecone + {embedding_model}."""
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os

# Set Pinecone API key
os.environ["PINECONE_API_KEY"] = "your-api-key"

# 1. Initialize embeddings
embeddings = HuggingFaceEmbeddings(model_name="{embedding_model}")

# 2. Load and split documents
loader = TextLoader("your_document.txt")
documents = loader.load()

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200
)
splits = text_splitter.split_documents(documents)

# 3. Create/connect to Pinecone index
vectorstore = PineconeVectorStore.from_documents(
    documents=splits,
    embedding=embeddings,
    index_name="my-rag-index"
)

# 4. Query
retriever = vectorstore.as_retriever(search_kwargs={{"k": 5}})
results = retriever.invoke("Your question here")
print(results)
'''
            else:
                return f'''"""RAG Pipeline using LangChain + {vector_db} + {embedding_model}."""
# See documentation for {vector_db} integration with LangChain
'''
        else:  # llamaindex
            return f'''"""RAG Pipeline using LlamaIndex + {embedding_model}."""
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# 1. Initialize embedding model
embed_model = HuggingFaceEmbedding(model_name="{embedding_model}")

# 2. Load documents
documents = SimpleDirectoryReader("./data").load_data()

# 3. Create index
index = VectorStoreIndex.from_documents(
    documents,
    embed_model=embed_model
)

# 4. Create query engine
query_engine = index.as_query_engine()

# 5. Query
response = query_engine.query("Your question here")
print(response)
'''
