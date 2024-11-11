
import qdrant_client
from llama_index.core.readers import SimpleDirectoryReader
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import VectorStoreIndex, StorageContext, load_index_from_storage
from llama_index.core.indices import MultiModalVectorStoreIndex

import pandas as pd
import os
import json
import openai
from utils import *
import streamlit as st
from attributes import *

openai.api_key = openai_api_key

def preprocess_image_dir():

    # read meta info
    descriptions = json.loads(pd.read_csv("./fashion_dataset/articles.csv", dtype=str).to_json(orient='records'))
    descriptions_dict = {i['article_id']: i for i in descriptions}

    # get all documents
    documents = SimpleDirectoryReader("./fashion_dataset/images/", recursive=True).load_data()

    # augment with meta info
    for docu in documents:
        # image idx
        docu_idx = docu.metadata['file_path'].split('/')[-1].replace('.jpg', '')
        docu.metadata = docu.metadata | descriptions_dict[docu_idx]
        if docu.metadata['detail_desc'] is not None:
            docu.text = docu.metadata['detail_desc']
        else:
            docu.text = ''

    return documents


def randomly_sample_documents(documents, samples_path: str):

    # parse samples
    selected_meta = set(load_from_json(samples_path)['random_image_ids'])

    # select documents
    selected_documents = [i for i in documents if i.metadata['article_id'] in selected_meta]

    return selected_documents


def save_index(index, persist_dir):

    if not os.path.exists(persist_dir):
        os.makedirs(persist_dir)

    index.storage_context.persist(persist_dir=persist_dir)


def load_index(persist_dir):

    storage_context: StorageContext = StorageContext.from_defaults(
        persist_dir=persist_dir
    )

    index = load_index_from_storage(storage_context)
    return index


def setup_vector_store(documents, persist_dir):

    # set up qdrant client
    # client = qdrant_client.QdrantClient(path="qdrant_db")

    # create vector index for images
    # text_store = QdrantVectorStore(
    #     client=client, collection_name="text_collection"
    # )
    #
    # image_store = QdrantVectorStore(
    #     client=client, collection_name="image_collection"
    # )
    #
    # storage_context = StorageContext.from_defaults(
    #     vector_store=text_store, image_store=image_store,
    # )

    index = MultiModalVectorStoreIndex.from_documents(
        documents,
        # is_text_vector_store_empty=True,
        show_progress=True,
        # storage_context=storage_context,
    )

    # save vector index
    if persist_dir:
        save_index(index=index, persist_dir=persist_dir)

    return index

#
#
# if __name__ == "__main__":
#
#     setup_vector_store()
#
