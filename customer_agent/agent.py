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

import os
import logging
import warnings
import streamlit as st
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv
from google.adk.agents.callback_context import CallbackContext

from google.genai import types
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm

from .config import MODEL_GEMINI_2_5_FLASH, MODEL_MAX_TOKENS, MODEL_TEMPERATURE
from .prompts import ROOT_AGENT_INSTRUCTIONS, GLOBAL_INSTRUCTIONS

from .sub_agents.appliance_support_and_troubleshooting_agent.agent import (
    appliance_support_and_troubleshooting_agent
)
from .sub_agents.customer_appliances_agent.agent import customer_appliances_agent
from .sub_agents.product_enquiry_agent.agent import product_enquiry_agent
from .sub_agents.register_appliance_agent.agent import register_appliance_agent
from .sub_agents.register_onsite_service_request.agent import (
    register_onsite_service_request_agent
)
from .sub_agents.service_requests_agent.agent import service_requests_agent
from .sub_agents.update_customer_profile_agent.agent import (
    update_customer_profile_agent
)
from .tools.customer_agent_tools import fetch_customer_details_by_id

load_dotenv()
warnings.filterwarnings("ignore")


def before_agent_callback(
    callback_context: CallbackContext
) -> Optional[types.Content]:
    state = callback_context.state

    if "customer_id" not in state:
        state["customer_id"] = st.session_state.get("customer_id", "")
        print(f"Customer Id: {state['customer_id']}")

    if "customer_full_name" not in state:
        try:
            customer_details = fetch_customer_details_by_id(state["customer_id"])
            state["customer_full_name"] = customer_details.get("first_name", "") + " " + customer_details.get("last_name", "")
            logging.info(state["customer_full_name"])

        except Exception as error: 
            logging.error(error)

    if "start_time" not in state:
        state["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if "current_date" not in state:
        state["current_date"] = datetime.now().strftime("%Y-%m-%d")

    return None


root_agent = LlmAgent(
    name="customer_agent",
    model=MODEL_GEMINI_2_5_FLASH,
    description="""
    Customer service agent for LogIQ - a customer support application for 
    household appliances like refrigerators, gas ranges, microwave ovens etc.
    """,
    instruction=ROOT_AGENT_INSTRUCTIONS,
    include_contents="default",
    generate_content_config=types.GenerateContentConfig(
        temperature=MODEL_TEMPERATURE,
        max_output_tokens=MODEL_MAX_TOKENS,
    ),
    sub_agents=[
        appliance_support_and_troubleshooting_agent,
        customer_appliances_agent,
        product_enquiry_agent,
        register_appliance_agent,
        register_onsite_service_request_agent,
        service_requests_agent,
        update_customer_profile_agent,
    ],
    global_instruction=GLOBAL_INSTRUCTIONS,
    before_agent_callback=before_agent_callback,
)
