from typing import Dict, Tuple
import numpy as np
import boto3
import json

class ActivitySimilarityEngine:
    def __init__(self, activity_keys):
        self.client = boto3.client("bedrock-runtime")
        self.activity_keys = list(activity_keys)
        self.embeddings = self._embed(self.activity_keys)

    def _embed(self, texts):
        response = self.client.invoke_model(
            modelId="cohere.embed-english-v3",
            body=json.dumps({
                "texts": texts,
                "input_type": "search_document"
            })
        )
        body = json.loads(response["body"].read())
        return np.array(body["embeddings"])

    def find_closest(self, query: str) -> Tuple[str, float]:
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
