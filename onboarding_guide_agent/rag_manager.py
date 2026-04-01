import os
import json
import uuid
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class RAGManager:
    def __init__(self, db_path: str = "./vectordb"):
        self.db_path = db_path
        
        self.chroma_client = chromadb.PersistentClient(
            path=self.db_path,
            settings=Settings(anonymized_telemetry=False)
        )
        
        # We use standard default embeddings (could swap for OpenAI embeddings inside `.env` if desired)
        self.embedding_func = embedding_functions.DefaultEmbeddingFunction()
        
        # Native FAQ Collections
        self.collection = self.chroma_client.get_or_create_collection(
            name="onboarding_faq", embedding_function=self.embedding_func
        )
        
        # Advanced Continuous Learning Collections
        self.step_resolutions = self.chroma_client.get_or_create_collection(
            name="step_resolutions", embedding_function=self.embedding_func
        )
        self.issue_categories = self.chroma_client.get_or_create_collection(
            name="issue_categories", embedding_function=self.embedding_func
        )
        self.user_segments = self.chroma_client.get_or_create_collection(
            name="user_segments", embedding_function=self.embedding_func
        )
        self.resolution_patterns = self.chroma_client.get_or_create_collection(
            name="resolution_patterns", embedding_function=self.embedding_func
        )
        
    def load_faq_into_db(self, faq_file_path: str):
        """Loads a JSON FAQ file into ChromaDB."""
        try:
            with open(faq_file_path, 'r', encoding='utf-8') as f:
                faqs = json.load(f)
                
            documents = []
            metadatas = []
            ids = []
            
            for key, answer in faqs.items():
                doc_text = f"FAQ Topic: {key.replace('_', ' ')}\nAnswer: {answer}"
                documents.append(doc_text)
                metadatas.append({"intent": key, "source": "platform_faq"})
                ids.append(key)
                
            if documents:
                self.collection.upsert(
                    documents=documents,
                    metadatas=metadatas,
                    ids=ids
                )
            logger.info(f"Loaded {len(documents)} FAQs into RAG Vector DB.")
            
        except FileNotFoundError:
            logger.warning(f"FAQ file {faq_file_path} not found. Ensure it exists.")

    def log_interaction_advanced(self, payload: Dict[str, Any]) -> str:
        """
        Stores advanced interaction metadata across specialized ChromaDB collections.
        """
        conversation_text = ""
        for turn in payload.get("conversation_turns", []):
            role = turn.get("role", "unknown")
            content = turn.get("content", "")
            conversation_text += f"[{role.upper()}]: {content}\n"
            
        resolution_path_str = ", ".join(payload.get("resolution_path", []))
        doc_text = f"Step: {payload.get('step_name')}\nConversation:\n{conversation_text}\nResolution Path: {resolution_path_str}"
        
        unique_id = f"interaction_{str(uuid.uuid4())[:12]}"
        meta_tags = ",".join(payload.get("tags", []))
        
        base_metadata = {
            "step_id": payload.get("step_id", "unknown"),
            "step_name": payload.get("step_name", "unknown"),
            "resolution_time": payload.get("time_to_resolution_seconds", 0),
            "user_satisfaction": payload.get("user_satisfaction_score", 0),
            "tags": meta_tags,
            "session_id": payload.get("session_id", "unknown")
        }
        
        nested_meta = payload.get("metadata", {})
        if "user_experience_level" in nested_meta:
            base_metadata["user_segment"] = nested_meta["user_experience_level"]
        if "issue_category" in nested_meta:
            base_metadata["issue_category"] = nested_meta["issue_category"]
            
        # Store in primary step resolutions
        self.step_resolutions.upsert(
            documents=[doc_text],
            metadatas=[base_metadata],
            ids=[unique_id]
        )
        
        # Distribute into contextual collections if applicable
        if "issue_category" in base_metadata:
            self.issue_categories.upsert(documents=[doc_text], metadatas=[base_metadata], ids=[f"issue_{unique_id}"])
            
        if "user_segment" in base_metadata:
            self.user_segments.upsert(documents=[doc_text], metadatas=[base_metadata], ids=[f"seg_{unique_id}"])
            
        logger.info(f"Advanced Interaction logged successfully: {unique_id}")
        return unique_id

    def search_similar_resolutions(self, query: str, step_id: str = None, user_segment: str = None, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Advanced Continuous Learning retrieval mapping. Filters for high satisfaction resolutions.
        """
        if self.step_resolutions.count() == 0:
            return []
            
        where_filter = {}
        if step_id and user_segment:
            where_filter = {"$and": [{"step_id": step_id}, {"user_segment": user_segment}]}
        elif step_id:
            where_filter = {"step_id": step_id}
        elif user_segment:
            where_filter = {"user_segment": user_segment}
            
        kwargs = {"query_texts": [query], "n_results": limit}
        if where_filter:
            kwargs["where"] = where_filter
            
        results = self.step_resolutions.query(**kwargs)
        
        formatted_results = []
        if results['documents'] and results['documents'][0]:
            for idx, doc in enumerate(results['documents'][0]):
                meta = results['metadatas'][0][idx] if results['metadatas'] else {}
                dist = results['distances'][0][idx] if results['distances'] else 0.0
                
                # Dynamic filter for effectiveness score
                if meta.get("user_satisfaction", 0) >= 4:
                    formatted_results.append({
                        "interaction_id": results['ids'][0][idx],
                        "similarity_score": round(1.0 - dist, 2),
                        "resolution_summary": "Retrieved successful resolution strategy.",
                        "time_to_resolution": meta.get("resolution_time", 0),
                        "user_satisfaction": meta.get("user_satisfaction", 0),
                        "full_text": doc
                    })
        return formatted_results

    def search_faq(self, query: str, n_results: int = 1) -> str:
        """Basic fallback FAQ retrieve."""
        retrieved_contexts = []
        if self.collection.count() > 0:
            faq_results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            if faq_results['documents'] and faq_results['documents'][0]:
                retrieved_contexts.extend(list(faq_results['documents'][0]))
                
        if not retrieved_contexts:
            return ""
        return "\n\n".join(retrieved_contexts)

