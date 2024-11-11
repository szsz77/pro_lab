
import streamlit as st

from front_end_show import *
from scenarios import *
from dialog_policy import *

# with st.sidebar:

st.title("AI Fashion Stylist")

# starting the service
load_welcome_message()

for msg in st.session_state.messages:
    message_rendering(msg, role=msg['role'])

# interacting
if prompt := st.chat_input(accept_file="multiple", file_type=["png", "jpg"]):

    # if not openai_api_key:
    #     st.info("Please add your OpenAI API key to continue.")
    #     st.stop()

    # parse input message and rending
    parsed_input = parse_user_input(prompt)
    message_rendering(message=parsed_input, role="user")

    # store input message
    st.session_state.messages.append({"role": "user"} | parsed_input)

    # prepare response
    parsed_output = generate_response(st.session_state.messages)
    message_rendering(message=parsed_output, role="assistant")

    # store output response
    st.session_state.messages.append({"role": "assistant"} | parsed_output)

    # debugging
    # st.write('CHATBOT DEBUGGING')
    # st.write('current situation for this conversation')
    # st.write(st.session_state.messages)
    # st.write(st.session_state.scenario_flag)
    # st.write(st.session_state.preferences)


