# tts_module.py
import os
import uuid
import requests
import streamlit as st
from pydub import AudioSegment
from io import BytesIO

# Ensure ffmpeg is available
AudioSegment.converter = "ffmpeg"  # or provide the full path if necessary

# Style-based TTS configurations
style_tts_config = {
    "ai.girlfriend.caring": {
        "voice": "sage",            # Gentle voice
        "pitch_adjustment": 1.1,    # Lower pitch
        "speed": 1.0                 # Normal speed
    },
    "ai.girlfriend.toxic": {
        "voice": "sage",            # Edgy voice
        "pitch_adjustment": 1.1,    # Higher pitch
        "speed": 1.0                 # Slightly faster
    },
    "ai.girlfriend.flirty": {
        "voice": "coral",           # Professional/neutral
        "pitch_adjustment": 1.0,    # Higher pitch
        "speed": 0.9                 # Slightly slower
    },
    "ai.girlfriend.curious": {
        "voice": "sage",            # Gentle voice
        "pitch_adjustment": 1.1,    # Lower pitch
        "speed": 1.1                 # Slightly faster
    },
    "ai.girlfriend.playful": {
        "voice": "coral",           # Edgy voice
        "pitch_adjustment": 1.2,    # Higher pitch
        "speed": 0.9                 # Faster
    },
    "ai.girlfriend.hood": {
        "voice": "shimmer",         # Professional/neutral
        "pitch_adjustment": 1.0,    # Lower pitch
        "speed": 1.1                 # Normal speed
    },
    "ai.girlfriend.country_girl": {
        "voice": "nova",            # Gentle voice
        "pitch_adjustment": 1.1,    # Lower pitch
        "speed": 0.95                # Slightly slower
    },
    "ai.girlfriend.depressed": {
        "voice": "sage",            # Edgy voice
        "pitch_adjustment": 1.1,    # Higher pitch
        "speed": 0.85                # Slower
    },
    "ai.girlfriend.narcissistic": {
        "voice": "nova",            # Professional/neutral
        "pitch_adjustment": 1.0,    # No pitch adjustment
        "speed": 1.0                 # Normal speed
    },
    "ai.girlfriend.joker": {
        "voice": "sage",            # Gentle voice
        "pitch_adjustment": 1.0,    # Lower pitch
        "speed": 1.1                 # Slightly faster
    },
    "ai.girlfriend.intellectual": {
        "voice": "coral",           # Edgy voice
        "pitch_adjustment": 1.1,    # Higher pitch
        "speed": 1.0                 # Normal speed
    },
    "ai.girlfriend.kinky": {
        "voice": "sage",            # Professional/neutral
        "pitch_adjustment": 1.1,    # Higher pitch
        "speed": 1.2                 # Slightly faster
    },
    "ai.girlfriend.churchy": {
        "voice": "coral",           # Gentle voice
        "pitch_adjustment": 1.1,    # Lower pitch
        "speed": 1.0                 # Normal speed
    },
    "ai.girlfriend.simple": {
        "voice": "sage",            # Edgy voice
        "pitch_adjustment": 1.1,    # Higher pitch
        "speed": 1.0                 # Normal speed
    },
    "ai.girlfriend.shy": {
        "voice": "sage",            # Professional/neutral
        "pitch_adjustment": 1.2,    # Higher pitch
        "speed": 0.95                # Slightly slower
    },
    "ai.girlfriend.basic": {
        "voice": "shimmer",         # Gentle voice
        "pitch_adjustment": 1.1,    # Lower pitch
        "speed": 1.0                 # Normal speed
    },
    "ai_athena.wife.colsons_wife": {
        "voice": "sage",            # Edgy voice
        "pitch_adjustment": 1.1,    # Higher pitch
        "speed": 1.0                 # Normal speed
    },
    "ai.girlfriend.anime": {
        "voice": "sage",           # Professional/neutral
        "pitch_adjustment": 1.20,    # Higher pitch
        "speed": 0.9                 # Faster
    },
    # Add more styles as needed...
}

# Fallback TTS config
default_tts = {
    "voice": "sage",
    "pitch_adjustment": 1.0,  # No pitch adjustment
    "speed": 1.0  # Default speed
}

def get_tts_config_for_style(style_name: str):
    """
    Return the (voice, pitch_adjustment, speed) for the given style.
    Fallback to 'default_tts' if not found.
    """
    return style_tts_config.get(style_name, default_tts)

def delete_audio_files_batch(file_paths: list):
    """
    Safely delete a list of local audio files if they exist.
    """
    for file_path in file_paths:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
                st.info(f"Deleted audio file: {file_path}")
            except Exception as e:
                st.warning(f"Could not delete {file_path}: {e}")

def adjust_pitch(audio_bytes: BytesIO, pitch_adjustment: float) -> BytesIO:
    """
    Adjust the pitch of the audio by a certain factor.
    Positive values increase pitch, negative decrease.
    Returns a new BytesIO object with the adjusted audio.
    """
    try:
        sound = AudioSegment.from_file(audio_bytes)
        
        # Calculate new sample rate based on pitch adjustment
        new_sample_rate = int(sound.frame_rate * pitch_adjustment)
        pitched_sound = sound._spawn(sound.raw_data, overrides={"frame_rate": new_sample_rate})
        
        # Maintain original frame rate to preserve playback speed
        pitched_sound = pitched_sound.set_frame_rate(sound.frame_rate)

        # Export to BytesIO
        pitched_audio_bytes = BytesIO()
        pitched_sound.export(pitched_audio_bytes, format="mp3")
        pitched_audio_bytes.seek(0)
        return pitched_audio_bytes
    except Exception as e:
        st.error(f"Pitch adjustment failed: {e}")
        return audio_bytes  # Return the original bytes if adjustment fails

def generate_audio(
    text: str,
    style_name: str,
    openai_api_key: str,
    model: str = "tts-1",
    audio_format: str = "mp3"  # Enforce 'mp3' to avoid ffmpeg issues
) -> BytesIO:
    """
    1) Look up voice, pitch, & speed from style config
    2) Call the OpenAI TTS API (with up to 3 retries)
    3) Adjust pitch if needed
    4) Return the final audio as BytesIO object (in-memory)
    """
    if not openai_api_key:
        st.error("No API key provided for TTS generation.")
        return None

    # Retrieve voice, pitch, and speed based on style
    style_config = get_tts_config_for_style(style_name)
    voice = style_config["voice"]
    pitch_adjustment = style_config["pitch_adjustment"]
    speed = style_config.get("speed", 1.0)  # Default to 1.0 if not specified

    url = "https://api.openai.com/v1/audio/speech"
    headers = {
        "Authorization": f"Bearer {openai_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "voice": voice,
        "input": text,
        "response_format": audio_format,  # Use 'mp3'
        "speed": speed  # Include speed parameter
    }

    audio_bytes = None
    for attempt in range(3):
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            audio_bytes = BytesIO(response.content)
            st.info(f"TTS generation succeeded on attempt {attempt + 1}")
            break  # Success, exit the retry loop
        except requests.exceptions.RequestException as req_err:
            if attempt < 2:
                st.warning(f"TTS generation error (attempt {attempt + 1}), retrying: {req_err}")
            else:
                st.error(f"TTS generation failed after 3 attempts: {req_err}")
        except Exception as e:
            if attempt < 2:
                st.warning(f"TTS unexpected error (attempt {attempt + 1}), retrying: {e}")
            else:
                st.error(f"TTS error after 3 attempts: {e}")

    # If we never got audio bytes, bail out
    if not audio_bytes:
        return None

    # Adjust pitch if needed
    if pitch_adjustment != 1.0:
        audio_bytes = adjust_pitch(audio_bytes, pitch_adjustment)

    return audio_bytes
