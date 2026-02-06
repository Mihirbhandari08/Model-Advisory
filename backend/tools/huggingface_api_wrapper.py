"""Hugging Face API wrapper for searching and filtering models."""
import httpx
from typing import List, Dict, Any, Optional
from config import HF_API_TOKEN, HF_API_BASE


class HuggingFaceAPI:
    """Wrapper for Hugging Face Hub API to search and filter models."""
    
    TASK_MAPPINGS = {
        "text-generation": "text-generation",
        "chat": "text-generation",
        "chatbot": "text-generation",
        "embedding": "feature-extraction",
        "text-embedding": "feature-extraction",
        "embeddings": "feature-extraction",
        "classification": "text-classification",
        "sentiment": "text-classification",
        "ner": "token-classification",
        "named-entity": "token-classification",
        "qa": "question-answering",
        "question-answering": "question-answering",
        "summarization": "summarization",
        "translation": "translation",
        "image-generation": "text-to-image",
        "image": "text-to-image",
        "speech": "automatic-speech-recognition",
        "asr": "automatic-speech-recognition",
        "tts": "text-to-speech",
        "code": "text-generation",
        "coding": "text-generation",
    }
    
    def __init__(self):
        self.base_url = HF_API_BASE
        self.headers = {}
        if HF_API_TOKEN:
            self.headers["Authorization"] = f"Bearer {HF_API_TOKEN}"
    
    def _normalize_task(self, task: str) -> str:
        """Convert user task description to HF pipeline tag."""
        task_lower = task.lower().strip()
        return self.TASK_MAPPINGS.get(task_lower, task_lower)
    
    async def search_models(
        self,
        task: str,
        search_query: str = "",
        limit: int = 20,
        sort: str = "downloads",
        license_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Search for models on Hugging Face.
        
        Args:
            task: Primary task (will be normalized)
            search_query: Additional search terms
            limit: Max number of results
            sort: Sort by (downloads, likes, created)
            license_filter: Filter by license type
        
        Returns:
            List of model metadata dictionaries
        """
        normalized_task = self._normalize_task(task)
        
        params = {
            "pipeline_tag": normalized_task,
            "sort": sort,
            "direction": "-1",
            "limit": limit,
        }
        
        if search_query:
            params["search"] = search_query
            
        if license_filter and license_filter != "any":
            if license_filter == "open-source":
                params["filter"] = "license:mit,license:apache-2.0,license:gpl,license:bsd"
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/models",
                    params=params,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"HF API Error: {e}")
                return []
    
    async def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific model."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/models/{model_id}",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                print(f"HF API Error getting model {model_id}: {e}")
                return None
    
    def filter_by_size(
        self, 
        models: List[Dict[str, Any]], 
        max_size_gb: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Filter models by approximate size in GB."""
        if not max_size_gb:
            return models
            
        filtered = []
        for model in models:
            # Estimate size from model ID patterns
            model_id = model.get("modelId", "").lower()
            estimated_size = self._estimate_model_size(model_id, model)
            if estimated_size <= max_size_gb:
                model["_estimated_size_gb"] = estimated_size
                filtered.append(model)
        
        return filtered
    
    def _estimate_model_size(self, model_id: str, model_data: Dict) -> float:
        """Estimate model size in GB from name patterns."""
        # Common size patterns in model names
        size_patterns = {
            "70b": 140.0, "65b": 130.0, "40b": 80.0,
            "33b": 66.0, "30b": 60.0, "20b": 40.0,
            "13b": 26.0, "7b": 14.0, "6b": 12.0,
            "3b": 6.0, "2b": 4.0, "1b": 2.0,
            "1.5b": 3.0, "0.5b": 1.0, "500m": 1.0,
            "350m": 0.7, "125m": 0.25, "base": 0.5,
            "small": 0.3, "mini": 0.15, "tiny": 0.1,
            "large": 1.5, "xl": 3.0, "xxl": 11.0,
        }
        
        for pattern, size in size_patterns.items():
            if pattern in model_id:
                return size
        
        # Default estimate based on task
        return 2.0  # Conservative default
    
    def filter_by_vram(
        self,
        models: List[Dict[str, Any]],
        max_vram_gb: float
    ) -> List[Dict[str, Any]]:
        """Filter models by VRAM requirement (rough estimate: model_size * 1.2 for inference)."""
        filtered = []
        for model in models:
            model_id = model.get("modelId", "").lower()
            estimated_size = self._estimate_model_size(model_id, model)
            estimated_vram = estimated_size * 1.2  # Add 20% overhead
            
            if estimated_vram <= max_vram_gb:
                model["_estimated_vram_gb"] = estimated_vram
                filtered.append(model)
        
        return filtered
    
    def parse_vram_constraint(self, constraint: str) -> Optional[float]:
        """Parse VRAM constraint string to GB float."""
        if not constraint:
            return None
            
        constraint = constraint.lower().strip()
        
        # Extract number and unit
        import re
        match = re.search(r'(\d+(?:\.\d+)?)\s*(gb|mb|g|m)?', constraint)
        if match:
            value = float(match.group(1))
            unit = match.group(2) or 'gb'
            
            if unit in ('mb', 'm'):
                return value / 1024
            return value
        
        return None
