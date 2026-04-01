"""
Fine-tuning Manager - Manages GPT-4 fine-tuning for industry and business-specific models
Supports industry-level fine-tuning (Option A) with extensibility for business-specific tuning
"""

import logging
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class FineTuningDataGenerator:
    """
    Generates training data for fine-tuning from business information
    Creates properly formatted JSONL files for OpenAI fine-tuning
    """
    
    def __init__(self):
        self.training_data = []
    
    def generate_from_business_data(
        self, 
        business_data: Dict[str, Any],
        industry: str
    ) -> List[Dict[str, Any]]:
        """
        Generate training examples from business data
        
        Args:
            business_data: Complete business information
            industry: Business industry
            
        Returns:
            List of training examples in OpenAI format
        """
        training_examples = []
        
        # Generate examples from FAQs
        if 'faqs' in business_data:
            faq_examples = self._generate_from_faqs(
                business_data['faqs'],
                business_data.get('business_profile', {}),
                industry
            )
            training_examples.extend(faq_examples)
        
        # Generate examples from products/services
        # Handle both new format (products/services) and legacy format (products_services)
        products_services = []
        if 'products_services' in business_data:
            products_services = business_data['products_services']
        else:
            # New format: combine products and services
            products = business_data.get('products', [])
            services = business_data.get('services', [])
            products_services = products + services
        
        if products_services:
            product_examples = self._generate_from_products(
                products_services,
                business_data.get('business_profile', {}),
                industry
            )
            training_examples.extend(product_examples)
        
        # Generate examples from AI context
        if 'ai_context' in business_data:
            context_examples = self._generate_from_ai_context(
                business_data['ai_context'],
                business_data.get('business_profile', {}),
                industry
            )
            training_examples.extend(context_examples)
        
        return training_examples
    
    def _generate_from_faqs(
        self, 
        faqs: List[Dict[str, str]], 
        business_profile: Dict[str, Any],
        industry: str
    ) -> List[Dict[str, Any]]:
        """Generate training examples from FAQs"""
        examples = []
        business_name = business_profile.get('business_name', 'the business')
        
        for faq in faqs:
            example = {
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are a helpful AI assistant for {business_name}, a {industry} business."
                    },
                    {
                        "role": "user",
                        "content": faq.get('question', '')
                    },
                    {
                        "role": "assistant",
                        "content": faq.get('answer', '')
                    }
                ]
            }
            examples.append(example)
        
        return examples
    
    def _generate_from_products(
        self, 
        products: List[Dict[str, Any]], 
        business_profile: Dict[str, Any],
        industry: str
    ) -> List[Dict[str, Any]]:
        """Generate training examples from products/services"""
        examples = []
        business_name = business_profile.get('business_name', 'the business')
        
        for product in products:
            # Product inquiry example
            product_name = product.get('name', 'Unknown Product')
            product_desc = product.get('description', '')
            product_price = product.get('price', 0)
            
            examples.append({
                "messages": [
                    {
                        "role": "system",
                        "content": f"You are a helpful AI assistant for {business_name}, a {industry} business."
                    },
                    {
                        "role": "user",
                        "content": f"Tell me about {product_name}"
                    },
                    {
                        "role": "assistant",
                        "content": f"{product_name}: {product_desc}. The price is ${product_price}."
                    }
                ]
            })
            
            # Pricing inquiry example
            if product_price:
                examples.append({
                    "messages": [
                        {
                            "role": "system",
                            "content": f"You are a helpful AI assistant for {business_name}, a {industry} business."
                        },
                        {
                            "role": "user",
                            "content": f"How much does {product_name} cost?"
                        },
                        {
                            "role": "assistant",
                            "content": f"{product_name} is priced at ${product_price}."
                        }
                    ]
                })
        
        return examples
    
    def _generate_from_ai_context(
        self, 
        ai_context: Dict[str, Any], 
        business_profile: Dict[str, Any],
        industry: str
    ) -> List[Dict[str, Any]]:
        """Generate training examples from AI context"""
        examples = []
        business_name = business_profile.get('business_name', 'the business')
        
        # Value propositions examples
        if 'value_propositions' in ai_context:
            for vp in ai_context['value_propositions']:
                examples.append({
                    "messages": [
                        {
                            "role": "system",
                            "content": f"You are a helpful AI assistant for {business_name}, a {industry} business."
                        },
                        {
                            "role": "user",
                            "content": "What makes your business special?"
                        },
                        {
                            "role": "assistant",
                            "content": vp
                        }
                    ]
                })
        
        return examples
    
    def generate_from_conversations(
        self, 
        conversations: List[Dict[str, Any]],
        business_name: str,
        industry: str
    ) -> List[Dict[str, Any]]:
        """
        Generate training examples from successful conversations
        
        Args:
            conversations: List of customer-AI conversation pairs
            business_name: Name of the business
            industry: Business industry
            
        Returns:
            List of training examples
        """
        examples = []
        
        for conv in conversations:
            if conv.get('success') and conv.get('rating', 0) >= 4:  # Only use highly-rated conversations
                example = {
                    "messages": [
                        {
                            "role": "system",
                            "content": f"You are a helpful AI assistant for {business_name}, a {industry} business."
                        },
                        {
                            "role": "user",
                            "content": conv.get('customer_message', '')
                        },
                        {
                            "role": "assistant",
                            "content": conv.get('ai_response', '')
                        }
                    ]
                }
                examples.append(example)
        
        return examples
    
    def save_to_jsonl(self, examples: List[Dict[str, Any]], filename: str) -> str:
        """
        Save training examples to JSONL file for OpenAI fine-tuning
        
        Args:
            examples: List of training examples
            filename: Output filename (without .jsonl extension)
            
        Returns:
            Path to saved file
        """
        try:
            # Create fine-tuning data directory
            data_dir = Path("./finetuning_data")
            data_dir.mkdir(exist_ok=True)
            
            filepath = data_dir / f"{filename}.jsonl"
            
            with open(filepath, 'w', encoding='utf-8') as f:
                for example in examples:
                    f.write(json.dumps(example) + '\n')
            
            logger.info(f"Saved {len(examples)} training examples to {filepath}")
            return str(filepath)
            
        except Exception as e:
            logger.error(f"Error saving training data: {e}")
            raise


class FineTuningManager:
    """
    Manages OpenAI fine-tuning jobs for industry-specific and business-specific models
    """
    
    def __init__(self):
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if not self.openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable must be set")
        
        self.data_generator = FineTuningDataGenerator()
        self.models_db = {}  # In-memory storage for model info (should use database in production)
    
    def create_industry_finetuning_job(
        self, 
        industry: str, 
        training_file_path: str,
        model: str = "gpt-4-turbo-2024-04-09"
    ) -> Dict[str, Any]:
        """
        Create a fine-tuning job for an industry
        
        Args:
            industry: Industry name
            training_file_path: Path to JSONL training file
            model: Base model to fine-tune
            
        Returns:
            Fine-tuning job information
        """
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            
            # Upload training file
            with open(training_file_path, 'rb') as f:
                uploaded_file = client.files.create(
                    file=f,
                    purpose='fine-tune'
                )
            
            logger.info(f"Uploaded training file: {uploaded_file.id}")
            
            # Create fine-tuning job
            fine_tune_job = client.fine_tuning.jobs.create(
                training_file=uploaded_file.id,
                model=model,
                suffix=f"{industry}-ai"
            )
            
            job_info = {
                "job_id": fine_tune_job.id,
                "industry": industry,
                "model": model,
                "status": fine_tune_job.status,
                "created_at": datetime.now().isoformat(),
                "training_file": uploaded_file.id
            }
            
            # Store job info
            self.models_db[industry] = job_info
            
            logger.info(f"Created fine-tuning job for {industry}: {fine_tune_job.id}")
            
            return {
                "success": True,
                "job_info": job_info
            }
            
        except Exception as e:
            logger.error(f"Error creating fine-tuning job: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def check_finetuning_status(self, job_id: str) -> Dict[str, Any]:
        """
        Check status of a fine-tuning job
        
        Args:
            job_id: Fine-tuning job ID
            
        Returns:
            Job status information
        """
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            
            job = client.fine_tuning.jobs.retrieve(job_id)
            
            return {
                "success": True,
                "job_id": job.id,
                "status": job.status,
                "fine_tuned_model": job.fine_tuned_model,
                "trained_tokens": job.trained_tokens,
                "created_at": job.created_at,
                "finished_at": job.finished_at
            }
            
        except Exception as e:
            logger.error(f"Error checking fine-tuning status: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_industry_model(self, industry: str) -> Optional[str]:
        """
        Get fine-tuned model ID for an industry
        
        Args:
            industry: Industry name
            
        Returns:
            Fine-tuned model ID or None
        """
        if industry in self.models_db:
            job_info = self.models_db[industry]
            if job_info.get('status') == 'succeeded':
                return job_info.get('fine_tuned_model')
        
        return None
    
    def list_finetuning_jobs(self) -> List[Dict[str, Any]]:
        """
        List all fine-tuning jobs
        
        Returns:
            List of job information
        """
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            
            jobs = client.fine_tuning.jobs.list(limit=50)
            
            job_list = []
            for job in jobs.data:
                job_list.append({
                    "job_id": job.id,
                    "model": job.model,
                    "status": job.status,
                    "fine_tuned_model": job.fine_tuned_model,
                    "created_at": job.created_at,
                    "finished_at": job.finished_at
                })
            
            return job_list
            
        except Exception as e:
            logger.error(f"Error listing fine-tuning jobs: {e}")
            return []
    
    def cancel_finetuning_job(self, job_id: str) -> Dict[str, Any]:
        """
        Cancel a fine-tuning job
        
        Args:
            job_id: Job ID to cancel
            
        Returns:
            Cancellation status
        """
        try:
            from openai import OpenAI
            client = OpenAI(api_key=self.openai_api_key)
            
            job = client.fine_tuning.jobs.cancel(job_id)
            
            return {
                "success": True,
                "job_id": job.id,
                "status": job.status
            }
            
        except Exception as e:
            logger.error(f"Error canceling fine-tuning job: {e}")
            return {
                "success": False,
                "error": str(e)
            }


def get_finetuning_manager() -> FineTuningManager:
    """
    Factory function to get fine-tuning manager instance
    
    Returns:
        FineTuningManager instance
    """
    return FineTuningManager()


def get_data_generator() -> FineTuningDataGenerator:
    """
    Factory function to get training data generator
    
    Returns:
        FineTuningDataGenerator instance
    """
    return FineTuningDataGenerator()

