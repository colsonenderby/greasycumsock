# prompt_generator.py

from personality_summaries import personality_summaries

def generate_prompt(personality_key, context_tags):
    """
    Generate a dynamic prompt combining personality and context tags.

    :param personality_key: Key for the AI girlfriend's personality (e.g., "ai.girlfriend.caring").
    :param context_tags: A list of context tags (e.g., ["reassurance", "confidence"]).
    :return: A formatted prompt string for DALL·E 2.
    """
    # Fetch personality summary
    personality_summary = personality_summaries.get(personality_key, "")
    if not personality_summary:
        raise ValueError(f"Personality key '{personality_key}' not found in summaries.")

    # Combine context tags into visual descriptions
    # For testing, assume context_tags are already descriptive enough
    tags_description = ", ".join(context_tags)

    # Construct the prompt
    prompt = (
        f"{personality_summary} "
        f"Reflect the context: '{tags_description}' in the image."
    )

    return prompt

# Example Usage for Testing
if __name__ == "__main__":
    personality_key = "ai.girlfriend.toxic"
    context_tags = ["reassurance", "confidence"]

    prompt = generate_prompt(personality_key, context_tags)
    print(f"Generated Prompt: {prompt}")
