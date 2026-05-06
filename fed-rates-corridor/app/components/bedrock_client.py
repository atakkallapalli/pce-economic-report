"""
Amazon Bedrock integration for LLM-powered AI summaries.

Provides a client wrapper around Amazon Bedrock's InvokeModel API
to generate context-aware economic analysis summaries using Claude.
Falls back to template-based summaries when Bedrock is unavailable.
"""

import json
import logging
import os

logger = logging.getLogger(__name__)


def _get_bedrock_client():
    """Get a boto3 Bedrock Runtime client."""
    try:
        import boto3

        region = os.environ.get("AWS_REGION", "us-east-1")
        return boto3.client("bedrock-runtime", region_name=region)
    except ImportError:
        logger.warning("boto3 not installed - Bedrock integration unavailable")
        return None
    except Exception as e:
        logger.warning(f"Failed to create Bedrock client: {e}")
        return None


def invoke_bedrock(prompt: str, max_tokens: int = 2048) -> str:
    """
    Invoke Amazon Bedrock with a prompt and return the response text.

    Uses the model specified by BEDROCK_MODEL_ID environment variable.
    Falls back gracefully if Bedrock is unavailable.

    Args:
        prompt: The prompt to send to the LLM.
        max_tokens: Maximum tokens in the response.

    Returns:
        Generated text from the model, or empty string on failure.
    """
    client = _get_bedrock_client()
    if client is None:
        return ""

    model_id = os.environ.get("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

    try:
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
            }
        )

        response = client.invoke_model(
            modelId=model_id,
            contentType="application/json",
            accept="application/json",
            body=body,
        )

        response_body = json.loads(response["body"].read())
        return response_body.get("content", [{}])[0].get("text", "")

    except Exception as e:
        logger.warning(f"Bedrock invocation failed: {e}")
        return ""


def generate_bedrock_summary(data_context: str, persona: str) -> str:
    """
    Generate an AI summary using Bedrock for the specified persona.

    Args:
        data_context: Formatted string of rate data and statistics.
        persona: One of 'economist', 'executive', 'public'.

    Returns:
        Markdown-formatted summary from the LLM.
    """
    persona_instructions = {
        "economist": (
            "You are an expert monetary economist at the Federal Reserve. "
            "Write a detailed technical analysis of the current policy rate corridor. "
            "Include spread analysis, corridor mechanics, rate positioning relative to "
            "administered rates, and assessment of monetary policy transmission. "
            "Use precise financial terminology. Format as markdown with headers."
        ),
        "executive": (
            "You are briefing a senior Federal Reserve executive (Board Governor level). "
            "Write a concise, action-oriented summary. Lead with the bottom line. "
            "Include a key metrics table, 3-4 bullet observations, and any concerns. "
            "Keep it under 300 words. Format as markdown."
        ),
        "public": (
            "You are explaining Federal Reserve interest rate policy to someone with "
            "no economics background. Use simple analogies and everyday language. "
            "Explain what the rates mean for mortgages, savings accounts, and credit cards. "
            "Avoid jargon. Format as markdown with clear headers."
        ),
    }

    instruction = persona_instructions.get(persona, persona_instructions["economist"])

    prompt = f"""{instruction}

Here is the current Federal Reserve rate corridor data:

{data_context}

Generate a comprehensive summary appropriate for your audience."""

    return invoke_bedrock(prompt)
