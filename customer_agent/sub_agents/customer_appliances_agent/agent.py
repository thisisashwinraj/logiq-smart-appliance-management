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
import json
import warnings
from typing import Optional
from datetime import datetime

from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.lite_llm import LiteLlm

from ...config import (
    MODEL_GEMINI_2_5_FLASH, 
    MODEL_MAX_TOKENS, 
    MODEL_TEMPERATURE
)
from .prompts import CUSTOMER_APPLIANCES_AGENT_INSTRUCTIONS

from ...tools.customer_agent_tools import (
    get_all_customer_appliances_tool,
    get_appliance_specifications_tool,
    update_customer_appliance_details_tool,
    delete_customer_appliance_tool,
    get_all_customer_appliances_callback_func,
)

warnings.filterwarnings("ignore")


def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    state = callback_context.state

    if "customer_appliances" not in state:
        try:
            customer_appliances = get_all_customer_appliances_callback_func(
                customer_id=callback_context.state["customer_id"],
                limit=-1,
            )
        except Exception as error:
            customer_appliances = {
                "Data Unavailable. Use `get_all_customer_appliances_tool()`"}

        state["customer_appliances"] = customer_appliances

    if "start_time" not in state:
        state["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if "current_date" not in state:
        state["current_date"] = datetime.now().strftime("%Y-%m-%d")

    return None


customer_appliances_agent = Agent(
    name="customer_appliances_agent",
    model=MODEL_GEMINI_2_5_FLASH,
    description="""
    Agent to help customers query and update details of their registered 
    appliances. This agent can NOT register a new appliances, but can delete an 
    existing appliance from the user's profile.
    """,
    instruction=CUSTOMER_APPLIANCES_AGENT_INSTRUCTIONS,
    include_contents="default",
    generate_content_config=types.GenerateContentConfig(
        temperature=MODEL_TEMPERATURE,
        max_output_tokens=MODEL_MAX_TOKENS,
    ),
    tools=[
        get_all_customer_appliances_tool,
        get_appliance_specifications_tool,
        update_customer_appliance_details_tool,
        delete_customer_appliance_tool,
    ],
    before_agent_callback=before_agent_callback,
)
