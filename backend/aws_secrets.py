import boto3
import json
import os

_cache = {}   # Module-level cache: we only call Secrets Manager once per Lambda cold start


def get_secret(secret_name: str) -> dict:
    """
    Retrieve a secret from AWS Secrets Manager and return it as a Python dict.
    Results are cached in memory for the lifetime of the Lambda execution environment,
    so repeated calls within the same invocation do not incur additional latency.
    """
    if secret_name in _cache:
        return _cache[secret_name]

    region = os.getenv("AWS_REGION", "us-east-1")
    # AWS automatically sets AWS_REGION on Lambda. The fallback is for local testing.

    client = boto3.client("secretsmanager", region_name=region)

    try:
        response = client.get_secret_value(SecretId=secret_name)

        # SecretString is a JSON-encoded string - parse it into a Python dict
        secret_string = response["SecretString"]
        secret_dict = json.loads(secret_string)

        _cache[secret_name] = secret_dict
        return secret_dict

    except Exception as e:
        print(f"Warning: could not retrieve secret '{secret_name}': {e}")
        return {}
