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

import logging
import warnings
import streamlit as st
from typing import Optional
from datetime import datetime
from dotenv import load_dotenv

from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext

from .config import NAVIGATION_AGENT_MODEL
from .config import NAVIGATION_AGENT_MAX_TOKENS, NAVIGATION_AGENT_TEMPERATURE
from .prompts import NAVIGATION_AGENT_DESCRIPTION, NAVIGATION_AGENT_INSTRUCTION

from .tools import (
    get_directions, 
    get_weather, 
    get_traffic_eta, 
    get_customer_address
)
from ...tools import fetch_engineer_details_by_id

load_dotenv()
warnings.filterwarnings("ignore", category=UserWarning, module=".*pydantic.*")
logger = logging.getLogger(__name__)


def before_agent_callback(
    callback_context: CallbackContext
) -> Optional[types.Content]:
    state = callback_context.state

    if "engineer_id" not in state:
        try:
            state["engineer_id"] = st.session_state.get("engineer_id", "")
        except:
            state["engineer_id"] = "Not Available"

    if "engineer_full_name" not in state:
        engineer_details = None

        try:
            engineer_details = fetch_engineer_details_by_id(
                state["engineer_id"]
            )

            engr_first_name = engineer_details.get("first_name", "")
            engr_last_name = engineer_details.get("last_name", "")
            
            state["engineer_full_name"] =  f"{engr_first_name} {engr_last_name}"
        
        except Exception as error:
            state["engineer_full_name"] = "Not Available"
    
    if "engineer_address" not in state:
        try:
            if not engineer_details:
                engineer_details = fetch_engineer_details_by_id(
                    state["engineer_id"]
                )

            street = engineer_details.get("street", "") 
            city = engineer_details.get("city", "")
            district = engineer_details.get("district", "") 
            region = engineer_details.get("state", "")
            zipcode = engineer_details.get("zip_code", "")

            address = f"{street}, {city}, {district}, {region}-{zipcode}"
            state["engineer_address"] = address

        except Exception as error:
            state["engineer_address"] = "Not Available"

    if "current_date" not in state:
        state["current_date"] = datetime.now().strftime("%Y-%m-%d")

    return None


navigation_agent = Agent(
    name="navigation_agent",
    model=NAVIGATION_AGENT_MODEL,
    description=NAVIGATION_AGENT_DESCRIPTION,
    instruction=NAVIGATION_AGENT_INSTRUCTION,
    include_contents="default",
    generate_content_config=types.GenerateContentConfig(
        temperature=NAVIGATION_AGENT_TEMPERATURE,
        max_output_tokens=NAVIGATION_AGENT_MAX_TOKENS,
    ),
    tools=[
        get_directions,
        get_weather,
        get_traffic_eta,
        get_customer_address
    ],
    before_agent_callback=before_agent_callback,
)
