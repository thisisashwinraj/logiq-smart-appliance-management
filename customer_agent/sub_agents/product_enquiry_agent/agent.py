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
from typing import Optional
from datetime import datetime

from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext

from ...config import (
    MODEL_GEMINI_2_5_FLASH, 
    MODEL_MAX_TOKENS, 
    MODEL_TEMPERATURE,
)
from .prompts import PRODUCT_ENQUIRY_AGENT_INSTRUCTIONS

from ...tools.customer_agent_tools import (
    get_appliance_specifications_tool,
    get_categories_tool,
    get_sub_categories_tool,
    get_filtered_appliances_tool,
)

warnings.filterwarnings("ignore")


def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    state = callback_context.state

    if "available_appliance_categories" not in state:
        available_categories = get_categories_tool()
        state["available_appliance_categories"] = available_categories

    if "start_time" not in state:
        state["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if "current_date" not in state:
        state["current_date"] = datetime.now().strftime("%Y-%m-%d")

    return None


product_enquiry_agent = Agent(
    name="product_enquiry_agent",
    model=MODEL_GEMINI_2_5_FLASH,
    description="""
    Agent to help customers query the details of various different appliances 
    offered by LogIQ. This agent does not answer queries related to customer 
    appliances; instead, it queries details about all appliances from multiple 
    brands registered with LogIQ. It can provide information about available 
    products/appliances, their specifications (such as dimensions, colors etc), 
    tagged price, and more.
    """,
    instruction=PRODUCT_ENQUIRY_AGENT_INSTRUCTIONS,
    include_contents="default",
    generate_content_config=types.GenerateContentConfig(
        temperature=MODEL_TEMPERATURE,
        max_output_tokens=MODEL_MAX_TOKENS,
    ),
    tools=[
        get_appliance_specifications_tool,
        get_sub_categories_tool,
        get_filtered_appliances_tool,
    ],
    before_agent_callback=before_agent_callback,
)
