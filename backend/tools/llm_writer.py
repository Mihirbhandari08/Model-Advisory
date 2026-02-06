"""LLM Writer using Gemini 2.5 Flash for generating formatted outputs."""
import google.generativeai as genai
from typing import Dict, List, Any, Optional
import json
import time
from config import GEMINI_API_KEY, GEMINI_MODEL
from logger import logger
from metrics import metrics


class LLMWriter:
    """Generate formatted output sections using Gemini 2.5 Flash."""
    
    def __init__(self):
        if GEMINI_API_KEY:
            genai.configure(api_key=GEMINI_API_KEY)
            self.model = genai.GenerativeModel(GEMINI_MODEL)
        else:
            self.model = None
    
    async def generate_tradeoffs(
        self,
        model_info: Dict[str, Any],
        constraints: Dict[str, Any],
        alternatives: List[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Generate honest trade-off analysis."""
        if not self.model:
            return self._fallback_tradeoffs(model_info)
        
        prompt = f"""Analyze the trade-offs for this AI model recommendation.

Model: {model_info.get('model_id', 'Unknown')}
Task: {model_info.get('task', 'general')}
Size: {model_info.get('size_mb', 'unknown')} MB
License: {model_info.get('license', 'unknown')}

User Requirements:
- Task: {constraints.get('primary_task', 'general')}
- Hardware: {constraints.get('hardware_constraint', 'any')}
- Priority: {constraints.get('performance_priority', 'balanced')}
- Environment: {constraints.get('deployment_environment', 'any')}

Provide 3-4 trade-offs in this exact JSON format:
[
  {{"aspect": "Performance vs Size", "pros": ["Fast inference", "Low memory"], "cons": ["May sacrifice accuracy"]}},
  ...
]

Be honest and specific. Only output the JSON array, no markdown."""

        try:
            start_time = time.time()
            response = await self.model.generate_content_async(prompt)
            duration_ms = (time.time() - start_time) * 1000
            text = response.text.strip()
            
            # Log and metrics
            prompt_tokens = len(prompt) // 4
            completion_tokens = len(text) // 4
            
            logger.log_llm_call(
                model=GEMINI_MODEL,
                operation="generate_tradeoffs",
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
            
            # Clean up response
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except Exception as e:
            logger.log_llm_call(
                model=GEMINI_MODEL,
                operation="generate_tradeoffs",
                duration_ms=(time.time() - start_time) * 1000 if 'start_time' in locals() else 0,
                success=False,
                error=str(e)
            )
            print(f"LLM error generating tradeoffs: {e}")
            return self._fallback_tradeoffs(model_info)
    
    async def generate_use_case_fit(
        self,
        model_info: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> str:
        """Generate use case fit analysis."""
        if not self.model:
            return self._fallback_use_case_fit(model_info, constraints)
        
        prompt = f"""Evaluate how well this model fits the user's use case.

Model: {model_info.get('model_id', 'Unknown')}
Task: {model_info.get('task', 'general')}

User's Use Case:
- Primary Task: {constraints.get('primary_task', 'general')}
- Context: {constraints.get('use_case_context', 'general application')}
- Domain: {constraints.get('domain_specificity', 'general')}
- Language: {constraints.get('language_requirement', 'en')}

Write a 2-3 sentence assessment of how well this model fits their needs. 
Be direct and helpful. Start with a fit score (Excellent/Good/Fair/Poor) then explain why."""

        try:
            start_time = time.time()
            response = await self.model.generate_content_async(prompt)
            duration_ms = (time.time() - start_time) * 1000
            text = response.text.strip()
            
            # Log and metrics
            logger.log_llm_call(
                model=GEMINI_MODEL,
                operation="generate_use_case_fit",
                prompt_tokens=len(prompt) // 4,
                completion_tokens=len(text) // 4,
                duration_ms=duration_ms,
                success=True
            )
            metrics.record_llm_call(
                model=GEMINI_MODEL,
                prompt_tokens=len(prompt) // 4,
                completion_tokens=len(text) // 4,
                duration_ms=duration_ms,
                success=True
            )
            
            return text
        except Exception as e:
            logger.log_llm_call(
                model=GEMINI_MODEL,
                operation="generate_use_case_fit",
                duration_ms=(time.time() - start_time) * 1000 if 'start_time' in locals() else 0,
                success=False,
                error=str(e)
            )
            print(f"LLM error generating use case fit: {e}")
            return self._fallback_use_case_fit(model_info, constraints)
    
    async def generate_pro_tips(
        self,
        model_info: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> List[str]:
        """Generate expert pro tips for using the model."""
        if not self.model:
            return self._fallback_pro_tips(model_info)
        
        prompt = f"""Give 3-4 expert pro tips for using this model effectively.

Model: {model_info.get('model_id', 'Unknown')}
Task: {model_info.get('task', 'general')}
User's Environment: {constraints.get('deployment_environment', 'cloud')}
User's Hardware: {constraints.get('hardware_constraint', 'any')}

Provide practical, actionable tips. Return as a JSON array of strings:
["Tip 1", "Tip 2", "Tip 3"]

Only output the JSON array, no markdown."""

        try:
            start_time = time.time()
            response = await self.model.generate_content_async(prompt)
            duration_ms = (time.time() - start_time) * 1000
            text = response.text.strip()
            
            logger.log_llm_call(
                model=GEMINI_MODEL,
                operation="generate_pro_tips",
                prompt_tokens=len(prompt) // 4,
                completion_tokens=len(text) // 4,
                duration_ms=duration_ms,
                success=True
            )
            metrics.record_llm_call(
                model=GEMINI_MODEL,
                prompt_tokens=len(prompt) // 4,
                completion_tokens=len(text) // 4,
                duration_ms=duration_ms,
                success=True
            )

            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except Exception as e:
            logger.log_llm_call(
                model=GEMINI_MODEL,
                operation="generate_pro_tips",
                duration_ms=(time.time() - start_time) * 1000 if 'start_time' in locals() else 0,
                success=False,
                error=str(e)
            )
            print(f"LLM error generating pro tips: {e}")
            return self._fallback_pro_tips(model_info)
    
    async def generate_next_steps(
        self,
        model_info: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> List[str]:
        """Generate actionable next steps."""
        if not self.model:
            return self._fallback_next_steps(model_info)
        
        prompt = f"""Provide 4-5 actionable next steps for someone who wants to use this model.

Model: {model_info.get('model_id', 'Unknown')}
Deployment: {constraints.get('deployment_environment', 'cloud')}

Return as a JSON array of action items:
["Step 1: ...", "Step 2: ..."]

Make them specific and ordered. Only output the JSON array."""

        try:
            start_time = time.time()
            response = await self.model.generate_content_async(prompt)
            duration_ms = (time.time() - start_time) * 1000
            text = response.text.strip()
            
            logger.log_llm_call(
                model=GEMINI_MODEL,
                operation="generate_next_steps",
                prompt_tokens=len(prompt) // 4,
                completion_tokens=len(text) // 4,
                duration_ms=duration_ms,
                success=True
            )
            metrics.record_llm_call(
                model=GEMINI_MODEL,
                prompt_tokens=len(prompt) // 4,
                completion_tokens=len(text) // 4,
                duration_ms=duration_ms,
                success=True
            )

            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            return json.loads(text)
        except Exception as e:
            logger.log_llm_call(
                model=GEMINI_MODEL,
                operation="generate_next_steps",
                duration_ms=(time.time() - start_time) * 1000 if 'start_time' in locals() else 0,
                success=False,
                error=str(e)
            )
            print(f"LLM error generating next steps: {e}")
            return self._fallback_next_steps(model_info)
    
    async def generate_reality_check(
        self,
        model_info: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate reality check table data."""
        return {
            "model_size": f"{model_info.get('size_mb', 'Unknown')} MB",
            "vram_required": model_info.get('vram_required', 'Unknown'),
            "license": model_info.get('license', 'Unknown'),
            "languages": ", ".join(model_info.get('languages', ['en'])),
            "task_match": "✅ Yes" if constraints.get('primary_task', '').lower() in model_info.get('task', '').lower() else "⚠️ Partial",
            "hardware_compatible": self._check_hardware_compatibility(model_info, constraints),
            "production_ready": "✅ Yes" if model_info.get('downloads', 0) > 10000 else "⚠️ Evaluate",
        }
    
    def _check_hardware_compatibility(self, model_info: Dict, constraints: Dict) -> str:
        """Check if model fits hardware constraints."""
        hardware = constraints.get('hardware_constraint', '')
        size_mb = model_info.get('size_mb', 0)
        
        if not hardware or not size_mb:
            return "❓ Check manually"
        
        # Parse VRAM from constraint
        if 'gb' in hardware.lower():
            import re
            match = re.search(r'(\d+)', hardware)
            if match:
                vram_gb = int(match.group(1))
                required_vram = (size_mb / 1024) * 1.2  # Model size + 20%
                
                if required_vram <= vram_gb:
                    return "✅ Compatible"
                else:
                    return f"❌ Needs ~{required_vram:.1f}GB"
        
        return "❓ Check manually"
    
    # Fallback methods for when Gemini is not available
    def _fallback_tradeoffs(self, model_info: Dict) -> List[Dict]:
        return [
            {
                "aspect": "Performance vs Size",
                "pros": ["Reasonable inference speed"],
                "cons": ["Larger models may be more accurate"]
            },
            {
                "aspect": "Ease of Use",
                "pros": ["Standard Hugging Face integration"],
                "cons": ["May require fine-tuning for specific domains"]
            }
        ]
    
    def _fallback_use_case_fit(self, model_info: Dict, constraints: Dict) -> str:
        task = model_info.get('task', 'general')
        return f"Good fit for {task} tasks. Review the model card for specific capabilities and limitations."
    
    def _fallback_pro_tips(self, model_info: Dict) -> List[str]:
        return [
            "Start with the default configuration before tuning",
            "Use batch processing for better throughput",
            "Consider quantization for production deployment",
            "Monitor memory usage during inference"
        ]
    
    def _fallback_next_steps(self, model_info: Dict) -> List[str]:
        model_id = model_info.get('model_id', 'the model')
        return [
            f"Install dependencies: pip install transformers torch",
            f"Review the model card at huggingface.co/{model_id}",
            "Run the provided code snippet locally",
            "Evaluate on your specific dataset",
            "Set up monitoring for production deployment"
        ]
