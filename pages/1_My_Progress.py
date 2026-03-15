import streamlit as st
import database as db
import pandas as pd
from datetime import datetime

# Configure page settings - MUST BE FIRST
st.set_page_config(layout="wide", page_title="AI Interview Coach - Progress")

# --- MINT GREEN & CHARCOAL GREY CSS STYLING ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap');
    .stApp { background-color: #f8f9fa; color: #1f2937; font-family: 'Poppins', sans-serif; }
    .stMarkdown h1 { color: #00C853; font-weight: 700; }
    .stMarkdown h2 { color: #424242; font-weight: 600; border-bottom: 2px solid #E8F5E9; padding-bottom: 5px; margin-top: 20px; }
    .stMetric > div > div:first-child { color: #00C853; font-weight: 700; font-size: 2em; }
    .stCodeBlock { background-color: #424242; color: #E8F5E9; border-radius: 8px; }
</style>
""", unsafe_allow_html=True)

st.title("📚 My Progress & History")
st.markdown("Review your past interview sessions, scores, and feedback.")

# Get all sessions from the database
sessions = db.get_all_sessions()

if not sessions:
    st.info("You haven't completed any interview sessions yet. Start one on the main page!")
else:
    df = pd.DataFrame(sessions)
    
    # Convert ID to string to match TextColumn config 
    df['id'] = df['id'].astype(str)
    
    # Format the start time
    df['start_time_formatted'] = df['start_time'].apply(lambda x: db.format_datetime(x))
    
    # Calculate display score
    df['average_score_display'] = df.apply(
        lambda row: f"{row['average_score']:.1f} / 10" if row['question_count'] > 0 else "N/A",
        axis=1
    )

    st.subheader("All Interview Sessions")
    
    # Prepare display dataframe
    display_df = df[['id', 'start_time_formatted', 'interview_mode', 'question_count', 'average_score_display', 'average_score']]
    display_df.columns = ['ID', 'Date Started', 'Type', 'Questions Answered', 'Avg. Score Text', 'Avg. Score']
    
    # Correctly configured data editor ---
    st.data_editor(
        display_df,
        column_config={
            "ID": st.column_config.TextColumn("ID", help="Session Identifier", disabled=True),
            "Date Started": st.column_config.TextColumn("Date Started", disabled=True),
            "Type": st.column_config.TextColumn("Type", disabled=True),
            "Questions Answered": st.column_config.NumberColumn("Questions Answered", disabled=True),
            "Avg. Score Text": st.column_config.TextColumn("Avg. Score", disabled=True),
            "Avg. Score": st.column_config.ProgressColumn(
                "Performance Visual", 
                help="Average Score (0-10)", 
                format="%.1f", 
                min_value=0, 
                max_value=10
            )
        },
        hide_index=True,
        key="sessions_table_editor",
        use_container_width=True
    )

    st.markdown("---")
    st.subheader("Session Details")

    session_ids = df['id'].tolist()
    
    selected_id = st.selectbox(
        "Select a Session ID to view detailed history:",
        options=session_ids,
        format_func=lambda x: f"Session {x} - {df[df['id'] == x]['start_time_formatted'].iloc[0]}"
    )

    if selected_id:
        # Note: Ensure database.get_session_details handles string IDs if necessary
        session_meta, records = db.get_session_details(selected_id)

        if session_meta:
            # Handle potential key difference (job_description vs job_desc)
            jd_text = session_meta.get('job_description') or session_meta.get('job_desc') or "No description"
            st.info(f"**Job Description:** {jd_text}")
            st.info(f"**Interview Type:** {session_meta.get('interview_mode', 'N/A')}")
        
        if not records:
            st.warning("No questions were recorded for this session.")
        else:
            total_score = sum(r['score'] for r in records)
            avg_score = total_score / len(records)
            st.metric("Overall Session Average Score", f"{avg_score:.2f} / 10")
            
            for i, record in enumerate(records):
                with st.expander(f"Q{i+1}: {record['question']}", expanded=False):
                    col_q_time, col_q_score = st.columns([0.7, 0.3])
                    with col_q_time:
                        st.caption(f"Answered: {db.format_datetime(record['timestamp'])}")
                    with col_q_score:
                        st.metric("Score", f"{record['score']} / 10")
                        
                    st.markdown("#### **Your Answer:**")
                    st.code(record['answer'], language='text')
                    st.markdown("#### **AI Feedback:**")
                    st.markdown(record['feedback'])