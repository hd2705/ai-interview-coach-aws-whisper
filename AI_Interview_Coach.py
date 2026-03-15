import streamlit as st
import database as db
import json
from datetime import datetime
import time
import hashlib


# --- AWS Logic Imports ---
from bedrock import get_ai_response_json, get_ai_response_text
from audio_processing import transcribe_audio_bytes, get_speech_audio
from st_audiorec import st_audiorec 


# Initialize the SQLite database tables (safe to call multiple times)
# This will call initialize_db() which now includes the 'interview_mode' column.
db.initialize_db()

# --- GLOBAL CONSTANTS (AWS related, minimal) ---
MAX_RETRIES = 5
RETRY_DELAY = 1  # seconds
# AWS credentials are handled by 'aws configure' and boto3, so no API_KEY is needed here.

# --- UTILITY & HELPER FUNCTIONS ---

# NOTE: AWS/boto3 handles retry logic implicitly for the basic connection.

def show_audio_player(audio_bytes):
    """Displays the audio player for synthesized speech."""
    if audio_bytes:
        # AWS Polly returns MP3 audio bytes
        st.audio(audio_bytes, format='audio/mp3')
def is_valid_audio(audio_bytes: bytes) -> bool:
    """Filters out ghost data (44 bytes) and overly short recordings."""
    if not audio_bytes:
        return False

    size = len(audio_bytes)

    # WAV header only (ghost)
    if size <= 44:
        return False

    # (5KB minimum)
    if size < 5000:
        return False

    return True
def generate_and_display_hint(job_desc, current_question):
    """Generates a hint using the HINT system prompt."""

    # Note: messages_history in the bedrock function expects a list of dictionaries.
    hint_message = [
        {"role": "user", "content": f"The job description is: {job_desc}. The current question I am stuck on is: {current_question}"}
    ]

    try:
        # Uses the restored bedrock.py function
        hint_text = get_ai_response_text(SYSTEM_PROMPT_HINT, hint_message)
        st.info(hint_text)
    except Exception as e:
        st.error(f"Error generating hint (API/Model Error): {e}")

def audio_hash(audio_bytes: bytes) -> str:
    """
    Generates a stable hash for an audio byte buffer.
    Used to prevent duplicate processing of the same recording.
    """
    return hashlib.md5(audio_bytes).hexdigest()

def calculate_average_score(interview_id):
    """Calculates the average score for an interview session."""
    # Uses the updated function from database.py
    session_meta, records = db.get_session_details(interview_id)
    if not records:
        return 0.0
    total_score = sum(r['score'] for r in records)
    return total_score / len(records)

def generate_final_summary(interview_id):
    """Generates the final comprehensive report using the FINAL_REPORT system prompt."""

    # 1. Fetch all records using the new database function
    session_meta, records = db.get_session_details(interview_id)

    if not records:
        raise Exception("No interview records found for the final report.")

    # 2. Compile the full transcript for the model
    # Uses the 'interview_mode' from the database metadata
    transcript = f"Job Description: {session_meta.get('job_description', 'N/A')}\nInterview Mode: {session_meta.get('interview_mode', 'N/A')}\n\n--- Transcript ---\n"
    scores = []

    for i, record in enumerate(records):
        transcript += f"Q{i+1}: {record['question']}\n"
        transcript += f"A{i+1}: {record['answer']}\n"
        transcript += f"Feedback: {record['feedback']} (Score: {record['score']}/10)\n\n"
        scores.append(record['score'])

    average_score = sum(scores) / len(records)

    # 3. Create the prompt for the report
    report_prompt = [
        {"role": "user", "content": f"Analyze the following interview transcript, paying special attention to the job description and provided feedback/scores. Generate a comprehensive, professional summary report in Markdown format. The report must contain sections for Overall Performance, Strengths, Areas for Improvement, and Final Score Breakdown.\n\nTranscript to analyze:\n{transcript}"}
    ]

    # 4. Get the AI-generated report text using the restored bedrock.py function
    report_text = get_ai_response_text(SYSTEM_PROMPT_FINAL_REPORT, report_prompt)

    return report_text, average_score


# Streamlit Configuration and Session State Initialization 
st.set_page_config(
    page_title="AI Interview Coach",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize all required session states
if "interview_id" not in st.session_state:
    st.session_state.interview_id = None
if "system_prompt" not in st.session_state:
    st.session_state.system_prompt = None
if "current_question" not in st.session_state:
    st.session_state.current_question = None
if "job_desc" not in st.session_state:
    st.session_state.job_desc = ""
if "is_finished" not in st.session_state:
    st.session_state.is_finished = False
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "content": "Hi! Paste a job description and choose an interview type to begin."}]
if "ready_for_recording" not in st.session_state:
    st.session_state.ready_for_recording = True
if "last_audio_hash" not in st.session_state:
    st.session_state.last_audio_hash = None
if "is_processing_answer" not in st.session_state:
    st.session_state.is_processing_answer = False
#  Theme CSS (Mint Green & Charcoal Grey) 
st.markdown("""
<style>
    /* Global Styles */
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    
    .stApp {
  ß      background-color: #f8f9fa !important;
        font-family: 'Poppins', sans-serif;
    }

    /* Force all general text to Charcoal Grey */
    .stApp, .stMarkdown p, .stMarkdown span, label, .stMarkdown div {
        color: #1f2937 !important;
    }

    /* Headings */
    .stMarkdown h1 {
        color: #00C853 !important; /* Mint Green */
        font-weight: 700;
    }
    
    .stMarkdown h2 {
        color: #424242 !important; /* Charcoal Grey */
        font-weight: 600;
        border-bottom: 2px solid #E8F5E9;
        padding-bottom: 5px;
        margin-top: 20px;
    }

    /* Target the instruction/info boxes specifically */
    [data-testid="stNotification"] {
        background-color: #E8F5E9 !important;
        color: #1f2937 !important;
        border: 1px solid #00C853;
    }

    /* Sidebar text visibility */
    [data-testid="stSidebar"] .stMarkdown p, [data-testid="stSidebar"] label {
        color: #1f2937 !important;
    }

    /* Chat Messages */
    .stChatMessage {
        background-color: #ffffff !important;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }

    /* Assistant specific styling */
    [data-testid="stChatMessage"][data-testid="stChatMessage-container"]:nth-child(even) {
        background-color: #E8F5E9; /* Pale Mint background for AI/Assistant */
    }

    /* Buttons */
    .stButton>button {
        color: white;
        background-color: #00C853; /* Mint Green */
        border: none;
        border-radius: 8px;
        padding: 10px 20px;
        font-weight: 600;
        transition: all 0.2s ease;
    }

    .stButton>button:hover {
        background-color: #00A343; /* Darker Mint Green on hover */
        box-shadow: 0 4px 6px rgba(0, 200, 83, 0.3);
    }

    /* Primary Button (Start Interview) */
    .stButton[data-testid="stFormSubmitButton"]>button {
        background-color: #424242; /* Charcoal Grey */
    }
    .stButton[data-testid="stFormSubmitButton"]>button:hover {
        background-color: #212121; /* Darker Charcoal Grey on hover */
    }

    /* Hint Button - Using the Charcoal color for visibility */
    #hint-button-container .stButton>button {
        background-color: #424242;
    }
    #hint-button-container .stButton>button:hover {
        background-color: #212121;
    }

    /* --- AUDIO RECORDER STYLING FIX --- */
    /* Target the main container of st_audiorec for light background */
    [data-testid="stVerticalBlock"] > div:nth-child(4) > div:nth-child(2) > div {
        background-color: #ffffff; /* White background for the recorder block */
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 15px;
        margin-top: 10px;
    }

    /* Target the buttons inside st_audiorec */
    [data-testid="stVerticalBlock"] button {
        background-color: #00C853 !important; /* Mint Green for recorder buttons */
        color: white !important;
        font-weight: 600;
        border: none;
    }

    [data-testid="stVerticalBlock"] button:hover {
        background-color: #00A343 !important; /* Darker Mint Green on hover */
    }

</style>
""", unsafe_allow_html=True)


# 2. System Prompts (The AI's Personalities) 
SYSTEM_PROMPT_STANDARD = """
You are a professional hiring manager. Your goal is to conduct a challenging interview,
mixing both behavioral and technical questions. You must analyze the ENTIRE
conversation history to ask deep, logical follow-up questions.
IMPORTANT: You MUST respond in a valid JSON format.
The JSON object must have these three keys:
1. "feedback": A concise, constructive critique of the user's last answer.
2. "score": An integer score from 1 (poor) to 10 (excellent) for the answer.
3. "next_question": The single, next logical interview question.
"""

SYSTEM_PROMPT_BEHAVIORAL = """
You are a professional hiring manager specializing in behavioral interviews.
Your goal is to ask questions that test the user's soft skills, teamwork, and
problem-solving process, often using the STAR method ("Tell me about a time...").
You must analyze the ENTIRE conversation history to ask deep, logical follow-ups.
IMPORTANT: You MUST respond in a valid JSON format.
The JSON object must have these three keys:
1. "feedback": A critique focused on communication, clarity, and use of the STAR method.
2. "score": An integer score from 1 (poor) to 10 (excellent) for the answer's behavioral strength.
3. "next_question": The single, next logical behavioral interview question.
"""

SYSTEM_PROMPT_TECHNICAL = """
You are a senior technical interviewer (e.g., a Staff Engineer or Principal Data Scientist).
Your goal is to conduct a rigorous technical deep-dive. Ask challenging questions about
algorithms, system design, data structures, and specific technologies from the job description.
You must analyze the ENTIRE conversation history to ask deep, logical follow-ups.
IMPORTANT: You MUST respond in a valid JSON format.
The JSON object must have these three keys:
1. "feedback": A critique focused on technical accuracy, depth, and efficiency of the solution.
2. "score": An integer score from 1 (poor) to 10 (excellent) for the answer's technical accuracy.
3. "next_question": The single, next logical technical interview question.
"""

SYSTEM_PROMPT_HINT = """
You are a supportive, expert interview coach. The user is stuck on a question.
Your goal is to provide a brief, actionable hint that guides the user to the correct
or best line of reasoning, without giving away the final answer.

If the question is:
- TECHNICAL: Provide the single most important **concept** or **term** they should mention.
- BEHAVIORAL: Remind them of the **structure** they should use.

Keep the hint brief (one sentence). Start your response with "Here is a hint to get you started:"
"""

SYSTEM_PROMPT_TEXT = "You are a professional hiring manager. Ask the user one single interview question based on their request. Do not add any conversational text before or after the question."

SYSTEM_PROMPT_FINAL_REPORT = "You are a top-tier interview coach. Your only job is to generate a comprehensive, professional summary report in Markdown format based on the user's transcript analysis."


# --- 3. Sidebar ---
with st.sidebar:
    st.header("Setup Your Interview")

    # --- New Layout for Finish Button ---
    if st.session_state.interview_id:
        st.markdown('<div id="finish-interview-button">', unsafe_allow_html=True)
        if st.button("Finish Interview & Get Report", key="finish_interview_btn", use_container_width=True):
            st.session_state.is_finished = True
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("---")

    interview_mode = st.selectbox(
        "Choose Interview Type:",
        ("Standard Mix", "Behavioral Only", "Technical Deep-Dive")
    )
    # Use st.session_state.job_desc as the default value if it's set
    default_job_desc = st.session_state.job_desc if st.session_state.job_desc else ""
    job_desc = st.text_area("Paste the Job Description Here:",
                             value=default_job_desc,
                             height=200,
                             placeholder="E.g., Data Scientist at Google...")

    start_button = st.button("Start Interview", type="primary")

# 4. Final Report Display Logic 
if st.session_state.is_finished:
    st.markdown("## 🛑 Interview Finished! Generating Report...")
    if st.session_state.interview_id:
        with st.spinner("Analyzing transcript and generating AI Summary..."):
            try:
                summary_text, average_score = generate_final_summary(st.session_state.interview_id)
                st.subheader(f"✅ Final Assessment Report (Score: {average_score:.2f}/10)")
                st.markdown(summary_text)

                # Reset session states for a clean start next time
                st.session_state.job_desc = ""
                st.session_state.current_question = None
                st.session_state.interview_id = None
                st.session_state.system_prompt = None
                st.session_state.messages = [{"role": "assistant", "content": "Hi! Paste a job description and choose an interview type to begin."}]
                st.session_state.is_finished = False

            except Exception as e:
                st.error(f"Error generating summary: {e}. Ensure you answered at least one question.")
    else:
        st.warning("No active interview session found to generate a report.")
        st.session_state.is_finished = False

    st.stop()


#  5. Main Chat Interface 
st.title("🤖 AI Interview Coach")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if isinstance(msg["content"], dict):
            st.subheader(f"Feedback (Score: {msg['content']['score']}/10)")
            st.markdown(msg['content']['feedback'])
            st.markdown("---")
            st.subheader("Next Question:")
            st.markdown(msg['content']['next_question'])
        else:
            # Properly display non-dictionary (text) messages
            st.markdown(msg["content"])


#  6. Logic for "Start Interview" 
if start_button:
    if not job_desc:
        st.error("Please paste a job description to start.")
    else:
        # Set the correct system prompt based on mode selection
        st.session_state.interview_mode = interview_mode
        if interview_mode == "Behavioral Only":
            st.session_state.system_prompt = SYSTEM_PROMPT_BEHAVIORAL
        elif interview_mode == "Technical Deep-Dive":
            st.session_state.system_prompt = SYSTEM_PROMPT_TECHNICAL
        else:
            st.session_state.system_prompt = SYSTEM_PROMPT_STANDARD

        # Save job_desc to session state
        st.session_state.job_desc = job_desc

        # Create the new interview session in the DB
        with st.spinner("Initializing database session..."):
            try:
                st.session_state.interview_id = db.create_interview_session(job_desc, interview_mode)
            except Exception as db_e:
                st.error(f"Database error when starting session: {db_e}. Ensure your database.py is updated and the .db file is deleted/recreated.")
                st.stop() # Stop if DB fails

        initial_messages = [
            {"role": "user", "content": f"I am preparing for an interview. Here is the job description: {job_desc}. My chosen mode is {interview_mode}. Please start the interview by asking me the first question."}
        ]

        with st.chat_message("assistant"):
            with st.spinner("AI is thinking..."):

                try:
                    # Uses the restored bedrock.py function
                    first_question = get_ai_response_text(SYSTEM_PROMPT_TEXT, initial_messages)

                    st.session_state.messages = [{"role": "assistant", "content": first_question}]
                    st.markdown(first_question)
                    st.session_state.current_question = first_question

                    # Synthesize and play audio using the restored audio_processing.py function (AWS Polly)
                    audio_bytes = get_speech_audio(first_question)
                    if audio_bytes:
                        show_audio_player(audio_bytes)

                except Exception as e:
                    # This will now display the detailed boto3/AWS error
                    st.error(f"Error generating first question (AWS/Model Error): {e}. Please ensure you ran 'aws configure'.")
                    st.session_state.messages = [{"role": "assistant", "content": "An error occurred while starting the interview. Please try again."}]
                    st.stop()

        st.rerun()

#  7. Voice Input Workflow (STABLE & CORRECTED LAYOUT) 

# Initialize the processing flag at the top if it doesn't exist
if "is_processing_answer" not in st.session_state:
    st.session_state.is_processing_answer = False

if "interview_id" in st.session_state and not st.session_state.is_finished and st.session_state.current_question:
    st.markdown("---")
    st.subheader("Your Answer:")

    # Split into columns for Mic and Hint 
    col_mic, col_hint = st.columns([0.7, 0.3])

    with col_hint:
        st.markdown('<div id="hint-button-container">', unsafe_allow_html=True)
        #The Hint button - next to the recorder
        if st.button("Get a Hint", use_container_width=True):
            if st.session_state.current_question:
                with st.spinner("Generating hint..."):
                    generate_and_display_hint(st.session_state.job_desc, st.session_state.current_question)
            else:
                st.warning("Please wait for the first question to be asked.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_mic:
        # Component renders inside the left column
        wav_audio_data = st_audiorec()

    # Processing Logic (Outside columns for better UI flow) 
    if wav_audio_data is not None:
        audio_size = len(wav_audio_data)
        
        if audio_size > 44:
            # Check processing flag to prevent the duplicate loop
            if not st.session_state.is_processing_answer:
                st.success("Audio captured! Click the button below to submit.")
                
                if st.button("🚀 Process My Answer", type="primary", use_container_width=True):
                    # LOCK the process
                    st.session_state.is_processing_answer = True
                    
                    with st.spinner("AI is analyzing your answer..."):
                        user_answer = transcribe_audio_bytes(wav_audio_data)
                        
                        if user_answer:
                            st.session_state.messages.append({"role": "user", "content": user_answer})
                            
                            try:
                                ai_response_json = get_ai_response_json(
                                    st.session_state.system_prompt, 
                                    st.session_state.messages
                                )
                                
                                st.session_state.messages.append({"role": "assistant", "content": ai_response_json})
                                st.session_state.current_question = ai_response_json['next_question']
                                
                                db.save_record(
                                    interview_id=st.session_state.interview_id,
                                    question=st.session_state.current_question,
                                    answer=user_answer,
                                    feedback=ai_response_json['feedback'],
                                    score=ai_response_json['score']
                                )
                                
                                # RESET flag and clean up
                                st.session_state.is_processing_answer = False
                                del wav_audio_data
                                st.rerun()
                                
                            except Exception as e:
                                st.error(f"AI Error: {e}")
                                st.session_state.is_processing_answer = False
                        else:
                            st.error("Transcription failed. Please try speaking again.")
                            st.session_state.is_processing_answer = False
            else:
                st.info("Analysis in progress... please wait.")
        else:
            # Standby message for 44-byte ghost data
            st.info("Microphone standby... Please click 'Start Recording' when ready.")
            st.session_state.is_processing_answer = False