"""Code generator for model deployment snippets."""
from typing import Dict, Optional


class CodeGenerator:
    """Generate Python code snippets for model deployment."""
    
    TEMPLATES = {
        "transformers": '''# Install: pip install transformers torch

from transformers import AutoTokenizer, AutoModel
import torch

# Load model and tokenizer
model_name = "{model_id}"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)

# Move to GPU if available
device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)

# Example inference
def get_embedding(text: str):
    inputs = tokenizer(text, return_tensors="pt", padding=True, truncation=True)
    inputs = {{k: v.to(device) for k, v in inputs.items()}}
    
    with torch.no_grad():
        outputs = model(**inputs)
    
    # Mean pooling
    embeddings = outputs.last_hidden_state.mean(dim=1)
    return embeddings.cpu().numpy()

# Usage
text = "Hello, world!"
embedding = get_embedding(text)
print(f"Embedding shape: {{embedding.shape}}")
''',
        
        "sentence-transformers": '''# Install: pip install sentence-transformers

from sentence_transformers import SentenceTransformer

# Load model
model = SentenceTransformer("{model_id}")

# Encode sentences
sentences = [
    "This is an example sentence",
    "Each sentence is converted to a vector"
]

embeddings = model.encode(sentences)
print(f"Embeddings shape: {{embeddings.shape}}")

# Compute similarity
from sentence_transformers import util
similarity = util.cos_sim(embeddings[0], embeddings[1])
print(f"Similarity: {{similarity.item():.4f}}")
''',
        
        "text-generation": '''# Install: pip install transformers torch accelerate

from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Load model and tokenizer
model_name = "{model_id}"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    torch_dtype=torch.float16,  # Use FP16 for memory efficiency
    device_map="auto"  # Automatic device placement
)

def generate_text(prompt: str, max_new_tokens: int = 256):
    inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
    
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=True,
            temperature=0.7,
            top_p=0.9,
        )
    
    return tokenizer.decode(outputs[0], skip_special_tokens=True)

# Usage
response = generate_text("Explain quantum computing in simple terms:")
print(response)
''',
        
        "api-inference": '''# Install: pip install huggingface_hub

from huggingface_hub import InferenceClient

# Initialize client (set HF_TOKEN env var or pass token)
client = InferenceClient(model="{model_id}")

# For text generation
response = client.text_generation(
    "Explain quantum computing:",
    max_new_tokens=256,
    temperature=0.7
)
print(response)

# For embeddings
embeddings = client.feature_extraction("Hello, world!")
print(f"Embedding dimension: {{len(embeddings[0])}}")
''',
        
        "fastapi-deployment": '''# Install: pip install fastapi uvicorn transformers torch

from fastapi import FastAPI
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModel
import torch

app = FastAPI()

# Load model at startup
model_name = "{model_id}"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModel.from_pretrained(model_name)
device = "cuda" if torch.cuda.is_available() else "cpu"
model = model.to(device)

class TextInput(BaseModel):
    text: str

@app.post("/embed")
async def get_embedding(input: TextInput):
    inputs = tokenizer(input.text, return_tensors="pt", truncation=True)
    inputs = {{k: v.to(device) for k, v in inputs.items()}}
    
    with torch.no_grad():
        outputs = model(**inputs)
    
    embedding = outputs.last_hidden_state.mean(dim=1).cpu().numpy().tolist()[0]
    return {{"embedding": embedding, "dimension": len(embedding)}}

# Run: uvicorn main:app --host 0.0.0.0 --port 8000
'''
    }
    
    def __init__(self):
        pass
    
    def generate(
        self,
        model_id: str,
        task: str,
        deployment_type: str = "local",
        library: Optional[str] = None
    ) -> str:
        """
        Generate deployment code for a model.
        
        Args:
            model_id: Hugging Face model ID
            task: Model task type
            deployment_type: local, api, fastapi
            library: Preferred library (transformers, sentence-transformers)
        
        Returns:
            Python code snippet
        """
        # Determine best template
        template_key = self._select_template(task, deployment_type, library, model_id)
        template = self.TEMPLATES.get(template_key, self.TEMPLATES["transformers"])
        
        return template.format(model_id=model_id)
    
    def _select_template(
        self,
        task: str,
        deployment_type: str,
        library: Optional[str],
        model_id: str
    ) -> str:
        """Select the best code template."""
        task_lower = task.lower()
        model_lower = model_id.lower()
        
        # Check deployment type first
        if deployment_type == "api":
            return "api-inference"
        elif deployment_type == "fastapi":
            return "fastapi-deployment"
        
        # Check for sentence-transformers models
        if "sentence-transformer" in model_lower or library == "sentence-transformers":
            return "sentence-transformers"
        
        # Check task type
        if task_lower in ("text-generation", "text2text-generation"):
            return "text-generation"
        elif task_lower in ("feature-extraction", "embedding"):
            if "sentence" in model_lower:
                return "sentence-transformers"
            return "transformers"
        
        return "transformers"
    
    def get_requirements(self, template_key: str) -> str:
        """Get pip requirements for a template."""
        requirements = {
            "transformers": "transformers torch",
            "sentence-transformers": "sentence-transformers",
            "text-generation": "transformers torch accelerate",
            "api-inference": "huggingface_hub",
            "fastapi-deployment": "fastapi uvicorn transformers torch",
        }
        return requirements.get(template_key, "transformers torch")
