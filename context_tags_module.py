# context_tags_module.py

import json
import requests
import os

def generate_context_tags(inputs: list) -> dict:
    """
    Generates context tags for multiple inputs (e.g., user input and assistant response).
    
    Args:
        inputs (list): A list of dictionaries with 'role' and 'content' keys.
                       Example:
                       [
                           {'role': 'user', 'content': "I'm feeling lonely."},
                           {'role': 'assistant', 'content': "I'm sorry you're feeling this way. How can I help?"}
                       ]
    
    Returns:
        dict: A dictionary with roles as keys and their respective context tags as values.
              Example:
              {
                  'user': [{'tag': 'emotional support', 'score': -0.8}, {'tag': 'loneliness', 'score': -0.9}],
                  'assistant': [{'tag': 'empathy', 'score': 0.9}, {'tag': 'supportive response', 'score': 0.85}]
              }
    """

    if not inputs:
        return {}

    # 1) Build the system prompt with instructions for each input
    system_prompt = (
        "You are a classifier for conversation context. Based on each input's content and role, "
        "generate 2-3 concise context tags that describe the emotional tone, topic, or intent of the input. "
        "Also, assign an emotional score from -1 (negative) to +1 (positive) for each tag.\n\n"
        "Please output the tags in the following JSON format:\n\n"
        "{\n"
        '    "user": [{"tag": "tag1", "score": score1}, {"tag": "tag2", "score": score2}],\n'
        '    "assistant": [{"tag": "tag1", "score": score1}, {"tag": "tag2", "score": score2}]\n'
        "}\n\n"
        "Ensure that the output is valid JSON."
    )

    # Append each input with its role to the prompt
    for input_item in inputs:
        role = input_item.get('role', 'user').capitalize()
        content = input_item.get('content', '')
        system_prompt += f"{role} Input: '{content}'\nTags and scores:\n"

    # 2) Choose which model to use for context tag generation
    model_name = "gpt-4"  # Using a more standard model

    # 3) Build the messages
    messages = [
        {
            "role": "system",
            "content": system_prompt
        }
    ]

    # 4) Get your API key from environment
    openai_api_key = os.getenv("OPENAI_API_KEY")  # Ensure this is set in your environment
    if not openai_api_key:
        return {}

    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model_name,
        "messages": messages,
        "temperature": 0  # Set temperature to 0 for deterministic output
    }

    url = "https://api.openai.com/v1/chat/completions"

    try:
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        raw_response = data["choices"][0]["message"]["content"].strip()

        # Parse the JSON response
        context_tags_result = json.loads(raw_response)

        return context_tags_result
    except json.JSONDecodeError:
        return {}
    except Exception:
        return {}
