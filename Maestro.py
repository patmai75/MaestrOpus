import streamlit as st
from anthropic import Anthropic
import re
from datetime import datetime
from PIL import Image
import base64
from io import BytesIO
import os

max_tokens = 4000

# Set page title and favicon
st.set_page_config(page_title="Maestro - Opus-Haiku Task Manager", page_icon=":robot_face:")

# Display the title and introduction
st.title("Maestro: Achieving Goals with Opus' Orchestration of Haiku' subagents")
st.write("Maestro is a framework for Claude Opus to orchestrate subagents. Simply ask for a goal, and Opus will break it down and intelligently orchestrate instances of Haiku to execute subtasks, which Opus will review at the end.")
st.write("By Patricio Mainardi (@pmainardi), adapted from Pietro Schirano (@skirano)")

# Set up the Anthropic API client
@st.cache_resource
def get_anthropic_client(api_key):
    return Anthropic(api_key=api_key)

# Define Opus Orchestrator function
# Define Opus Orchestrator function
def opus_orchestrator(client, objective, messages=None, previous_results=None):
    try:
        st.subheader(f"\nCalling Opus for your objective")
        previous_results_text = "\n".join(previous_results) if previous_results else "None"
        messages_with_objective = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Based on the following objective and the previous sub-task results (if any), please break down the objective into the next sub-task, and create a concise and detailed prompt for a subagent so it can execute that task, please assess if the objective has been fully achieved. If the previous sub-task results comprehensively address all aspects of the objective, include the phrase 'The task is complete:' at the beginning of your response. If the objective is not yet fully achieved, break it down into the next sub-task and create a concise and detailed prompt for a subagent to execute that task.:\n\nObjective: {objective}\n\nPrevious sub-task results:\n{previous_results_text}"}
                ] + messages
            }
        ]

        opus_response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=max_tokens,
            messages=messages_with_objective
        )

        response_text = opus_response.content[0].text
        if "The task is complete:" not in response_text:
            st.markdown(f"Opus Orchestrator:\n{response_text}\n\nSending task to Haiku 👇")
        else:
            st.markdown(f"Opus Orchestrator:\n{response_text}")
        return response_text
    except Exception as e:
        st.error(f"Error in opus_orchestrator: {str(e)}")
        return None
    
# Define Haiku Sub-agent function
def haiku_sub_agent(client, prompt, previous_haiku_tasks=None):
    try:
        if previous_haiku_tasks is None:
            previous_haiku_tasks = []

        system_message = "Previous Haiku tasks:\n" + "\n".join(previous_haiku_tasks)

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt}
                ]
            }
        ]

        haiku_response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=max_tokens,
            messages=messages,
            system=system_message
        )

        response_text = haiku_response.content[0].text
        st.markdown(f"Haiku Sub-agent Result:\n{response_text}\n\nTask completed, sending result to Opus 👇")
        return response_text
    except Exception as e:
        st.error(f"Error in haiku_sub_agent: {str(e)}")
        return None

# Define Opus Refine function
def opus_refine(client, objective, messages, sub_task_results):
    try:
        st.subheader(f"\nCalling Opus to provide the refined final output for your objective:")
        messages_with_results = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": f"Objective: {objective}\n\nSub-task results:\n" + "\n".join(sub_task_results) + "\n\nPlease review and refine the sub-task results into a cohesive final output. add any missing information or details as needed. When working on code projects make sure to include the code implementation by file."}
                ] + messages
            }
        ]

        opus_response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=max_tokens,
            messages=messages_with_results
        )

        response_text = opus_response.content[0].text
        st.markdown(f"Final Output:\n{response_text}")
        return response_text
    except Exception as e:
        st.error(f"Error in opus_refine: {str(e)}")
        return None
    
# Function to read file content
def read_file(file_path):
    try:
        with open(file_path, 'r') as file:
            content = file.read()
        return content
    except FileNotFoundError:
        st.error(f"File not found: {file_path}")
        return None
    except IOError as e:
        st.error(f"Error reading file: {str(e)}")
        return None

# Function to validate the API key
def validate_api_key(api_key):
    try:
        client = Anthropic(api_key=api_key)
        
        # Make a simple API request to validate the key
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Hi"}
                    ]
                }
            ]
        )
        
        return True
    except Exception as e:
        st.error("Invalid API key. Please check your API key and try again. Error")
        return False

def main():
    # Get the Anthropic API key from the user
    api_key = st.text_input("Enter your Anthropic API key:", type="password",help="⚠️ Please note that your API key is not stored, saved, or transmitted outside of this page and the necessary interactions with Anthropic's API. Your key remains confidential.")
    if not api_key:
        st.warning("Please enter your Anthropic API key to continue. Go to https://console.anthropic.com/ to get one!")
        return

    # Validate the API key
    if not validate_api_key(api_key):
        return

    client = get_anthropic_client(api_key)

    # Get the objective from the user
    objective = st.text_area("Enter your objective:")
    
    # Allow the user to upload a text file (optional)
    uploaded_file = st.file_uploader("Choose a text file (optional)", type=["txt", "doc", "docx", "pdf", "md", "html", "csv", "json"], accept_multiple_files=False)
    
    # Allow the user to upload an image file (optional)
    image_file = st.file_uploader("Upload image (optional)", type=["jpg", "jpeg", "png", "gif", "bmp", "tiff", "svg", "webp"], accept_multiple_files=False)
    messages = []

    # Process the uploaded image file
    if image_file:
        img = Image.open(image_file)
        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        st.image(img, caption=image_file.name, use_column_width=True)
        messages.append(
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/png",
                    "data": img_str
                }
            }
        )

    # Process the uploaded text file
    if uploaded_file is not None:
        file_content = uploaded_file.read().decode("utf-8")
        objective = f"{objective}\n\n{file_content}"

    # Allow the user to toggle the option to download the full exchange log
    Download_Log = st.checkbox(label="Download Full Exchange Log", value=True)

    # Start task execution when the user clicks the button
    if st.button("Start Task Execution"):
        if not objective:
            st.warning("Please enter an objective to start the task execution.")
            return

        task_exchanges = []
        haiku_tasks = []

        stop_button = st.button("Stop Execution")

        while not stop_button:
            previous_results = [result for _, result in task_exchanges]
            opus_result = opus_orchestrator(client, objective, messages, previous_results)

            if opus_result is None:
                break

            if "The task is complete:" in opus_result:
                break
            else:
                sub_task_prompt = opus_result
                sub_task_result = haiku_sub_agent(client, sub_task_prompt, haiku_tasks)
                if sub_task_result is None:
                    break
                haiku_tasks.append(f"Task: {sub_task_prompt}\nResult: {sub_task_result}")
                task_exchanges.append((sub_task_prompt, sub_task_result))

        refined_output = opus_refine(client, objective, messages, [result for _, result in task_exchanges])

        if refined_output is None:
            st.error("Failed to generate the refined final output.")
        else:
            output_path_msg = ""
            if Download_Log:
                exchange_log = f"Objective: {objective}\n\n"
                if uploaded_file is not None:
                    exchange_log += f"Text File: {uploaded_file.name}\n\n"
                else:
                    exchange_log += "Text File: None\n\n"
                if image_file is not None:
                    exchange_log += f"Image: {image_file.name}\n\n"
                else:
                    exchange_log += "Image: None\n\n"
                exchange_log += "=" * 40 + " Task Breakdown " + "=" * 40 + "\n\n"
                for i, (prompt, result) in enumerate(task_exchanges, start=1):
                    exchange_log += f"Task {i}:\n"
                    exchange_log += f"Prompt: {prompt}\n"
                    exchange_log += f"Result: {result}\n\n"
            
                exchange_log += "=" * 40 + " Refined Final Output " + "=" * 40 + "\n\n"
                exchange_log += refined_output
            
                sanitized_objective = re.sub(r'\W+', '_', objective)
                timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
                if sanitized_objective:
                    filename = f"Maestro_{timestamp}_{sanitized_objective[:50]}.md" if len(sanitized_objective) > 50 else f"{timestamp}_{sanitized_objective}.md"
                else:
                    filename = f"Maestro_{timestamp}_output.md"
            
                # Get the full path of the output file
                output_path = os.path.join(os.getcwd(), filename)
                output_path_msg = f" Output file saved at: {output_path}"
            
                with open(filename, 'w', encoding='utf-8') as file:
                    file.write(exchange_log)
            st.success(f"Task execution completed!{output_path_msg}")

if __name__ == "__main__":
    main()
