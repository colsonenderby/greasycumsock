# main.py

import os
import json
import requests
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path
from PIL import Image  # For image processing

# 1) Import the TTS utilities
from tts_module import generate_audio  # Ensure this module is correctly implemented
from context_tags_module import generate_context_tags  # Ensure logging is removed as per previous steps
from style_prompts_module import style_prompts  # Your style dictionary
from image_selector import get_selected_image, DEFAULT_IMAGE_PATH  # Import functions and constants

# Import the email utility to send the JSON data
from email_utils import send_file_via_email

############################################
# 1) ENV / FILE MANAGEMENT
############################################
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    st.error("OPENAI_API_KEY is missing. Please set it in .env or environment.")
    st.stop()

DATA_DIR = "Data"
os.makedirs(DATA_DIR, exist_ok=True)
PROCESSED_INPUTS_FILE = "processed_inputs.json"

def load_processed_inputs():
    if not os.path.exists(PROCESSED_INPUTS_FILE):
        return []
    try:
        with open(PROCESSED_INPUTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def save_processed_input(style: str, user_text: str):
    data = load_processed_inputs()
    if not any(d["style"] == style and d["text"] == user_text for d in data):
        data.append({"style": style, "text": user_text})
        with open(PROCESSED_INPUTS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)

############################################
# 2) Assistant Reply Generation (NEW)
############################################
def call_openai_chatcompletion(dev_prompt: str, short_context: list) -> str:
    """
    Build messages with:
      - system message: dev_prompt 
      - then for each turn in short_context, role= user/assistant, content=the text
    Returns AI's final assistant message text.
    """
    if not dev_prompt:
        dev_prompt = "(no prompt)"
    
    # Fixed model for the assistant reply
    model_name = "ft:gpt-3.5-turbo-0125:personal:bro:AyoqyVN6"

    # Build the messages array
    messages = []
    # 1) system
    messages.append({
        "role": "system",
        "content": dev_prompt
    })

    # 2) short context turns
    for turn in short_context:
        role = turn["role"]  # "user" or "assistant"
        text_content = turn["content"][0]["text"]  # the actual string
        messages.append({
            "role": role,
            "content": text_content
        })

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": messages,
        "max_tokens": 200,  # Limit the response length
        "temperature": 0.9,  # Control randomness
        "top_p": 1.0,  # Nucleus sampling for token range
        "frequency_penalty": 0,  # Penalize repeated tokens
        "presence_penalty": 0  # Encourage diverse responses
    }

    try:
        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        ai_text = data["choices"][0]["message"]["content"].strip()
        return ai_text
    except Exception as e:
        st.error(f"ChatCompletion error: {e}")
    return "(error) ChatCompletion failed."

############################################
# 3) Session Setup
############################################
def reset_conversation():
    st.session_state["messages"] = []
    st.session_state["current_audio"] = None  # Reset current audio
    st.session_state["expanded_images"] = {}  # Reset expanded images

def init_session_state():
    if "messages" not in st.session_state:
        st.session_state["messages"] = []
    if "style" not in st.session_state:
        st.session_state["style"] = "ai.girlfriend.caring"
    # Set the prompt directly from the style dictionary; no manual editing needed now.
    st.session_state["prompt_text"] = style_prompts.get(st.session_state["style"], "")
    if "tts_off" not in st.session_state:
        st.session_state["tts_off"] = False
    if "current_audio" not in st.session_state:
        st.session_state["current_audio"] = None
    # Set the model to the fixed one for assistant replies.
    st.session_state["openai_model"] = "ft:gpt-3.5-turbo-0125:personal:bro:AyoqyVN6"
    if "short_context_length" not in st.session_state:
        st.session_state["short_context_length"] = 4
    if "duplicate_warning" not in st.session_state:
        st.session_state["duplicate_warning"] = False
    if "talking_gif_ms" not in st.session_state:
        st.session_state["talking_gif_ms"] = 0
    if "expanded_images" not in st.session_state:
        st.session_state["expanded_images"] = {}  # To track which images are expanded

############################################
# 4) End & Save
############################################
def on_end_and_save():
    if not st.session_state["messages"]:
        st.info("No conversation to save.")
        return

    style_folder = os.path.join(DATA_DIR, st.session_state["style"])
    os.makedirs(style_folder, exist_ok=True)
    style_file_path = os.path.join(style_folder, "conversations.json")

    if not os.path.exists(style_file_path):
        with open(style_file_path, "w", encoding="utf-8") as f:
            json.dump({"conversations": []}, f)

    with open(style_file_path, "r", encoding="utf-8") as f:
        try:
            existing_data = json.load(f)
        except json.JSONDecodeError:
            existing_data = {"conversations": []}

    if "conversations" not in existing_data:
        existing_data["conversations"] = []
    
    # Prepare messages without 'image_path'
    messages_to_save = []
    for msg in st.session_state["messages"]:
        msg_copy = msg.copy()
        if "image_path" in msg_copy:
            del msg_copy["image_path"]
        messages_to_save.append(msg_copy)
    
    final_data = {
        "style": st.session_state["style"],
        "conversation": messages_to_save
    }
    existing_data["conversations"].append(final_data)

    with open(style_file_path, "w", encoding="utf-8") as f:
        json.dump(existing_data, f, indent=4)

    st.success(f"Conversation saved to {style_file_path}")

    # Reset conversation after saving
    reset_conversation()

    # Automatically email the saved JSON file to your computer
    send_file_via_email(style_file_path)

############################################
# 5) Chat Input
############################################
def on_user_submit():
    typed = st.session_state.get("msg_input", "").strip()
    if not typed:
        return

    style_used = st.session_state["style"]
    # Check duplicates
    data = load_processed_inputs()
    found_dup = any(d["style"] == style_used and d["text"] == typed for d in data)
    if found_dup:
        st.warning("This user input has already been used with the current style.")
        st.session_state["duplicate_warning"] = True
    else:
        st.session_state["duplicate_warning"] = False

    # Save processed input
    save_processed_input(style_used, typed)

    # 1) Append user message without context tags initially
    user_msg = {
        "role": "user",
        "content": [{"type": "text", "text": typed}],
        "context_tags": []  # Temporary placeholder
    }
    st.session_state["messages"].append(user_msg)

    # short context
    sc_len = st.session_state["short_context_length"]
    short_context = st.session_state["messages"][-sc_len:]

    # AI reply using the fixed model and static prompt
    ai_reply_text = call_openai_chatcompletion(st.session_state["prompt_text"], short_context)

    assistant_msg = {
        "role": "assistant",
        "content": [{"type": "text", "text": ai_reply_text}],
        "context_tags": []  # Temporary placeholder
    }
    st.session_state["messages"].append(assistant_msg)

    ########################################
    # 2) Generate context tags for both messages
    ########################################
    context_inputs = [
        {'role': 'user', 'content': typed},
        {'role': 'assistant', 'content': ai_reply_text}
    ]
    context_tags = generate_context_tags(context_inputs)

    if 'user' in context_tags:
        st.session_state["messages"][-2]["context_tags"] = context_tags['user']
    else:
        st.warning("No context tags returned for user input.")

    if 'assistant' in context_tags:
        st.session_state["messages"][-1]["context_tags"] = context_tags['assistant']
    else:
        st.warning("No context tags returned for assistant response.")

    ########################################
    # 3) Image Selection
    ########################################
    selected_image_path = get_selected_image(context_tags)
    st.session_state["messages"][-1]["image_path"] = selected_image_path

    ########################################
    # 4) TTS if ON
    ########################################
    if not st.session_state["tts_off"]:
        audio_bytes = generate_audio(
            text=ai_reply_text,
            style_name=style_used,
            openai_api_key=OPENAI_API_KEY,
            model="tts-1",
            audio_format="mp3"
        )
        if audio_bytes:
            st.session_state["current_audio"] = audio_bytes
            st.audio(audio_bytes, format="audio/mp3", autoplay=True)
            st.session_state["current_audio"] = None

    words = len(ai_reply_text.split())
    ms_per_word = 500
    talk_ms = words * ms_per_word
    if talk_ms < 2000:
        talk_ms = 2000
    elif talk_ms > 20000:
        talk_ms = 20000
    st.session_state["talking_gif_ms"] = talk_ms

############################################
# 6) End & Save are unchanged
############################################

############################################
# 7) Main
############################################
def main():
    st.set_page_config(page_title="ai.girlfriend", layout="wide")
    init_session_state()

    with st.sidebar:
        st.title("Assistant Settings & Controls")

        # Style selection remains
        style_keys = list(style_prompts.keys())
        chosen_style = st.selectbox(
            "Select Style (Persona):",
            style_keys,
            index=style_keys.index(st.session_state["style"])
        )
        if chosen_style != st.session_state["style"]:
            st.session_state["style"] = chosen_style
            # Update prompt text directly based on style; no manual editing.
            st.session_state["prompt_text"] = style_prompts[chosen_style]
            reset_conversation()

        st.write(f"**Current Style**: {st.session_state['style']}")
        st.write(f"**Using Model:** {st.session_state['openai_model']}")

        sc_len = st.number_input(
            "Short context (recent msgs):",
            min_value=1,
            max_value=50,
            value=st.session_state["short_context_length"]
        )
        st.session_state["short_context_length"] = sc_len

        # TTS ON/OFF
        if st.session_state["tts_off"]:
            if st.button("TTS On"):
                st.session_state["tts_off"] = False
        else:
            if st.button("TTS Off"):
                st.session_state["tts_off"] = True
        tts_status = "OFF" if st.session_state["tts_off"] else "ON"
        st.write(f"**TTS Status:** {tts_status}")

        if st.button("End & Save Conversation"):
            on_end_and_save()

    st.title("ai.girlfriend")

    st.markdown("""
    <div class="scrollable-container" style="max-height: 400px; overflow-y: auto; padding: 0.5rem; margin-bottom: 1rem;">
    """, unsafe_allow_html=True)

    st.subheader("Conversation So Far")

    # Display messages as read-only instead of editable text areas.
    for i, msg in enumerate(st.session_state["messages"]):
        role = msg["role"]
        text = msg["content"][0].get("text", "")

        with st.chat_message(role):
            if role == "assistant" and msg.get("image_path"):
                col1, col2 = st.columns([4, 1], gap="small")
                with col1:
                    st.markdown(text)
                with col2:
                    try:
                        image = Image.open(msg["image_path"])
                    except Exception as e:
                        st.error(f"Error loading image: {e}")
                        image = None
                    if image:
                        st.image(image=image, width=160)
                        expand_key = f"expand_button_{i}"
                        if st.button("Expand", key=expand_key):
                            st.session_state["expanded_images"][i] = True
                        if st.session_state["expanded_images"].get(i, False):
                            with st.expander("Close", expanded=True):
                                st.image(image=image, use_container_width=True)
            else:
                st.markdown(text)

    st.markdown("</div>", unsafe_allow_html=True)

    # Chat input remains unchanged
    st.chat_input("Your message here...", key="msg_input", on_submit=on_user_submit)

    user_turns = sum(1 for m in st.session_state["messages"] if m["role"] == "user")
    st.write(f"**User turns so far**: {user_turns}")

############################################
# Run the App
############################################
if __name__ == "__main__":
    main()
