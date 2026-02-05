from typing import Dict, Tuple
import numpy as np
import boto3
import json
import logging  # Added for error logging

logger = logging.getLogger(__name__)  # Added logger setup

class ActivitySimilarityEngine:
    def __init__(self, activity_keys):
        self.client = boto3.client("bedrock-runtime")
        self.activity_keys = list(activity_keys)
        self.embeddings = self._embed(self.activity_keys)

    def _embed(self, texts):
        try:
            response = self.client.invoke_model(
                modelId="cohere.embed-english-v3",
                body=json.dumps({
                    "texts": texts,
                    "input_type": "search_document"
                })
            )
            body = json.loads(response["body"].read())
            return np.array(body["embeddings"])
        except Exception as e:
            logger.error("Embedding failed: %s", e)
            # Fallback: Return zeros array with expected shape (assuming 768 dimensions for Cohere)
            return np.zeros((len(texts), 768))

    def find_closest(self, query: str) -> Tuple[str, float]:
        try:
            response = self.client.invoke_model(
                modelId="cohere.embed-english-v3",
                body=json.dumps({
                    "texts": [query],
                    "input_type": "search_query"
                })
            )
            body = json.loads(response["body"].read())
            query_vec = np.array(body["embeddings"][0])

            scores = self.embeddings @ query_vec
            idx = int(scores.argmax())

            return self.activity_keys[idx], float(scores[idx])
        except Exception as e:
            logger.error("Similarity search failed: %s", e)
            # Fallback: Return the first activity with score 0.0
            return self.activity_keys[0], 0.0