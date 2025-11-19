# Copyright 2025 Ashwin Raj
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import io
import json
import time
import streamlit as st
from dotenv import load_dotenv

from google import genai
from google.genai import types
from google.cloud import storage
from google.oauth2.service_account import Credentials

load_dotenv()

    
def list_gcs_files(bucket_name: str):
    credentials = Credentials.from_service_account_info(
        json.loads(st.secrets["CLOUD_STORAGE_SERVICE_ACCOUNT_KEY"])
    )

    client = storage.Client(credentials=credentials)
    
    bucket = client.bucket(bucket_name)
    blobs = client.list_blobs(bucket_name)

    files = [blob.name for blob in blobs]
    return files


def get_service_manual(bucket_name: str, filename: str):
    credentials = Credentials.from_service_account_info(
        json.loads(st.secrets["CLOUD_STORAGE_SERVICE_ACCOUNT_KEY"])
    )

    client = storage.Client(credentials=credentials)

    bucket = client.bucket(bucket_name)
    blob = bucket.blob(filename)

    data = blob.download_as_bytes()
    return data


def _get_file_search_store():
    TROUBLESHOOT_GUIDE_FILE_SEARCH_STORE_UID = "fileSearchStores/troubleshootguidefilesearch-7rcpimuqqfn4"

    client = genai.Client()

    available_guide_file_search_stores = client.file_search_stores.list()
    available_file_search_stores = [
        store.name for store in available_guide_file_search_stores
    ]

    if TROUBLESHOOT_GUIDE_FILE_SEARCH_STORE_UID in available_file_search_stores:
        troubleshoot_guide_file_search_store = client.file_search_stores.get(
            name=TROUBLESHOOT_GUIDE_FILE_SEARCH_STORE_UID
        )

    else:
        troubleshoot_guide_file_search_store = client.file_search_stores.create(
            config={'display_name': "troubleshoot_guide_file_search_store"}
        )

        service_manuals = list_gcs_files("service_manual_bucket")

        for filename in service_manuals:
            try:
                file_bytes = get_service_manual("service_manual_bucket", filename)

                operation = client.file_search_stores.upload_to_file_search_store(
                    file=io.BytesIO(file_bytes),
                    file_search_store_name=troubleshoot_guide_file_search_store.name,
                    config={
                        'display_name' : filename,
                        'mime_type': "application/pdf",
                        'chunking_config': {
                            'white_space_config': {
                                'max_tokens_per_chunk': 300,
                                'max_overlap_tokens': 30
                            }
                        }
                    }
                )

                while not operation.done:
                    time.sleep(5)
                    operation = client.operations.get(operation)

            except Exception as error:
                return None  

    return troubleshoot_guide_file_search_store.name


def get_troubleshooting_help(query: str):
    """
    Tool to retrieve troubleshooting guidance for a given query using Gemini's 
    File Search powered Retrieval-Augmented Generation (RAG).

    This tool retrieves the active file search store containing appliance 
    manuals and technical documents to provide context-aware troubleshooting 
    assistance.

    Args:
        query (str): The user's troubleshooting question, symptom description, 
            error code, or repair-related query.

    Returns:
        dict: A response object with the following structure:
            - "status": "success" or "error".
            - "response": The generated troubleshooting guidance 
              (present only on success).
            - "message": Error details (present only on error).
    """
    try:
        client = genai.Client()
        file_search_store = _get_file_search_store()

        if file_search_store is None:
            return {
                "status": "error",
                "message": "Unable to find the file search store."
            }

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=query,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[file_search_store],
                        )
                    )
                ]
            )
        )

        return {
            "status": "success",
            "response": response.candidates[0].content,
        }

    except Exception as error:
        return {
            "status": "error",
            "message": f"An error occured: {error}"
        }
