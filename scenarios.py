
from openai import OpenAI
import streamlit as st
import re
from utils import *
from vector_store import *
from attributes import *
import numpy as np

# Scenario 0: raw GPT output
client = OpenAI(api_key=openai_api_key)


def need_summarization_wrapper(message_history: list[dict]) -> dict:

    # read in system setup
    # prepare the prompt for detecting user intent
    system_msg = read_txt_file('prompt_messages/customer_need_sum_system_message.txt')
    system_msg = "\n".join([system_msg,
                            ""])
    prompt = [{"role": "system", "content": system_msg}]

    # reorganize the input message to ensure the format adhere to gpt
    user_info_history = " ".join([msg['text'] for msg in message_history if msg['role'] == 'user'])
    current_status = "\n".join(["SCENARIO CLASSIFICATION: ", st.session_state.scenario_flag, "\nSLOT FILLING: ",
                                    " ".join([i[0]+": "+i[1] for i in st.session_state.preferences.items() if
                                              i[1] != 'N/A' or i[1] != ""])])

    prompt = prompt + [{"role": "user", "content": user_info_history + '\n' + current_status + "\n SUMMARIZATION: "}]

    # generate response
    response = client.chat.completions.create(model="gpt-4",
                                              messages=prompt)
    msg = response.choices[0].message.content

    msg = msg[:CLIP_STRING_LENGTH]

    return msg


def information_collector_wrapper(message_history: list[dict]) -> dict:

    # read in system setup
    # prepare the prompt for detecting user intent
    system_msg = read_txt_file('prompt_messages/info_collector.txt')
    system_msg = "\n".join([system_msg,
                            ""])
    prompt = [{"role": "system", "content": system_msg}]

    # reorganize the input message to ensure the format adhere to gpt
    user_info_history = " ".join([msg['text'] for msg in message_history if msg['role'] == 'user'])
    if st.session_state.scenario_flag == 'N/A':
        current_status = "\n".join(["SCENARIO CLASSIFICATION: MISSING\n", "SLOT FILLING: ", " ".join([i[0] + ": MISSING" for i in st.session_state.preferences.items() if i[1] == 'N/A' or i[1] == ""])])
    else:
        current_status = "\n".join(["SCENARIO CLASSIFICATION: ", st.session_state.scenario_flag, "\nSLOT FILLING: ",
                                    " ".join([i[0] + ": MISSING" for i in st.session_state.preferences.items() if
                                              i[1] == 'N/A' or i[1] == ""])])

    prompt = prompt + [{"role": "user", "content": user_info_history + '\n' + current_status + "\n FOLLOW UP QUESTION: "}]

    st.write("CURRENT STATUS:", current_status)

    # generate response
    response = client.chat.completions.create(model="gpt-4",
                                              messages=prompt)
    msg = response.choices[0].message.content

    return {'text': msg, 'images': []}


def recommended_items_reranking(input_items, selected_items=10):

    items = input_items[:selected_items]

    return items


def recommend_based_on_need(user_need):

    # load image index
    # loading
    image_index = st.session_state.image_index

    # get results
    retrieval_results_raw = image_retrieval_from_text(image_index=image_index, text_query=user_need, similarity_top_k=100,
                                                  image_similarity_top_k=200)

    # randomly shuffle or reranking
    retrieval_results = recommended_items_reranking(retrieval_results_raw, selected_items=3)

    # generate standard output
    images_path = [res.node.metadata["file_path"] for res in retrieval_results]
    images_info = [res.node.metadata for res in retrieval_results]
    # {'text': msg, 'images': []}

    # generate text description
    text_descriptions = generate_image_description(images_info)

    return {'text': text_descriptions, 'images': images_path}


def customer_satis_check(message_history):

    # read in system setup
    # prepare the prompt for detecting user intent
    system_msg = read_txt_file('prompt_messages/satis_check_system_message.txt')
    system_msg = "\n".join([system_msg,
                            "Output format:\n\n LABEL: SATISFIED, NOT-SATISFIED, UNKNOWN.\n Justification: XXXX"])
    prompt = [{"role": "system", "content": system_msg}]

    # reorganize the input message to ensure the format adhere to gpt
    user_info_history = " ".join([msg['text'] for msg in message_history if msg['role'] == 'user'])

    prompt = prompt + [{"role": "user", "content": user_info_history + "\n LABEL: "}]

    # print(prompt)

    # generate response
    response = client.chat.completions.create(model="gpt-4",
                                              messages=prompt)
    msg = response.choices[0].message.content.split('\n')[0]

    # print(msg)

    # satis label
    satisfied_label = ''
    if 'NOT' in msg:
        satisfied_label = 'not_satisfied'
    elif 'UN' in msg:
        satisfied_label = 'unknown'
    else:
        satisfied_label = 'satisfied'

    return satisfied_label


def message_rewrite_satisfied(original_msg, satis_label):

    # read in system setup
    # prepare the prompt for detecting user intent
    system_msg = read_txt_file('prompt_messages/satis_rewrite_system_message.txt')
    system_msg = "\n".join([system_msg,
                            ""])

    prompt = [{"role": "system", "content": system_msg}]

    prompt = prompt + [{"role": "user", "content": f"Original Message:\n {original_msg} \n\n Satisfy Level: {satis_label} \n\n Rewrite Message: "}]

    # print(prompt)

    # generate response
    response = client.chat.completions.create(model="gpt-4",
                                              messages=prompt)
    msg_rewrite = response.choices[0].message.content

    return msg_rewrite


def seasonal_recommendation_wrapper(user_need, message_history):

    # first get the user need

    customer_mood = customer_satis_check(message_history=message_history)
    st.session_state.monitoring['satisfied_label'] = customer_mood

    # st.write(st.session_state.monitoring['satisfied_label'])
    # st.write(message_history)

    if st.session_state.monitoring['satisfied_label'] == 'N/A':
        retrieval_results = recommend_based_on_need(user_need)
        response = retrieval_results
    else:
        # check mood
        customer_mood = customer_satis_check(message_history=message_history)
        st.session_state.monitoring['satisfied_label'] = customer_mood
        st.write(customer_mood)

        if customer_mood in ['not_satisfied', 'unknown']:
            retrieval_results = recommend_based_on_need(user_need)
            msg_rewrite = message_rewrite_satisfied(retrieval_results['text'], customer_mood)
            response = {'text': msg_rewrite, 'images': retrieval_results['images']}
        else:
            response = {"text": "If you need any further modifications or more information, please let me know!", "images": []}

    return response


def event_recommendation_wrapper(user_need, message_history):

    # load image index
    # loading
    image_index = st.session_state.image_index

    # get results
    retrieval_results = image_retrieval_from_text(image_index=image_index, text_query=user_need)

    # generate standard output
    images_path = [res.node.metadata["file_path"] for res in retrieval_results]
    images_info = [res.node.metadata for res in retrieval_results]
    # {'text': msg, 'images': []}

    # generate text description
    text_descriptions = generate_image_description(images_info)

    # # read in system setup
    # # prepare the prompt for detecting user intent
    # system_msg = read_txt_file('prompt_messages/info_collector.txt')
    # system_msg = "\n".join([system_msg,
    #                         ""])
    # prompt = [{"role": "system", "content": system_msg}]
    #
    # # reorganize the input message to ensure the format adhere to gpt
    # message_history_gpt = prompt + [{"role": msg['role'], "content": msg['text']} for msg in message_history]
    #
    # # generate response
    # response = client.chat.completions.create(model="gpt-4",
    #                                           messages=message_history_gpt)
    # msg = response.choices[0].message.content

    return {'text': text_descriptions, 'images': images_path}


def generate_image_description(images_info):

    # prepare the prompt for detecting user intent
    system_msg = read_txt_file('./prompt_messages/description_generation_system_message.txt')
    system_msg = "\n".join([system_msg,
                            "You might be provided with multiple products, combine the introduction to them together."])
    prompt = [{"role": "system", "content": system_msg}]

    # include user response
    # get meta info for each product
    images_meta = []
    for idx, image in enumerate(images_info):
        try:
            images_meta.append("Product "+str(idx)+":\n"+" ".join([i[0]+': '+i[1] for i in image.items() if 'file' not in i[0] and 'date' not in i[0]]))
        except:
            st.write(image)

    prompt += [{"role": "user", "content": "we provide you with the following information: "+"\n\n".join(images_meta)}]

    # generate response
    image_description_raw = client.chat.completions.create(model="gpt-4",
                                                           messages=prompt)

    # post processing
    image_description = image_description_raw.choices[0].message.content

    return image_description


def image_retrieval_from_image(image_index, image, top_k=3):

    # generate image retrieval results
    retriever_engine = image_index.as_retriever(image_similarity_top_k=top_k)

    # retrieve more information from the GPT4V response
    retrieval_results = retriever_engine.image_to_image_retrieve(image)

    return retrieval_results


def image_retrieval_from_text(image_index, text_query, similarity_top_k=3, image_similarity_top_k=5):

    # generate image retrieval results
    retriever_engine = image_index.as_retriever(similarity_top_k=similarity_top_k, image_similarity_top_k=image_similarity_top_k)

    # retrieve more information from the GPT4V response
    retrieval_results = retriever_engine.retrieve(text_query)

    return retrieval_results


def image_to_image_retrieval_wrapper(message_history):

    # load image index
    # loading
    image_index = st.session_state.image_index

    # get the last figure
    images = [i['images_mapping'] for i in message_history if 'images_mapping' in i]
    images = [j for i in images for j in i]

    # get results
    retrieval_results = []
    for image in images:
        retrieval_results += image_retrieval_from_image(image_index=image_index, image=image['image_local_path'])

    # generate standard output
    images_path = [res.node.metadata["file_path"] for res in retrieval_results]
    images_info = [res.node.metadata for res in retrieval_results]
    # {'text': msg, 'images': []}

    # generate text description
    text_descriptions = generate_image_description(images_info)

    return {"text": text_descriptions, "images": images_path}


def preference_collector(message_history):

    # read in system setup
    # prepare the prompt for detecting user intent
    system_msg = read_txt_file('./prompt_messages/preference_filler.txt')
    system_msg = "\n".join([system_msg,
                            ""])
    prompt = [{"role": "system", "content": system_msg}]

    # print(system_msg)

    # reorganize the input message to ensure the format adhere to gpt
    all_user_answers = ' '.join([msg['text'] for msg in message_history if msg['role'] == 'user'])
    message_history_gpt = prompt + [{"role": "user", "content": "CURRENT SLOT FILLING SITUATION:\n"+st.session_state.preferences}]

    # generate response
    response = client.chat.completions.create(model="gpt-4",
                                              messages=message_history_gpt)
    msg = json.loads(response.choices[0].message.content)

    msg = {'text': msg, 'images': []}
    return msg


def preference_filler(message_history):

    # read in system setup
    # prepare the prompt for detecting user intent
    system_msg = read_txt_file('./prompt_messages/preference_filler.txt')
    system_msg = "\n".join([system_msg,
                            ""])
    prompt = [{"role": "system", "content": system_msg}]

    # print(system_msg)

    # reorganize the input message to ensure the format adhere to gpt
    all_user_answers = ' '.join([msg['text'] for msg in message_history if msg['role'] == 'user'])
    message_history_gpt = prompt + [{"role": "user", "content": "USER CONVERSATION:\n"+all_user_answers+"FILLED SLOTS:"}]

    # generate response
    count = 0
    msg = None
    while count <= ERROR_MAXIMUM_TRY_OUT:
        response = client.chat.completions.create(model="gpt-4",
                                                  messages=message_history_gpt)
        # st.write(response)
        try:
            msg = json.loads(response.choices[0].message.content)
        except:
            count = count + 1
        if msg:
            break

    if msg is None:
        msg = {i: "N/A" for i in PREFERENCE_SLOTS}

    return msg


def generic_recommendation_wrapper(message_history: list[dict]) -> dict:

    # read in system setup
    # prepare the prompt for detecting user intent
    system_msg = read_txt_file('prompt_messages/generic_recommendation_system_message.txt')
    system_msg = "\n".join([system_msg,
                            ""])
    prompt = [{"role": "system", "content": system_msg}]

    # reorganize the input message to ensure the format adhere to gpt
    message_history_gpt = prompt + [{"role": msg['role'], "content": msg['text']} for msg in message_history]

    # generate response
    response = client.chat.completions.create(model="gpt-4",
                                              messages=message_history_gpt)
    msg = response.choices[0].message.content

    return {'text': msg, 'images': []}
