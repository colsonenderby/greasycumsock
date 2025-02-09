# jsonl_finalizing.py

import os
import json
from pathlib import Path
from style_prompts_module import style_prompts  # Import the refined prompts

def add_prefix_to_style(style: str, prefix: str = "ai.girlfriend.") -> str:
    """
    Adds a prefix to the style if it's not already present.

    Parameters:
    - style (str): The original style string.
    - prefix (str): The prefix to add.

    Returns:
    - str: The updated style string.
    """
    if not style.startswith(prefix):
        return f"{prefix}{style}"
    return style

# Define mapping of old style names to new ones
old_to_new_styles = {
    "ai.girlfriend.Basic-Bitch": "ai.girlfriend.basic",
    "ai.girlfriend.Basic_Bitch": "ai.girlfriend.basic",
    "ai.girlfriend.ghetto": "ai.girlfriend.hood",
    "ai.girlfriend.dumb": "ai.girlfriend.simple",  # Note typo in 'girfriend'
    "ai.girlfriend.Shy": "ai.girlfriend.shy",
    "ai.girlfriend.country_girl": "ai.girlfriend.country",
    "ai_athena.wife.colsons_wife": "ai.girlfriend.athena"
}

def get_system_prompt(style: str) -> str:
    """
    Retrieves the full system prompt based on the style.

    Parameters:
    - style (str): The style of the AI girlfriend.

    Returns:
    - str: The full system prompt string.
    """
    return style_prompts.get(style, "")

def split_conversation(messages: list, max_interactions: int = 25) -> list:
    """
    Splits a list of messages into multiple lists, each ending with an assistant message and containing up to max_interactions messages.

    Parameters:
    - messages (list): The list of message dictionaries to split (excluding the system prompt).
    - max_interactions (int): The maximum number of interactions per split.

    Returns:
    - list: A list of split message lists.
    """
    splits = []
    current_split = []
    interaction_count = 0

    for msg in messages:
        current_split.append(msg)
        interaction_count += 1

        if interaction_count >= max_interactions:
            # Check if the last message is from the assistant
            if msg['role'] == 'assistant':
                splits.append(current_split)
                current_split = []
                interaction_count = 0
            else:
                # Find the last assistant message in the current_split
                for i in range(len(current_split)-1, -1, -1):
                    if current_split[i]['role'] == 'assistant':
                        # Split at this point
                        split_part = current_split[:i+1]
                        splits.append(split_part)
                        # Start the new split with the remaining messages
                        current_split = current_split[i+1:]
                        interaction_count = len(current_split)
                        break
                else:
                    # No assistant message found in current_split, force split
                    splits.append(current_split)
                    current_split = []
                    interaction_count = 0

    # Append any remaining messages as a final split
    if current_split:
        splits.append(current_split)

    return splits

def process_json_file(file_path: Path, prefix: str = "ai.girlfriend.") -> list:
    """
    Processes a single JSON file:
    - Loads the JSON data.
    - Maps old style names to new ones.
    - Retrieves the full system prompt from style_prompts.
    - Splits conversations exceeding max_interactions into multiple conversations.
    - Formats conversations into the desired structure for JSONL.
    - Returns a list of formatted conversations.

    Parameters:
    - file_path (Path): The path to the JSON file.
    - prefix (str): The prefix to add to each style.

    Returns:
    - list: A list of formatted conversation dictionaries suitable for JSONL.
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON in '{file_path.name}': {e}")
        return []
    except Exception as e:
        print(f"Unexpected error reading '{file_path.name}': {e}")
        return []

    if 'conversations' not in data or not isinstance(data['conversations'], list):
        print(f"Skipping '{file_path.name}': 'conversations' key missing or not a list.")
        return []

    formatted_conversations = []

    for convo_idx, conversation in enumerate(data['conversations'], start=1):
        original_style = conversation.get('style', '').strip()
        if not original_style:
            print(f"Conversation {convo_idx} in '{file_path.name}' missing 'style'. Skipping.")
            continue

        # Map old style names to new ones if necessary
        updated_style = old_to_new_styles.get(original_style, original_style)

        # Ensure the style has the prefix
        updated_style = add_prefix_to_style(updated_style, prefix)

        # Retrieve the full system prompt based on the style
        system_prompt = get_system_prompt(updated_style)
        if not system_prompt:
            print(f"Style '{updated_style}' not found in style_prompts. Skipping Conversation {convo_idx} in '{file_path.name}'.")
            continue

        # Initialize the full message list with the system prompt
        original_messages = [
            {"role": "system", "content": system_prompt}
        ]

        convo_messages = conversation.get('conversation', [])
        if not isinstance(convo_messages, list):
            print(f"Conversation {convo_idx} in '{file_path.name}' has invalid 'conversation' format. Skipping.")
            continue

        # Process each message in the conversation
        for msg_idx, msg in enumerate(convo_messages, start=1):
            role = msg.get('role', '').strip()
            content_list = msg.get('content', [])
            if not role or not isinstance(content_list, list):
                print(f"Message {msg_idx} in Conversation {convo_idx} of '{file_path.name}' is malformed. Skipping this message.")
                continue

            # Extract text from content
            text = ""
            for content in content_list:
                if content.get('type') == 'text' and 'text' in content:
                    text = content['text'].strip()
                    break  # Assuming only one text content per message

            if not text:
                print(f"Message {msg_idx} in Conversation {convo_idx} of '{file_path.name}' has no text content. Skipping this message.")
                continue

            # Append the message without adding style information
            original_messages.append({
                "role": role,
                "content": text
            })

        # Exclude the system prompt when counting interactions
        interactions = original_messages[1:]  # Exclude system prompt

        if len(interactions) > 25:
            split_interactions = split_conversation(interactions, max_interactions=25)
            for split_idx, split_msgs in enumerate(split_interactions, start=1):
                # Each split conversation starts with the system prompt
                split_convo = [
                    {"role": "system", "content": system_prompt}
                ] + split_msgs
                formatted_conversations.append({
                    "messages": split_convo
                })
        else:
            # If no split is needed, append the entire conversation
            formatted_conversations.append({
                "messages": original_messages
            })

    return formatted_conversations

def combine_json_files(source_folder: str, output_file: str, prefix: str = "ai.girlfriend.") -> None:
    """
    Combines all JSON files in the source folder into a single JSONL file suitable for OpenAI fine-tuning.

    Parameters:
    - source_folder (str): The path to the folder containing JSON files.
    - output_file (str): The path to the output JSONL file.
    - prefix (str): The prefix to add to each style.
    """
    source_path = Path(source_folder)
    if not source_path.is_dir():
        print(f"Error: The folder '{source_folder}' does not exist or is not a directory.")
        return

    json_files = list(source_path.glob('*.json'))
    if not json_files:
        print(f"No JSON files found in '{source_folder}'.")
        return

    print(f"Found {len(json_files)} JSON file(s) in '{source_folder}'. Processing...")

    all_formatted_conversations = []

    for json_file in json_files:
        print(f"Processing '{json_file.name}'...")
        formatted_convos = process_json_file(json_file, prefix)
        all_formatted_conversations.extend(formatted_convos)

    if not all_formatted_conversations:
        print("No valid conversations found to combine.")
        return

    # Write to JSONL file
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            for convo in all_formatted_conversations:
                json_line = json.dumps(convo, ensure_ascii=False)
                f.write(json_line + '\n')
        print(f"\nSuccessfully combined conversations into '{output_file}'.")
    except Exception as e:
        print(f"Error writing to '{output_file}': {e}")

if __name__ == "__main__":
    # Define the source folder containing JSON files and the output JSONL file path
    source_folder = r"C:\Users\colso\Documents\Side_Bitch\Gpt_Interface\Post processing\json"
    output_jsonl_file = r"C:\Users\colso\Documents\Side_Bitch\Gpt_Interface\Post processing\combined_conversations.jsonl"

    combine_json_files(source_folder, output_jsonl_file)
