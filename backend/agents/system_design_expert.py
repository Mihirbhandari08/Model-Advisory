"""ML System Design Expert Agent using Gemini 2.5 Flash."""
import google.generativeai as genai
import json
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

from config import GEMINI_API_KEY, GEMINI_MODEL
from logger import logger
from metrics import metrics


class SystemDesignExpert:
    """ML System Design Expert for deployment and infrastructure guidance."""

    def __init__(self):
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel(GEMINI_MODEL)
        else:
            self.model = None
        self.prompt_template = self._load_prompt()

    def _load_prompt(self) -> str:
        """Load system design prompt from file."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "system_design_prompt.md"
        if prompt_path.exists():
            return prompt_path.read_text()
        return self._default_prompt()

    def _default_prompt(self) -> str:
        """Fallback prompt if file not found."""
        return """You are a senior ML system design expert. Help with deployment, 
        infrastructure, quantization, vector DBs, and model optimization.
        Be concise, technical, and include code samples when applicable.
        Return JSON with: answer, code_samples, tradeoffs, alternatives, resources."""

    async def answer(
        self,
        question: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Answer system design questions with model context.
        
        Args:
            question: User's implementation/deployment question
            context: Model info, constraints, hardware specs from session
            
        Returns:
            Structured response with advice, code samples, trade-offs
        """
        start_time = time.time()
        
        # Build context-aware prompt
        model_info = context.get("best_match", {})
        constraints = context.get("constraints", {})
        hardware_specs = context.get("hardware_specs", {})
        
        # Format the prompt with context
        formatted_prompt = self._format_prompt(model_info, constraints, hardware_specs)
        
        full_prompt = f"""{formatted_prompt}

---

## User Question

{question}

---

Respond with valid JSON only. Do not include markdown code fences around the JSON.
"""

        try:
            if self.model:
                # Log the LLM call start
                logger.log_llm_call(
                    model=GEMINI_MODEL,
                    operation="generate_system_design_answer",
                    prompt_tokens=len(full_prompt.split()),
                    completion_tokens=0,
                    duration_ms=0,
                    success=True
                )
                
                response = self.model.generate_content(full_prompt)
                raw_response = response.text.strip()
                
                duration_ms = (time.time() - start_time) * 1000
                
                # Log successful call
                logger.log_agent_step(
                    agent="system_design_expert",
                    step="answer_question",
                    success=True,
                    duration_ms=duration_ms,
                    details={"question": question[:100]}
                )
                
                # Record metrics
                metrics.record_llm_call(
                    model=GEMINI_MODEL,
                    duration_ms=duration_ms,
                    success=True
                )
                
                # Parse JSON response
                parsed = self._parse_response(raw_response)
                parsed["context_summary"] = self._build_context_summary(model_info, constraints)
                parsed["suggested_followups"] = self._generate_followups(question, model_info, constraints)
                
                return parsed
            else:
                # Fallback without LLM
                return self._fallback_response(question, model_info, constraints)
                
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            logger.log_agent_step(
                agent="system_design_expert",
                step="answer_question",
                success=False,
                duration_ms=duration_ms,
                error=str(e)
            )
            metrics.record_llm_call(
                model=GEMINI_MODEL,
                duration_ms=duration_ms,
                success=False
            )
            return self._fallback_response(question, context.get("best_match", {}), context.get("constraints", {}))

    def _format_prompt(
        self,
        model_info: Dict,
        constraints: Dict,
        hardware_specs: Optional[Dict] = None
    ) -> str:
        """Format the prompt template with context values."""
        prompt = self.prompt_template
        
        # Replace placeholders with actual values
        replacements = {
            "{model_id}": model_info.get("model_id", "Not specified"),
            "{size_mb}": str(model_info.get("size_mb", "Unknown")),
            "{vram_required}": model_info.get("vram_required", "Unknown"),
            "{hardware_constraint}": hardware_specs.get("hardware", "") if hardware_specs else constraints.get("hardware_constraint", "Not specified"),
            "{deployment_environment}": constraints.get("deployment_environment", "cloud"),
            "{use_case_context}": constraints.get("use_case_context", "General use"),
            "{budget_constraint}": constraints.get("budget_constraint", "Not specified"),
            "{performance_priority}": constraints.get("performance_priority", "balanced"),
        }
        
        for placeholder, value in replacements.items():
            prompt = prompt.replace(placeholder, str(value))
            
        return prompt

    def _parse_response(self, raw_response: str) -> Dict[str, Any]:
        """Parse the LLM JSON response."""
        try:
            # Clean up response - remove markdown code fences if present
            cleaned = raw_response.strip()
            if cleaned.startswith("```"):
                # Remove code fence
                lines = cleaned.split("\n")
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].strip() == "```":
                    lines = lines[:-1]
                cleaned = "\n".join(lines)
            
            parsed = json.loads(cleaned)
            
            # Ensure required fields exist
            result = {
                "answer": parsed.get("answer", ""),
                "code_samples": parsed.get("code_samples", []),
                "tradeoffs": parsed.get("tradeoffs", []),
                "alternatives": parsed.get("alternatives", []),
                "resources": parsed.get("resources", []),
            }
            
            return result
            
        except json.JSONDecodeError as e:
            logger.warning("SYSTEM_DESIGN", f"Failed to parse JSON response: {e}")
            # Return the raw response as the answer
            return {
                "answer": raw_response,
                "code_samples": [],
                "tradeoffs": [],
                "alternatives": [],
                "resources": [],
            }

    def _build_context_summary(self, model_info: Dict, constraints: Dict) -> str:
        """Build a human-readable context summary."""
        model_name = model_info.get("name", model_info.get("model_id", "Unknown model"))
        deployment = constraints.get("deployment_environment", "cloud")
        hardware = constraints.get("hardware_constraint", "")
        
        parts = [f"Based on your selection of **{model_name}**"]
        
        if deployment:
            parts.append(f"for {deployment} deployment")
        if hardware:
            parts.append(f"with {hardware}")
            
        return " ".join(parts) + "."

    def _generate_followups(
        self,
        question: str,
        model_info: Dict,
        constraints: Dict
    ) -> List[str]:
        """Generate relevant follow-up questions based on the current question."""
        model_name = model_info.get("name", model_info.get("model_id", "this model"))
        deployment = constraints.get("deployment_environment", "cloud")
        
        question_lower = question.lower()
        followups = []
        
        # Context-aware suggestions
        if "deploy" in question_lower:
            followups.extend([
                f"How do I monitor {model_name} in production?",
                "What's the best way to handle scaling?",
                "How do I set up CI/CD for model updates?",
            ])
        elif "vector" in question_lower or "embed" in question_lower:
            followups.extend([
                "How do I build a RAG pipeline with this?",
                "What chunk size should I use for documents?",
                "How do I handle hybrid search?",
            ])
        elif "quantiz" in question_lower:
            followups.extend([
                "What's the accuracy loss after quantization?",
                "Can I further optimize for mobile?",
                "How do I benchmark the quantized model?",
            ])
        elif "fine-tun" in question_lower or "lora" in question_lower:
            followups.extend([
                "How much training data do I need?",
                "What learning rate should I use?",
                "How do I evaluate the fine-tuned model?",
            ])
        else:
            # Generic followups
            followups.extend([
                f"How do I optimize {model_name} for faster inference?",
                "What are the monitoring best practices?",
                f"How do I containerize {model_name}?",
            ])
        
        return followups[:3]  # Return top 3

    def _fallback_response(
        self,
        question: str,
        model_info: Dict,
        constraints: Dict
    ) -> Dict[str, Any]:
        """Generate a fallback response without LLM."""
        model_id = model_info.get("model_id", "the selected model")
        
        # Basic pattern matching for common questions
        question_lower = question.lower()
        
        if "docker" in question_lower or "deploy" in question_lower:
            return {
                "answer": f"To deploy {model_id}, you can use Docker with the Hugging Face transformers library.",
                "code_samples": [{
                    "language": "dockerfile",
                    "filename": "Dockerfile",
                    "description": "Basic Dockerfile for model serving",
                    "code": f"""FROM python:3.10-slim

WORKDIR /app

RUN pip install transformers torch fastapi uvicorn

COPY app.py .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]"""
                }],
                "tradeoffs": [{
                    "approach": "Docker deployment",
                    "pros": ["Portable", "Reproducible", "Easy scaling"],
                    "cons": ["Larger image size", "Need container orchestration for production"]
                }],
                "alternatives": [
                    "Use Modal.com for serverless GPU deployment",
                    "Deploy to Hugging Face Spaces",
                    "Use AWS SageMaker for managed inference"
                ],
                "resources": [
                    {"title": "Hugging Face Docker Guide", "url": "https://huggingface.co/docs/transformers/installation#docker"}
                ],
                "context_summary": self._build_context_summary(model_info, constraints),
                "suggested_followups": self._generate_followups(question, model_info, constraints)
            }
        
        elif "vector" in question_lower:
            return {
                "answer": "For vector databases, the choice depends on your scale and requirements. ChromaDB is great for local development, Pinecone for managed production, and Milvus for self-hosted scale.",
                "code_samples": [{
                    "language": "python",
                    "filename": "vector_db_example.py",
                    "description": "ChromaDB setup example",
                    "code": """import chromadb
from chromadb.utils import embedding_functions

# Initialize ChromaDB
client = chromadb.Client()

# Create collection
collection = client.create_collection(
    name="my_docs",
    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction()
)

# Add documents
collection.add(
    documents=["doc1", "doc2"],
    ids=["id1", "id2"]
)

# Query
results = collection.query(query_texts=["search query"], n_results=5)"""
                }],
                "tradeoffs": [
                    {"approach": "ChromaDB", "pros": ["Free", "Local", "Easy setup"], "cons": ["Not for production scale"]},
                    {"approach": "Pinecone", "pros": ["Managed", "Fast", "Scalable"], "cons": ["Paid service"]},
                ],
                "alternatives": ["Weaviate for hybrid search", "Qdrant for self-hosted", "pgvector if you use PostgreSQL"],
                "resources": [
                    {"title": "ChromaDB Docs", "url": "https://docs.trychroma.com/"},
                    {"title": "Pinecone Docs", "url": "https://docs.pinecone.io/"}
                ],
                "context_summary": self._build_context_summary(model_info, constraints),
                "suggested_followups": self._generate_followups(question, model_info, constraints)
            }
        
        # Generic response
        return {
            "answer": f"I can help with {model_id} implementation. Please note that I'm operating in fallback mode. For detailed guidance, ensure the Gemini API is configured.",
            "code_samples": [],
            "tradeoffs": [],
            "alternatives": [],
            "resources": [
                {"title": "Hugging Face Model Hub", "url": f"https://huggingface.co/{model_id}"}
            ],
            "context_summary": self._build_context_summary(model_info, constraints),
            "suggested_followups": [
                f"How do I deploy {model_id}?",
                "What vector DB should I use?",
                "Can I quantize this model?"
            ]
        }

    async def suggest_questions(self, context: Dict[str, Any]) -> List[str]:
        """
        Generate suggested questions based on the model and context.
        
        Args:
            context: Model info and constraints from session
            
        Returns:
            List of suggested questions
        """
        model_info = context.get("best_match", {})
        constraints = context.get("constraints", {})
        
        model_name = model_info.get("name", model_info.get("model_id", "this model"))
        deployment = constraints.get("deployment_environment", "cloud")
        hardware = constraints.get("hardware_constraint", "")
        task = model_info.get("task", "")
        
        suggestions = []
        
        # Deployment suggestions
        if deployment == "local":
            suggestions.append(f"How do I run {model_name} on my laptop?")
        elif deployment == "edge":
            suggestions.append(f"Can I quantize {model_name} for edge deployment?")
        else:
            suggestions.append(f"What's the cheapest way to host {model_name}?")
        
        # Hardware-specific suggestions
        if hardware and ("4gb" in hardware.lower() or "8gb" in hardware.lower()):
            suggestions.append(f"How do I optimize {model_name} for limited RAM?")
        
        # Task-specific suggestions
        if "embed" in task.lower():
            suggestions.append("What vector DB should I use with this model?")
            suggestions.append("How do I build a RAG pipeline?")
        elif "generation" in task.lower():
            suggestions.append("Should I use LoRA or full fine-tuning?")
            suggestions.append("How do I set up streaming responses?")
        
        # Generic useful suggestions
        suggestions.extend([
            f"How do I containerize {model_name}?",
            "What's the recommended batch size for inference?",
            "How do I monitor model performance in production?",
        ])
        
        # Return unique suggestions, max 5
        seen = set()
        unique = []
        for s in suggestions:
            if s not in seen:
                seen.add(s)
                unique.append(s)
        
        return unique[:5]
