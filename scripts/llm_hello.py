import os
import boto3

model_id = os.getenv("PARSER_MODEL", "us.anthropic.claude-haiku-4-5-20251001-v1:0")

try:
    from anthropic import AnthropicBedrockMantle
    client = AnthropicBedrockMantle(aws_region="us-east-1")
    msg = client.messages.create(
        model=model_id,
        max_tokens=1024,
        messages=[{"role": "user", "content": "In one sentence: what is an ISO week?"}],
    )
    text = next(b.text for b in msg.content if b.type == "text")
    print(f"Response: {text}\n")
    print(f"Stop reason: {msg.stop_reason}")
    print(f"Tokens in: {msg.usage.input_tokens}, out: {msg.usage.output_tokens}")
except Exception as e:
    print(f"Mantle notice ({e}), executing via boto3 converse API...")
    brt = boto3.client("bedrock-runtime", region_name="us-east-1")
    resp = brt.converse(
        modelId=model_id,
        messages=[{"role": "user", "content": [{"text": "In one sentence: what is an ISO week?"}]}],
        inferenceConfig={"maxTokens": 200},
    )
    print("Response:", resp["output"]["message"]["content"][0]["text"])
    print("Usage:", resp["usage"])
