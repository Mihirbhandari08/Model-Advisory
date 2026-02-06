"""Constraint Extraction Agent using Gemini 2.5 Flash."""
import google.generativeai as genai
import json
import time
from typing import Dict, Any, Optional
from pathlib import Path

from config import GEMINI_API_KEY, GEMINI_MODEL
from models.schemas import Constraints
from logger import logger
from metrics import metrics


class ConstraintExtractor:
    """Extract structured constraints from natural language queries using Gemini."""
    
    def __init__(self):
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel(GEMINI_MODEL)
        else:
            self.model = None
        
        # Load prompt template
        prompt_path = Path(__file__).parent.parent / "prompts" / "constraint_extraction_prompt.md"
        if prompt_path.exists():
            self.prompt_template = prompt_path.read_text()
        else:
            self.prompt_template = self._default_prompt()
    
    def _default_prompt(self) -> str:
        return """You are an AI model recommendation expert. Extract structured constraints from the user's query.

Given a user query about AI/ML model needs, extract the following fields:
- primary_task: The main task type (text-generation, text-embedding, text-classification, image-generation, etc.)
- sub_task: Specific sub-task if mentioned (retrieval, sentiment, summarization, etc.)
- deployment_environment: Where they want to deploy (local, cloud, edge, mobile, server)
- hardware_constraint: Any VRAM/RAM/GPU constraints mentioned (e.g., "8GB VRAM", "CPU only")
- license_requirement: License needs (open-source, commercial, any)
- performance_priority: What they prioritize (speed, quality, balanced, cost)
- language_requirement: Languages needed (en, multilingual, specific languages)
- domain_specificity: Specific domain (legal, medical, code, enterprise, etc.)
- use_case_context: The broader context of their use case
- budget_constraint: Any budget mentions
- batch_size: Volume/batch size if mentioned (1M docs, real-time, etc.)

User Query: {query}

Respond with ONLY a valid JSON object, no markdown:
{example_output}"""

    async def extract(self, query: str) -> Constraints:
        """
        Extract constraints from user query.
        
        Args:
            query: Natural language query from user
            
        Returns:
            Constraints object with extracted fields
        """
        if not self.model:
            # Return defaults if no Gemini API key
            return self._extract_basic(query)
        
        prompt = self.prompt_template.format(query=query)
        
        try:
            start_time = time.time()
            response = await self.model.generate_content_async(prompt)
            duration_ms = (time.time() - start_time) * 1000
            text = response.text.strip()
            
            # Estimate tokens
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(text) // 4
            
            # Log and record metrics
            logger.log_llm_call(
                model=GEMINI_MODEL,
                operation="constraint_extraction",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                duration_ms=duration_ms,
                success=True
            )
            metrics.record_llm_call(
                model=GEMINI_MODEL,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                duration_ms=duration_ms,
                success=True
            )
            
            # Clean up response - remove markdown if present
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
                if text.startswith("json"):
                    text = text[4:].strip()
            
            # Try to extract JSON from the response
            text = text.strip()
            
            # Find JSON object in response (might be wrapped in other text)
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                text = text[start_idx:end_idx + 1]
            
            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                # Try to fix common issues
                import re
                # Remove trailing commas
                text = re.sub(r',\s*}', '}', text)
                text = re.sub(r',\s*]', ']', text)
                data = json.loads(text)
            
            logger.log_agent_step(
                agent="ConstraintExtractor",
                step="extract",
                duration_ms=duration_ms,
                success=True,
                details={"primary_task": data.get("primary_task")}
            )
            
            return Constraints(**data)
            
        except Exception as e:
            logger.log_llm_call(
                model=GEMINI_MODEL,
                operation="constraint_extraction",
                duration_ms=(time.time() - start_time) * 1000 if 'start_time' in locals() else 0,
                success=False,
                error=str(e)
            )
            logger.log_agent_step(
                agent="ConstraintExtractor",
                step="extract",
                success=False,
                error=str(e)
            )
            return self._extract_basic(query)
    
    def _extract_basic(self, query: str) -> Constraints:
        """Basic rule-based extraction as fallback."""
        query_lower = query.lower()
        
        constraints = Constraints()
        
        # Task detection
        task_keywords = {
            "embed": "text-embedding",
            "embedding": "text-embedding",
            "vector": "text-embedding",
            "chat": "text-generation",
            "chatbot": "text-generation",
            "generate": "text-generation",
            "llm": "text-generation",
            "classify": "text-classification",
            "sentiment": "text-classification",
            "summarize": "summarization",
            "summary": "summarization",
            "translate": "translation",
            "image": "text-to-image",
            "code": "text-generation",
            "coding": "text-generation",
        }
        
        for keyword, task in task_keywords.items():
            if keyword in query_lower:
                constraints.primary_task = task
                break
        
        # Hardware constraints
        import re
        vram_match = re.search(r'(\d+)\s*gb\s*(vram|gpu|ram)?', query_lower)
        if vram_match:
            constraints.hardware_constraint = f"{vram_match.group(1)}GB VRAM"
        
        # Environment
        if any(word in query_lower for word in ["local", "laptop", "desktop", "offline"]):
            constraints.deployment_environment = "local"
        elif any(word in query_lower for word in ["cloud", "server", "aws", "gcp"]):
            constraints.deployment_environment = "cloud"
        elif any(word in query_lower for word in ["mobile", "phone", "android", "ios"]):
            constraints.deployment_environment = "mobile"
        
        # License
        if any(word in query_lower for word in ["open-source", "open source", "free", "mit", "apache"]):
            constraints.license_requirement = "open-source"
        elif any(word in query_lower for word in ["commercial", "enterprise", "paid"]):
            constraints.license_requirement = "commercial"
        
        # Language
        if "multilingual" in query_lower:
            constraints.language_requirement = "multilingual"
        
        # Priority
        if any(word in query_lower for word in ["fast", "speed", "quick", "real-time"]):
            constraints.performance_priority = "speed"
        elif any(word in query_lower for word in ["accurate", "quality", "best"]):
            constraints.performance_priority = "quality"
        elif any(word in query_lower for word in ["cheap", "budget", "cost"]):
            constraints.performance_priority = "cost"
        
        # Context
        constraints.use_case_context = query[:200]
        
        return constraints
    
    async def refine(self, constraints: Constraints, followup: str) -> Constraints:
        """
        Refine existing constraints based on follow-up query.
        
        Args:
            constraints: Existing constraints
            followup: Follow-up query from user
            
        Returns:
            Updated Constraints object
        """
        if not self.model:
            return constraints
        
        prompt = f"""Given these existing constraints:
{json.dumps(constraints.model_dump(), indent=2)}

And this follow-up request: "{followup}"

Update the constraints accordingly. Only change fields that the follow-up affects.
Return ONLY the updated JSON object, no markdown."""

        try:
            start_time = time.time()
            response = await self.model.generate_content_async(prompt)
            duration_ms = (time.time() - start_time) * 1000
            text = response.text.strip()
            
            # Log LLM call
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(text) // 4
            
            logger.log_llm_call(
                model=GEMINI_MODEL,
                operation="constraint_refinement",
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                duration_ms=duration_ms,
                success=True
            )
            metrics.record_llm_call(
                model=GEMINI_MODEL,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                duration_ms=duration_ms,
                success=True
            )
            
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])
            
            data = json.loads(text)
            
            logger.log_agent_step(
                agent="ConstraintExtractor",
                step="refine",
                duration_ms=duration_ms,
                success=True
            )
            
            return Constraints(**data)
            
        except Exception as e:
            logger.log_llm_call(
                model=GEMINI_MODEL,
                operation="constraint_refinement",
                success=False,
                error=str(e)
            )
            logger.log_agent_step(
                agent="ConstraintExtractor",
                step="refine",
                success=False,
                error=str(e)
            )
            return constraints
