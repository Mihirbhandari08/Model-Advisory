"""Model card aggregator for fetching detailed model metadata."""
import httpx
from typing import Dict, Any, Optional, List
from config import HF_API_TOKEN, HF_API_BASE


class ModelCardAggregator:
    """Fetch and parse model card information from Hugging Face."""
    
    def __init__(self):
        self.base_url = HF_API_BASE
        self.headers = {}
        if HF_API_TOKEN:
            self.headers["Authorization"] = f"Bearer {HF_API_TOKEN}"
    
    async def get_model_card(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch full model card data.
        
        Args:
            model_id: Hugging Face model ID (e.g., 'sentence-transformers/all-MiniLM-L6-v2')
        
        Returns:
            Parsed model card data
        """
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/models/{model_id}",
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                data = response.json()
                
                return self._parse_model_data(data)
            except httpx.HTTPError as e:
                print(f"Error fetching model card for {model_id}: {e}")
                return None
    
    def _parse_model_data(self, data: Dict) -> Dict[str, Any]:
        """Parse raw API response into structured model info."""
        tags = data.get("tags", [])
        
        # Extract languages from tags
        languages = [t.replace("language:", "") for t in tags if t.startswith("language:")]
        
        # Extract license
        license_tag = next((t.replace("license:", "") for t in tags if t.startswith("license:")), "unknown")
        
        # Estimate size from siblings (files)
        size_bytes = 0
        for sibling in data.get("siblings", []):
            if sibling.get("rfilename", "").endswith((".bin", ".safetensors", ".pt")):
                size_bytes += sibling.get("size", 0)
        
        size_mb = size_bytes / (1024 * 1024) if size_bytes else None
        
        return {
            "model_id": data.get("modelId", data.get("id", "")),
            "name": data.get("modelId", "").split("/")[-1],
            "author": data.get("author", ""),
            "task": data.get("pipeline_tag", ""),
            "library": data.get("library_name", ""),
            "downloads": data.get("downloads", 0),
            "likes": data.get("likes", 0),
            "license": license_tag,
            "languages": languages if languages else ["en"],
            "tags": [t for t in tags if not t.startswith(("language:", "license:"))],
            "size_mb": round(size_mb, 2) if size_mb else None,
            "created_at": data.get("createdAt", ""),
            "updated_at": data.get("lastModified", ""),
            "model_card_url": f"https://huggingface.co/{data.get('modelId', '')}",
            "description": self._extract_description(data),
            "config": data.get("config", {}),
        }
    
    def _extract_description(self, data: Dict) -> str:
        """Extract description from model card."""
        # Try to get from card data
        card_data = data.get("cardData", {})
        if card_data:
            desc = card_data.get("model-index", [{}])
            if desc and isinstance(desc, list) and len(desc) > 0:
                return desc[0].get("name", "")
        
        # Fallback to model ID
        return f"Model: {data.get('modelId', 'Unknown')}"
    
    async def get_model_readme(self, model_id: str) -> Optional[str]:
        """Fetch the README/model card markdown."""
        async with httpx.AsyncClient() as client:
            try:
                # Try to get raw README
                response = await client.get(
                    f"https://huggingface.co/{model_id}/raw/main/README.md",
                    headers=self.headers,
                    timeout=30.0
                )
                if response.status_code == 200:
                    return response.text[:5000]  # Limit size
            except httpx.HTTPError:
                pass
        return None
    
    async def get_multiple_cards(self, model_ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch model cards for multiple models."""
        cards = []
        for model_id in model_ids[:10]:  # Limit to 10 to avoid rate limits
            card = await self.get_model_card(model_id)
            if card:
                cards.append(card)
        return cards
    
    def estimate_vram_requirement(self, model_data: Dict) -> str:
        """Estimate VRAM requirement from model data."""
        size_mb = model_data.get("size_mb")
        
        if not size_mb:
            return "Unknown"
        
        size_gb = size_mb / 1024
        
        # Rough estimate: model weights + 20% overhead
        vram_gb = size_gb * 1.2
        
        if vram_gb < 2:
            return "< 2GB (CPU friendly)"
        elif vram_gb < 4:
            return "2-4GB (most GPUs)"
        elif vram_gb < 8:
            return "4-8GB (RTX 3060+)"
        elif vram_gb < 16:
            return "8-16GB (RTX 3090/4090)"
        elif vram_gb < 24:
            return "16-24GB (A10G/A5000)"
        elif vram_gb < 48:
            return "24-48GB (A100-40GB)"
        else:
            return "48GB+ (Multi-GPU required)"
