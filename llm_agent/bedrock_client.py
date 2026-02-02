import json
import boto3


class BedrockClient:
    def __init__(self, model_id="anthropic.claude-3-sonnet-20240229-v1:0"):
        self.client = boto3.client("bedrock-runtime")
        self.model_id = model_id

    def invoke(self, prompt: str) -> str:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 800,
            "temperature": 0,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        response = self.client.invoke_model(
            modelId=self.model_id,
            body=json.dumps(body)
        )

        response_body = json.loads(response["body"].read())
        return response_body["content"][0]["text"]
