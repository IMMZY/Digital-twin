from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from typing import Optional, List, Dict
import uuid
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from context import prompt
from dynamo_memory import load_conversation, save_conversation
from aws_secrets import get_secret

load_dotenv()

app = FastAPI()

USE_DYNAMODB = os.getenv("USE_DYNAMODB", "false").lower() == "true"
BEDROCK_REGION = os.getenv("BEDROCK_REGION", "us-east-1")
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "global.amazon.nova-2-lite-v1:0")

if USE_DYNAMODB:
    secret_name = os.getenv("SECRET_NAME", "twin/config")
    config = get_secret(secret_name)
    cors_origins = config.get("CORS_ORIGINS", "http://localhost:3000").split(",")
else:
    cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

bedrock_client = boto3.client(
    service_name="bedrock-runtime",
    region_name=BEDROCK_REGION
)


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


def call_bedrock(conversation: List[Dict], user_message: str) -> str:
    messages = []
    for msg in conversation[-50:]:
        messages.append({
            "role": msg["role"],
            "content": [{"text": msg["content"]}]
        })
    messages.append({"role": "user", "content": [{"text": user_message}]})

    try:
        response = bedrock_client.converse(
            modelId=BEDROCK_MODEL_ID,
            system=[{"text": prompt()}],
            messages=messages,
            inferenceConfig={"maxTokens": 2000, "temperature": 0.7, "topP": 0.9}
        )
        return response["output"]["message"]["content"][0]["text"]
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        if error_code == "ValidationException":
            raise HTTPException(status_code=400, detail="Invalid message format for Bedrock")
        elif error_code == "AccessDeniedException":
            raise HTTPException(status_code=403, detail="Access denied to Bedrock model")
        else:
            raise HTTPException(status_code=500, detail=f"Bedrock error: {str(e)}")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "storage": "dynamodb" if USE_DYNAMODB else "local",
        "bedrock_model": BEDROCK_MODEL_ID,
        "workspace": os.getenv("ENVIRONMENT", "local")
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        session_id = request.session_id or str(uuid.uuid4())

        conversation = load_conversation(session_id) if USE_DYNAMODB else []

        assistant_response = call_bedrock(conversation, request.message)

        conversation.append({"role": "user",      "content": request.message,    "timestamp": datetime.now().isoformat()})
        conversation.append({"role": "assistant",  "content": assistant_response, "timestamp": datetime.now().isoformat()})

        if USE_DYNAMODB:
            save_conversation(session_id, conversation)

        return ChatResponse(response=assistant_response, session_id=session_id)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
