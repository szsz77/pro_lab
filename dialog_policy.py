from scenarios import *
import streamlit as st
from front_end_show import *
import uuid
from PIL import Image
from openai import OpenAI
from utils import *
import re
import os
from attributes import *

client = OpenAI(api_key=openai_api_key)

def load_welcome_message():
    # TODO: set up system message

    welcome_message = load_from_json("prompt_messages/welcome_message.json")

    if "messages" not in st.session_state:
        st.session_state["messages"] = [{"role": "assistant",
                                         "text": welcome_message['welcome_message'],
                                         "images": []}]

        # prepare some states
        # a global state for identifying the scenario
        st.session_state['scenario_flag'] = "N/A"

        # a global state to understand the preferences
        st.session_state['preferences_history'] = []
        st.session_state['preferences'] = {i: "" for i in PREFERENCE_SLOTS}

        # some counts
        st.session_state['counts'] = {"scenario_detection_counts": 0, "preference_detection_counts": 0, "info_collection_counts": 0}

        # quality control
        st.session_state['monitoring'] = {'satisfied_label': 'N/A'}

        # load index
        with st.spinner('Preparing Your AI Fashion Stylist (loading vector index) ...'):
            # @st.cache_resource(show_spinner=False)
            # def load_vector_index():
            st.session_state['image_index'] = load_index(persist_dir=VECTOR_STORE_PATH)
            # load_vector_index()

            @st.cache_resource(show_spinner=False)
            def load_vector_index():
                return load_index(persist_dir=VECTOR_STORE_PATH)

            if 'image_index' not in st.session_state:
                st.session_state['image_index'] = load_vector_index()


def detect_scenario(message_history):

    # message history reorganize
    message_history_gpt = message_history_reformat_gpt(message_history)

    # prepare the prompt for detecting user intent
    system_msg = read_txt_file('./prompt_messages/scenario_detect_system_message.txt')
    system_msg = "\n".join([system_msg,
                            "Now, your job is to classify the user's first conversation into one of the above 4 scenarios.",
                            "Note: You should ONLY classify the whole conversation into ONE scenario when you are HIGHLY CONFIDENT. DO NOT output the scenario number when the provided information from the customer is not sufficient enough to make this judgement - you should output N/A instead.",
                            "Output format:\n\n Classification: Scenario XX or N/A.\n Justification: XXXX"])
    prompt = [{"role": "system", "content": system_msg}]

    # include user response
    prompt += [{"role": "user", "content": '\n'.join([i['content'] for i in message_history_gpt if i['role'] == 'user'])}]

    # generate response
    scenario_class_raw = client.chat.completions.create(model="gpt-4",
                                                        messages=prompt)

    # post processing
    scenario_class = scenario_class_raw.choices[0].message.content.split('\n')

    if len(scenario_class) != 2:
        scenario_flag = 'N/A'
    else:
        scenario_flag, scenario_explain = scenario_class
        scenario_flag = re.findall(r'\d+', scenario_flag)
        if scenario_flag:
            scenario_flag = 'situation_' + scenario_flag[0]
        else:
            scenario_flag = 'N/A'

    # st.write(scenario_class)

    return scenario_flag


def conversation_redirect(message_history, flag='situation_0'):
    """
    for a given message, detect its situation:
    situation 1: Proactive recommendation based on seasonality
    situation 2: Event-based recommendation
    situation 3: Open-ended Multi-modality Recommendation based on User’s preference
    situation 4: Style matching/complete your look recommendation
    :return:
    """

    # identify user intent

    # redirect
    situation_flag = detect_scenario(message_history=message_history)

    return situation_flag


def message_history_reformat_gpt(message_history):

    # reorganize the input message to ensure the format adhere to gpt
    message_history_gpt = [{"role": msg['role'], "content": msg['text']} for msg in message_history]

    return message_history_gpt

# upload images to a folder

def parse_user_input(prompt: dict) -> dict:

    # decouple text and images for further processing
    text = prompt['text']
    images = prompt['files']

    def save_upload_image(image_data):

        if not os.path.exists('./temp_images_upload/'):
            os.makedirs('./temp_images_upload/')

        image_id = str(uuid.uuid4())
        image_path = os.path.join('./temp_images_upload/', f"{image_id}.png")
        image_data.save(image_path)
        return image_path

    # save images and mapping relations
    images_mapping = []
    for image_obj in images:
        image = Image.open(image_obj)
        image_path = save_upload_image(image)
        # also get the corresponding info
        # images_mapping.append(json.loads(image.to_json))
        images_mapping.append({'upload_object': image_obj, 'image_local_path': image_path})
        # st.write(image_path)

    return {'text': text, 'images': images, 'images_mapping': images_mapping, 'situation_flag': 'N/A'}


def generate_response(message_history: list[dict]) -> dict:

    # information collection period
    if (st.session_state.scenario_flag == 'N/A' or (["N/A" or "" in st.session_state.preferences.values()])) and st.session_state.counts['info_collection_counts'] <= INFO_COLLECT_MAXIMUM_TRY_OUT:

        if message_history[-1]['images']:
            st.session_state.scenario_flag = 'situation_3'

        # check intent and slot filling conditions
        if st.session_state.scenario_flag == 'N/A':
            scenario_flag = detect_scenario(message_history)
            if scenario_flag != 'N/A':
                st.session_state.scenario_flag = scenario_flag
            # st.write(scenario_flag)

        slot_filling = preference_filler(message_history=message_history)
        st.session_state.preferences_history.append(slot_filling)
        for slot in PREFERENCE_SLOTS:
            slot_history = [i[slot] for i in st.session_state.preferences_history if slot in i and i[slot] != 'N/A']
            if slot_history:
                st.session_state.preferences[slot] = slot_history[-1]

        # provide slot
        # st.write(st.session_state.preferences)
        #
        response = information_collector_wrapper(message_history=message_history)

        st.session_state.counts['info_collection_counts'] += 1

        # st.write("HERE")
    else:

        # redirect period - reorganizing
        ## deal with no information
        if st.session_state.scenario_flag == 'N/A':
            st.session_state.scenario_flag = 'situation_1'

        # user need summarization
        user_need_sum = need_summarization_wrapper(message_history=message_history)

        # st.write(user_need_sum)

        response = {'text': '', 'images': []}
        # redirect
        if st.session_state.scenario_flag == 'situation_1':
            response = seasonal_recommendation_wrapper(user_need=user_need_sum, message_history=message_history)
        elif st.session_state.scenario_flag == 'situation_2':
            response = event_recommendation_wrapper(user_need=user_need_sum, message_history=message_history)
        elif st.session_state.scenario_flag == 'situation_3':
            response = image_to_image_retrieval_wrapper(message_history=message_history)
        elif st.session_state.scenario_flag == 'situation_4':
            response = generic_recommendation_wrapper(message_history=message_history)

    return response


