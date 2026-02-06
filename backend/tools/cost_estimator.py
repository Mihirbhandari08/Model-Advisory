"""Cost estimation for model deployment options."""
from typing import Dict, List, Optional
from config import COST_DEFAULTS


class CostEstimator:
    """Estimate deployment costs for different hosting options."""
    
    def __init__(self):
        self.costs = COST_DEFAULTS
    
    def estimate_self_hosted(
        self,
        model_size_gb: float,
        monthly_requests: int = 100000,
        avg_tokens_per_request: int = 500
    ) -> Dict:
        """
        Estimate costs for self-hosted deployment.
        
        Args:
            model_size_gb: Model size in GB
            monthly_requests: Expected monthly request volume
            avg_tokens_per_request: Average tokens per request
        
        Returns:
            Cost breakdown dictionary
        """
        # Determine required GPU based on model size
        if model_size_gb <= 4:
            gpu_type = "T4"
            hourly_cost = self.costs["gpu_t4"]
        elif model_size_gb <= 16:
            gpu_type = "A10G"
            hourly_cost = self.costs["gpu_a10"]
        else:
            gpu_type = "A100"
            hourly_cost = self.costs["gpu_a100"]
        
        # Assume 24/7 uptime for production
        monthly_gpu_cost = hourly_cost * 24 * 30
        
        # Add infrastructure overhead (15%)
        total_monthly = monthly_gpu_cost * 1.15
        
        return {
            "deployment_type": "self-hosted",
            "gpu_type": gpu_type,
            "monthly_cost_low": round(total_monthly * 0.8, 2),  # Spot/reserved pricing
            "monthly_cost_high": round(total_monthly, 2),
            "setup_cost": 0,
            "notes": [
                f"Requires {gpu_type} GPU ({model_size_gb:.1f}GB model)",
                "Costs assume 24/7 uptime",
                "Can reduce costs 20-40% with spot instances",
                f"Handles ~{self._estimate_throughput(gpu_type, model_size_gb):,} req/day"
            ]
        }
    
    def estimate_api_usage(
        self,
        provider: str,
        monthly_requests: int = 100000,
        avg_tokens_per_request: int = 500
    ) -> Dict:
        """
        Estimate costs for API-based usage.
        
        Args:
            provider: API provider (openai, gemini, anthropic)
            monthly_requests: Expected monthly requests
            avg_tokens_per_request: Average tokens per request
        
        Returns:
            Cost breakdown dictionary
        """
        # Token costs per 1K tokens (input + output combined estimate)
        api_costs = {
            "openai-gpt4": 0.045,
            "openai-gpt3.5": 0.002,
            "gemini": 0.00,  # Free tier
            "gemini-pro": 0.00035,
            "anthropic-claude": 0.008,
            "anthropic-haiku": 0.0008,
        }
        
        provider_lower = provider.lower()
        cost_per_1k = api_costs.get(provider_lower, 0.002)
        
        total_tokens = monthly_requests * avg_tokens_per_request
        monthly_cost = (total_tokens / 1000) * cost_per_1k
        
        notes = []
        if "gemini" in provider_lower and cost_per_1k == 0:
            notes.append("Free tier - rate limits apply (15 RPM)")
            notes.append("Upgrade to paid for higher limits")
        else:
            notes.append(f"${cost_per_1k:.4f} per 1K tokens")
            notes.append("Scales linearly with usage")
        
        return {
            "deployment_type": "api",
            "provider": provider,
            "monthly_cost_low": round(monthly_cost * 0.7, 2),  # Optimistic
            "monthly_cost_high": round(monthly_cost * 1.3, 2),  # Pessimistic
            "setup_cost": 0,
            "notes": notes
        }
    
    def estimate_cloud_hosted(
        self,
        model_size_gb: float,
        provider: str = "huggingface"
    ) -> Dict:
        """
        Estimate costs for managed cloud hosting (HF Inference Endpoints, etc.)
        
        Args:
            model_size_gb: Model size in GB
            provider: Cloud provider
        
        Returns:
            Cost breakdown dictionary
        """
        # HF Inference Endpoints pricing tiers
        if model_size_gb <= 2:
            tier = "CPU Small"
            hourly = 0.06
        elif model_size_gb <= 8:
            tier = "GPU Small (T4)"
            hourly = 0.60
        elif model_size_gb <= 24:
            tier = "GPU Medium (A10G)"
            hourly = 1.30
        else:
            tier = "GPU Large (A100)"
            hourly = 4.50
        
        monthly_cost = hourly * 24 * 30
        
        return {
            "deployment_type": "managed-cloud",
            "provider": provider,
            "tier": tier,
            "monthly_cost_low": round(monthly_cost * 0.5, 2),  # Scale to zero
            "monthly_cost_high": round(monthly_cost, 2),
            "setup_cost": 0,
            "notes": [
                f"HF Inference Endpoints - {tier}",
                "Can scale to zero when idle (saves ~50%)",
                "Managed infrastructure, no DevOps needed",
                "Automatic model updates available"
            ]
        }
    
    def _estimate_throughput(self, gpu_type: str, model_size_gb: float) -> int:
        """Estimate daily request throughput."""
        base_throughput = {
            "T4": 50000,
            "A10G": 100000,
            "A100": 200000,
        }
        
        throughput = base_throughput.get(gpu_type, 50000)
        # Larger models = slower inference
        size_factor = max(0.2, 1 - (model_size_gb / 50))
        
        return int(throughput * size_factor)
    
    def get_recommendation(
        self,
        model_size_gb: float,
        monthly_requests: int,
        budget_priority: str = "balanced"
    ) -> Dict:
        """
        Get cost recommendation based on requirements.
        
        Args:
            model_size_gb: Model size in GB
            monthly_requests: Expected monthly requests
            budget_priority: cost, quality, balanced
        
        Returns:
            Best deployment recommendation
        """
        self_hosted = self.estimate_self_hosted(model_size_gb, monthly_requests)
        api_gemini = self.estimate_api_usage("gemini", monthly_requests)
        cloud = self.estimate_cloud_hosted(model_size_gb)
        
        options = [
            {"option": self_hosted, "type": "self-hosted"},
            {"option": api_gemini, "type": "api"},
            {"option": cloud, "type": "managed-cloud"},
        ]
        
        if budget_priority == "cost":
            # Sort by lowest cost
            options.sort(key=lambda x: x["option"]["monthly_cost_low"])
        elif budget_priority == "quality":
            # Prefer self-hosted for control
            options.sort(key=lambda x: 0 if x["type"] == "self-hosted" else 1)
        
        return {
            "recommended": options[0]["option"],
            "alternatives": [opt["option"] for opt in options[1:]]
        }
