
import streamlit as st
from streamlit_carousel import carousel


def message_rendering(message, role):

    with st.chat_message(role):
        st.write(message['text'])
        if message['images']:
            # uploaded_files = []
            if len(message['images']) == 1:
                st.image(message['images'][0])
            elif len(message['images']) >= 2:
                carousel(items=[{'title': '', 'text': "", 'img': i}
                                for i in message['images']])
                # if not isinstance(img, str):
                #     uploaded_files.append([img.file_id, img.name, img.type])
