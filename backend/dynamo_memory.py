import boto3
import os
from datetime import datetime, timedelta
from typing import List, Dict

_dynamodb = None
_table = None   # Cache both the resource object and the Table object


def _get_table():
    """
    Lazily initialise the DynamoDB resource and Table, caching both.
    The Table object is created once per Lambda execution environment
    (cold start) and reused for all subsequent invocations.
    """
    global _dynamodb, _table
    if _table is None:
        _dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
        table_name = os.getenv("DYNAMODB_TABLE", "twin-dev-conversations")
        _table = _dynamodb.Table(table_name)
    return _table


def load_conversation(session_id: str) -> List[Dict]:
    """
    Load the conversation history for a session from DynamoDB.
    Returns an empty list if the session does not exist or any error occurs.
    """
    try:
        table = _get_table()
        response = table.get_item(Key={"session_id": session_id})
        if "Item" in response:
            return response["Item"].get("messages", [])
        return []
    except Exception as e:
        print(f"Error loading conversation from DynamoDB: {e}")
        return []


def save_conversation(session_id: str, messages: List[Dict]) -> None:
    """
    Save the conversation history for a session to DynamoDB.
    Sets a TTL of 30 days so old sessions are automatically cleaned up.
    """
    try:
        table = _get_table()
        ttl_timestamp = int((datetime.utcnow() + timedelta(days=30)).timestamp())

        table.put_item(Item={
            "session_id": session_id,
            "messages": messages,           # boto3 handles list-of-dicts natively
            "updated_at": datetime.utcnow().isoformat(),
            "ttl": ttl_timestamp            # DynamoDB auto-deletes this item after 30 days
        })
    except Exception as e:
        print(f"Error saving conversation to DynamoDB: {e}")
