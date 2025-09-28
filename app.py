# app.py

import streamlit as st
import google.generativeai as genai
import plotly.express as px
import pandas as pd
import re
import json
import database as db

# --- Page Configuration ---
st.set_page_config(
    layout="wide",
    page_title="Productivity Copilot Dashboard"
)

# --- Database Initialization ---
db.create_table()

# --- API Key and Model Configuration ---
try:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
    model = genai.GenerativeModel('gemini-2.5-flash-preview')
model = genai.GenerativeModel('gemini-2.5-flash-preview')
 # This line is now indented
except Exception as e:
    st.error("Google API key not found...", icon="🚨")
    st.stop()

# --- Initialize Session State ---
if 'tasks' not in st.session_state:
    st.session_state.tasks = []
if 'ai_summary' not in st.session_state:
    st.session_state.ai_summary = ""

# --- Helper Function to Clean JSON (NEW) ---
def clean_json_response(text):
    """Cleans the AI's response to extract a valid JSON string."""
    # Use regex to find the content between the first '{' and the last '}'
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return None

# --- Sidebar ---
with st.sidebar:
    st.title("📄 Input & Controls")
    st.subheader("Enter your text below")
    user_input = st.text_area("Paste your meeting notes, emails, etc.:", height=250)

    if st.button("Analyze Text ✨"):
        if user_input:
            with st.spinner('Gemini is thinking...'):
                try:
                    # --- UPDATED PROMPT: Requesting JSON Output ---
                    prompt = f"""
                    Analyze the text below. Return a single, valid JSON object with two keys:
                    1. "summary": A concise summary of the key points.
                    2. "action_items": A list of strings, where each string is a clear task or to-do item.

                    Do not include any text or formatting outside of the JSON object.

                    Text to Analyze:
                    ---
                    {user_input}
                    ---
                    """
                    response = model.generate_content(prompt)
                    
                    # --- UPDATED PARSING LOGIC: Using JSON ---
                    cleaned_json_string = clean_json_response(response.text)
                    if cleaned_json_string:
                        ai_data = json.loads(cleaned_json_string)
                        st.session_state.ai_summary = ai_data.get("summary", "No summary provided.")
                        
                        action_items_list = ai_data.get("action_items", [])
                        st.session_state.tasks = [{'task': item, 'done': False} for item in action_items_list]
                        
                        # Save the results to the database
                        db.insert_analysis(st.session_state.ai_summary, st.session_state.tasks)
                        st.success("Analysis complete and saved to history!")
                    else:
                        st.error("The AI did not return a valid JSON response. Please try again.")

                except json.JSONDecodeError:
                    st.error("Failed to decode the AI's response. The format was invalid.")
                except Exception as e:
                    st.error(f"An error occurred: {e}", icon="🚨")
        else:
            st.warning("Please enter some text to analyze.", icon="⚠️")

    # --- Analysis History Display (No changes here) ---
    st.markdown("---")
    st.title("📖 Analysis History")
    history = db.get_all_analyses()

    if not history:
        st.info("No past analyses found.")
    else:
        for record in history:
            timestamp = pd.to_datetime(record['created_at']).strftime('%Y-%m-%d %H:%M')
            with st.expander(f"Analysis from {timestamp}"):
                st.write("**Summary:**")
                st.write(record['summary'])
                st.write("**Action Items:**")
                tasks_from_db = json.loads(record['tasks'])
                for task in tasks_from_db:
                    st.write(f"- {task['task']}")

# --- Main Dashboard Area (No changes here) ---
st.title("🤖 Productivity Copilot Dashboard")

if not st.session_state.tasks and not st.session_state.ai_summary:
    st.info("Enter some text in the sidebar and click 'Analyze Text' to get started.")
else:
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