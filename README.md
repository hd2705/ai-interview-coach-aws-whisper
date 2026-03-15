# AI Interview Coach: Multimodal Generative AI Assistant
### 🎙️ AWS Bedrock + OpenAI Whisper + AWS Polly

An intelligent, voice-enabled interview preparation platform that provides real-time conversational practice and structured feedback. This system uses a hybrid AI approach, combining cloud-based LLMs for intelligence with local models for high-accuracy speech processing.

## 🚀 Key Features
* **Voice-to-Voice Interaction:** Practice interviews using natural speech, powered by OpenAI Whisper (STT) and AWS Polly (TTS).
* **Intelligent Feedback:** Real-time analysis of answers using **AWS Bedrock (Claude 3.5 Sonnet)** to provide scores on clarity, relevance, and technical depth.
* **Mode Selection:** Supports "Behavioral" and "Technical" interview modes with customized question generation.
* **Progress Tracking:** Persistent storage of interview history and performance metrics using SQLite3.

## 🛠️ Technical Tech Stack
* **Generative AI:** AWS Bedrock (Claude 3.5 Sonnet)
* **Speech-to-Text:** OpenAI Whisper (Medium Model)
* **Text-to-Speech:** AWS Polly
* **Frontend:** Streamlit & streamlit-audiorec
* **Backend/Database:** Python, Boto3, SQLite3, Pandas

## ⚙️ System Architecture
The application follows a three-tiered architecture:
1.  **Presentation Layer:** Streamlit UI handles microphone input and renders the interactive dashboard and chat history.
2.  **Logic Layer:** * `bedrock.py`: Manages prompt engineering and JSON sanitization for feedback.
    * `audio_processing.py`: Handles local Whisper transcription and AWS Polly synthesis.
3.  **Data Layer:** `database.py` manages the SQLite schema to track user progress over time.

## 📈 Visualizations & Dashboard
The project includes a dedicated "My Progress" dashboard (located in `/pages`) that analyzes:
* Average performance scores across different interview sessions.
* Trend analysis of technical vs. behavioral competency.
* Historical logs of questions, answers, and AI-generated critiques.

## 📂 Repository Structure
* `AI_Interview_Coach.py`: Main application entry point.
* `/pages`: `1_My_Progress.py` - User performance dashboard.
* `bedrock.py`: AWS Bedrock integration logic.
* `audio_processing.py`: Whisper and Polly audio pipelines.
* `database.py`: SQLite schema and data persistence methods.
* `requirements.txt`: Environment dependencies.

---
**Author:** Hrushitha Darna  
**Project:** Final Capstone - AI Interview Systems
