# app.py

import streamlit as st
import google.generativeai as genai
import plotly.express as px
import pandas as pd
import re
import json
import database as db  # Import our new database helper

# --- Page Configuration ---
st.set_page_config(
    layout="wide",
    page_title="Productivity Copilot Dashboard"
)

# --- Database Initialization ---
# This will create the database and table on the first run
db.create_table()

# --- API Key and Model Configuration ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error("Google API key not found. Please add it to your Streamlit secrets.", icon="🚨")
    st.stop()

# --- Initialize Session State ---
if 'tasks' not in st.session_state:
    st.session_state.tasks = []
if 'ai_summary' not in st.session_state:
    st.session_state.ai_summary = ""

# --- Sidebar ---
with st.sidebar:
    st.title("📄 Input & Controls")
    st.subheader("Enter your text below")
    user_input = st.text_area("Paste your meeting notes, emails, etc.:", height=250)

    if st.button("Analyze Text ✨"):
        if user_input:
            with st.spinner('Gemini is thinking...'):
                try:
                    # (Code for prompting the AI remains the same)
                    prompt = f"""
                    Analyze the text below. First, create a concise '## Summary'.
                    Second, extract any clear tasks into a list under a '## Action Items' heading.
                    Each action item must be on a new line and start with a hyphen (-).

                    Text to Analyze:
                    ---
                    {user_input}
                    ---
                    """
                    response = model.generate_content(prompt)
                    ai_response = response.text

                    st.session_state.ai_summary = re.search(r"## Summary\n(.*?)(?=\n## Action Items|\Z)", ai_response, re.DOTALL).group(1).strip()
                    
                    action_items_text = re.search(r"## Action Items\n(.*?)(?=\Z)", ai_response, re.DOTALL)
                    if action_items_text:
                        task_list = action_items_text.group(1).strip().split('\n')
                        st.session_state.tasks = [{'task': task.strip('- '), 'done': False} for task in task_list if task.strip()]
                    else:
                        st.session_state.tasks = []
                    
                    # --- NEW: Save the results to the database ---
                    db.insert_analysis(st.session_state.ai_summary, st.session_state.tasks)
                    
                    st.success("Analysis complete and saved to history!")

                except Exception as e:
                    st.error(f"An error occurred: {e}", icon="🚨")
        else:
            st.warning("Please enter some text to analyze.", icon="⚠️")

    # --- NEW: Display Analysis History in Sidebar ---
    st.markdown("---")
    st.title("📖 Analysis History")
    history = db.get_all_analyses()

    if not history:
        st.info("No past analyses found.")
    else:
        for record in history:
            # Format the timestamp to be more readable
            timestamp = pd.to_datetime(record['created_at']).strftime('%Y-%m-%d %H:%M')
            with st.expander(f"Analysis from {timestamp}"):
                st.write("**Summary:**")
                st.write(record['summary'])
                st.write("**Action Items:**")
                tasks_from_db = json.loads(record['tasks'])
                for task in tasks_from_db:
                    st.write(f"- {task['task']}")

# --- Main Dashboard Area ---
st.title("🤖 Productivity Copilot Dashboard")

if not st.session_state.tasks and not st.session_state.ai_summary:
    st.info("Enter some text in the sidebar and click 'Analyze Text' to get started.")
else:
    # (The rest of the main dashboard code remains the same)
    summary_col, dashboard_col = st.columns(2)

    with summary_col:
        st.subheader("📝 Summary")
        st.write(st.session_state.ai_summary)

    with dashboard_col:
        st.subheader("✅ Action Items Checklist")
        
        for i, task in enumerate(st.session_state.tasks):
            st.session_state.tasks[i]['done'] = st.checkbox(task['task'], value=task['done'], key=f"task_{i}")

        st.subheader("📊 Task Progress")
        
        done_count = sum(1 for task in st.session_state.tasks if task['done'])
        todo_count = len(st.session_state.tasks) - done_count

        if len(st.session_state.tasks) > 0:
            df = pd.DataFrame([
                {'Status': 'Done', 'Count': done_count},
                {'Status': 'To-Do', 'Count': todo_count}
            ])
            fig = px.pie(df, values='Count', names='Status', title='Task Status',
                         color_discrete_map={'Done': '#4CAF50', 'To-Do': '#E0E0E0'})
            st.plotly_chart(fig, use_container_width=True)
            
            st.markdown("---")
            
            export_text = f"# AI Analysis Results\n\n## Summary\n{st.session_state.ai_summary}\n\n## Action Items\n"
            for task in st.session_state.tasks:
                status = "[x]" if task['done'] else "[ ]"
                export_text += f"- {status} {task['task']}\n"
                
            st.download_button(
                label="📥 Export as Markdown",
                data=export_text,
                file_name="analysis_results.md",
                mime="text/markdown"
            )