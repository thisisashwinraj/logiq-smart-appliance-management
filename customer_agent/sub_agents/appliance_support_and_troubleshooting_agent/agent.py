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

import warnings
import streamlit as st

from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools.retrieval.vertex_ai_rag_retrieval import VertexAiRagRetrieval

from vertexai import rag
from ...config import (
    MODEL_GEMINI_2_5_FLASH, 
    MODEL_MAX_TOKENS, 
    MODEL_TEMPERATURE,
)
from .prompts import APPLIANCE_SUPPORT_AND_TROUBLESHOOTING_AGENT_INSTRUCTIONS

load_dotenv()
warnings.filterwarnings("ignore")


def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    state = callback_context.state

    if "start_time" not in state:
        state["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if "current_date" not in state:
        state["current_date"] = datetime.now().strftime("%Y-%m-%d")

    return None


retrieve_service_manual_corpora_tool = VertexAiRagRetrieval(
    name="retrieve_service_manual_corpora_tool",
    description="""
    This tool leverages Vertex AI's Retrieval-Augmented Generation (RAG) 
    capabilities to intelligently search and retrieve relevant information from 
    a comprehensive corpus of service manuals and troubleshooting guides. It is 
    designed to provide contextual data to answer queries grounded in these 
    technical documents.
    """,
    rag_resources=[
        rag.RagResource(rag_corpus="projects/logiq-project/locations/us-central1/ragCorpora/2305843009213693952")
    ],
    similarity_top_k=5,
    vector_distance_threshold=0.6,
)


appliance_support_and_troubleshooting_agent = Agent(
    name="appliance_support_and_troubleshooting_agent",
    model=MODEL_GEMINI_2_5_FLASH,
    description="""
    Agent to assist customers by answering appliance-related queries limited to 
    usage, cleaning, maintenance, and general product information. This agent 
    ground answer based on available service manuals & troubleshooting guides.
    """,
    instruction=APPLIANCE_SUPPORT_AND_TROUBLESHOOTING_AGENT_INSTRUCTIONS,
    include_contents="default",
    generate_content_config=types.GenerateContentConfig(
        temperature=MODEL_TEMPERATURE,
        max_output_tokens=MODEL_MAX_TOKENS,
    ),
    tools=[retrieve_service_manual_corpora_tool],
    before_agent_callback=before_agent_callback,
)
