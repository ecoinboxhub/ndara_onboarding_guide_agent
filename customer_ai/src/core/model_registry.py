"""
Model Registry - Tracks fine-tuned models for industries and businesses.
Manages model versions and deployment status.

Multi-process note: Registry uses a single JSON file with no file locking.
With multiple worker processes (e.g. gunicorn workers), concurrent writes can
corrupt the file or drop updates. For multi-worker deployments, either use a
single worker, or migrate to a database-backed registry.
"""

import logging
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

try:
    from filelock import FileLock
    _filelock_available = True
except ImportError:
    _filelock_available = False

logger = logging.getLogger(__name__)


class ModelRegistry:
    """
    Registry for tracking fine-tuned models.
    Stores model information in JSON file (can be migrated to database).
    Not safe for concurrent writes across processes; see module docstring.
    """
    
    def __init__(self, registry_path: str = "./models_registry.json"):
        """
        Initialize model registry

        Args:
            registry_path: Path to registry JSON file
        """
        self.registry_path = Path(registry_path)
        self._lock_path = str(self.registry_path) + ".lock"
        self._lock = FileLock(self._lock_path, timeout=10) if _filelock_available else None
        self.models = self._load_registry()
    
    def _load_registry(self) -> Dict[str, Any]:
        """Load registry from file (with cross-process file lock if available)."""
        try:
            if self.registry_path.exists():
                if self._lock:
                    with self._lock:
                        with open(self.registry_path, 'r') as f:
                            return json.load(f)
                else:
                    with open(self.registry_path, 'r') as f:
                        return json.load(f)
            else:
                return {
                    "industry_models": {},
                    "business_models": {},
                    "metadata": {
                        "created_at": datetime.now().isoformat(),
                        "last_updated": datetime.now().isoformat()
                    }
                }
        except Exception as e:
            logger.error(f"Error loading registry: {e}")
            return {
                "industry_models": {},
                "business_models": {},
                "metadata": {}
            }

    def _save_registry(self):
        """Save registry to file (with cross-process file lock if available)."""
        try:
            self.models["metadata"]["last_updated"] = datetime.now().isoformat()
            if self._lock:
                with self._lock:
                    with open(self.registry_path, 'w') as f:
                        json.dump(self.models, f, indent=2)
            else:
                with open(self.registry_path, 'w') as f:
                    json.dump(self.models, f, indent=2)
            logger.info(f"Registry saved to {self.registry_path}")
        except Exception as e:
            logger.error(f"Error saving registry: {e}")
    
    def register_industry_model(
        self, 
        industry: str, 
        model_id: str, 
        base_model: str,
        job_id: str,
        training_info: Optional[Dict] = None
    ) -> bool:
        """
        Register a fine-tuned model for an industry
        
        Args:
            industry: Industry name
            model_id: Fine-tuned model ID from OpenAI
            base_model: Base model that was fine-tuned
            job_id: Fine-tuning job ID
            training_info: Optional training information
            
        Returns:
            Success status
        """
        try:
            model_entry = {
                "model_id": model_id,
                "base_model": base_model,
                "job_id": job_id,
                "status": "active",
                "registered_at": datetime.now().isoformat(),
                "training_info": training_info or {},
                "usage_count": 0,
                "businesses_using": []
            }
            
            if industry not in self.models["industry_models"]:
                self.models["industry_models"][industry] = {
                    "current_model": model_id,
                    "versions": []
                }
            
            # Add to versions
            self.models["industry_models"][industry]["versions"].append(model_entry)
            self.models["industry_models"][industry]["current_model"] = model_id
            
            self._save_registry()
            
            logger.info(f"Registered industry model for {industry}: {model_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering industry model: {e}")
            return False
    
    def register_business_model(
        self, 
        business_id: str, 
        model_id: str,
        base_model: str,
        job_id: str,
        training_info: Optional[Dict] = None
    ) -> bool:
        """
        Register a fine-tuned model for a specific business
        
        Args:
            business_id: Business identifier
            model_id: Fine-tuned model ID
            base_model: Base model that was fine-tuned
            job_id: Fine-tuning job ID
            training_info: Optional training information
            
        Returns:
            Success status
        """
        try:
            model_entry = {
                "model_id": model_id,
                "base_model": base_model,
                "job_id": job_id,
                "status": "active",
                "registered_at": datetime.now().isoformat(),
                "training_info": training_info or {},
                "usage_count": 0
            }
            
            if business_id not in self.models["business_models"]:
                self.models["business_models"][business_id] = {
                    "current_model": model_id,
                    "versions": []
                }
            
            # Add to versions
            self.models["business_models"][business_id]["versions"].append(model_entry)
            self.models["business_models"][business_id]["current_model"] = model_id
            
            self._save_registry()
            
            logger.info(f"Registered business model for {business_id}: {model_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error registering business model: {e}")
            return False
    
    def get_industry_model(self, industry: str) -> Optional[str]:
        """
        Get current fine-tuned model for an industry
        
        Args:
            industry: Industry name
            
        Returns:
            Model ID or None
        """
        if industry in self.models["industry_models"]:
            return self.models["industry_models"][industry].get("current_model")
        return None
    
    def get_business_model(self, business_id: str) -> Optional[str]:
        """
        Get current fine-tuned model for a business
        
        Args:
            business_id: Business identifier
            
        Returns:
            Model ID or None
        """
        if business_id in self.models["business_models"]:
            return self.models["business_models"][business_id].get("current_model")
        return None
    
    def get_model_for_request(self, business_id: str, industry: str) -> Dict[str, Any]:
        """
        Get appropriate model for a request (business-specific > industry > base)
        
        Args:
            business_id: Business identifier
            industry: Industry name
            
        Returns:
            Model information with priority order
        """
        # Priority 1: Business-specific model
        business_model = self.get_business_model(business_id)
        if business_model:
            self._increment_usage(business_id, "business")
            return {
                "model_id": business_model,
                "type": "business_specific",
                "business_id": business_id
            }
        
        # Priority 2: Industry model
        industry_model = self.get_industry_model(industry)
        if industry_model:
            self._increment_usage(industry, "industry")
            return {
                "model_id": industry_model,
                "type": "industry_specific",
                "industry": industry
            }
        
        # Priority 3: Base model
        return {
            "model_id": "gpt-4o",
            "type": "base_model"
        }
    
    def _increment_usage(self, identifier: str, model_type: str):
        """Increment usage count for a model"""
        try:
            if model_type == "industry":
                if identifier in self.models["industry_models"]:
                    versions = self.models["industry_models"][identifier]["versions"]
                    if versions:
                        versions[-1]["usage_count"] += 1
                        self._save_registry()
            
            elif model_type == "business":
                if identifier in self.models["business_models"]:
                    versions = self.models["business_models"][identifier]["versions"]
                    if versions:
                        versions[-1]["usage_count"] += 1
                        self._save_registry()
                        
        except Exception as e:
            logger.error(f"Error incrementing usage: {e}")
    
    def deactivate_model(self, model_id: str) -> bool:
        """
        Deactivate a model
        
        Args:
            model_id: Model ID to deactivate
            
        Returns:
            Success status
        """
        try:
            # Search in industry models
            for industry, data in self.models["industry_models"].items():
                for version in data["versions"]:
                    if version["model_id"] == model_id:
                        version["status"] = "inactive"
                        version["deactivated_at"] = datetime.now().isoformat()
                        self._save_registry()
                        return True
            
            # Search in business models
            for business_id, data in self.models["business_models"].items():
                for version in data["versions"]:
                    if version["model_id"] == model_id:
                        version["status"] = "inactive"
                        version["deactivated_at"] = datetime.now().isoformat()
                        self._save_registry()
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error deactivating model: {e}")
            return False
    
    def get_model_info(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a model
        
        Args:
            model_id: Model ID
            
        Returns:
            Model information or None
        """
        # Search in industry models
        for industry, data in self.models["industry_models"].items():
            for version in data["versions"]:
                if version["model_id"] == model_id:
                    return {
                        **version,
                        "type": "industry",
                        "industry": industry
                    }
        
        # Search in business models
        for business_id, data in self.models["business_models"].items():
            for version in data["versions"]:
                if version["model_id"] == model_id:
                    return {
                        **version,
                        "type": "business",
                        "business_id": business_id
                    }
        
        return None
    
    def list_all_models(self) -> Dict[str, List[Dict]]:
        """
        List all registered models
        
        Returns:
            Dictionary with industry and business models
        """
        return {
            "industry_models": [
                {
                    "industry": industry,
                    "current_model": data["current_model"],
                    "versions_count": len(data["versions"])
                }
                for industry, data in self.models["industry_models"].items()
            ],
            "business_models": [
                {
                    "business_id": business_id,
                    "current_model": data["current_model"],
                    "versions_count": len(data["versions"])
                }
                for business_id, data in self.models["business_models"].items()
            ]
        }
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """
        Get usage statistics for all models
        
        Returns:
            Usage statistics
        """
        industry_stats = {}
        for industry, data in self.models["industry_models"].items():
            total_usage = sum(v["usage_count"] for v in data["versions"])
            industry_stats[industry] = {
                "total_usage": total_usage,
                "active_models": sum(1 for v in data["versions"] if v["status"] == "active")
            }
        
        business_stats = {}
        for business_id, data in self.models["business_models"].items():
            total_usage = sum(v["usage_count"] for v in data["versions"])
            business_stats[business_id] = {
                "total_usage": total_usage,
                "active_models": sum(1 for v in data["versions"] if v["status"] == "active")
            }
        
        return {
            "industry_models": industry_stats,
            "business_models": business_stats,
            "total_industry_models": len(self.models["industry_models"]),
            "total_business_models": len(self.models["business_models"])
        }


_model_registry_instance: Optional[ModelRegistry] = None


def get_model_registry(registry_path: str = "./models_registry.json") -> ModelRegistry:
    """
    Factory function to get model registry singleton.

    Args:
        registry_path: Path to registry file

    Returns:
        ModelRegistry instance (singleton)
    """
    global _model_registry_instance
    if _model_registry_instance is None:
        _model_registry_instance = ModelRegistry(registry_path=registry_path)
    return _model_registry_instance

