import boto3
import whisper
import tempfile
import os

# --- Whisper Model Logic ---
_whisper_model = None

def get_whisper_model():
    """
    Lazy Loading: Only loads the 5GB model into RAM when needed.
    """
    global _whisper_model
    if _whisper_model is None:
        print("Loading Whisper model...")
        # If 'medium' is too heavy for your Mac, change this to 'base'
        _whisper_model = whisper.load_model("medium")
        print("Whisper model loaded.")
    return _whisper_model

# --- Polly Client ---
polly_client = boto3.client("polly", region_name="us-east-1")

# --- Transcription (REPAIRED) ---
def transcribe_audio_bytes(audio_bytes: bytes) -> str:
    """
    Transcribes audio bytes using Whisper.
    Processes audio only after passing the Logic Firewall.
    """
    if not audio_bytes or len(audio_bytes) <= 44:
        return ""

    model = get_whisper_model()

    # Write audio to temp WAV file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
        tmp_file.write(audio_bytes)
        temp_path = tmp_file.name

    try:
        # fp16=False is used for better compatibility on CPUs/Macs
        result = model.transcribe(temp_path, fp16=False)
        transcription = result.get("text", "").strip()

        if transcription:
            print(f"[DEBUG] Whisper transcription: {transcription}")

        return transcription

    except Exception as e:
        print(f"[ERROR] Whisper transcription failed: {e}")
        return ""

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

# --- Text-to-Speech (Polly) ---
def get_speech_audio(text):
    """
    Converts AI feedback into high-fidelity speech using AWS Polly.
    """
    try:
        response = polly_client.synthesize_speech(
            Text=text,
            OutputFormat="mp3",
            VoiceId="Joanna", # Neural engine voice
            Engine="neural"
        )
        return response['AudioStream'].read()
    except Exception as e:
        print(f"[ERROR] Polly synthesis failed: {e}")
        return None