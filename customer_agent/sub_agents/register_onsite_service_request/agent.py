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
    MODEL_TEMPERATURE
)
from .prompts import ONSITE_SERVICE_REQUEST_REGISTRATION_AGENT_INSTRUCTIONS

from ...tools.customer_agent_tools import (
    get_all_customer_appliances_tool,
    get_customer_address_tool,
    get_customer_email_tool, 
    get_customer_phone_number_tool, 
    register_onsite_service_request_tool, 
    validate_and_format_address_tool, 
)

warnings.filterwarnings("ignore")


def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    Simple callback that logs when the agent starts processing a request
    and initializes agent specific states.

    Args:
        callback_context: Contains state and context information

    Returns:
        None to continue with normal agent processing
    """
    state = callback_context.state

    if "start_time" not in state:
        state["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if "current_date" not in state:
        state["current_date"] = datetime.now().strftime("%Y-%m-%d")

    return None


register_onsite_service_request_agent = Agent(
    name="register_onsite_service_request_agent",
    model=MODEL_GEMINI_2_5_FLASH,
    description="""
    Agent to help customers register a new onsite service request ticket.
    """,
    instruction=ONSITE_SERVICE_REQUEST_REGISTRATION_AGENT_INSTRUCTIONS,
    include_contents="default",
    generate_content_config=types.GenerateContentConfig(
        temperature=MODEL_TEMPERATURE,
        max_output_tokens=MODEL_MAX_TOKENS,
    ),
    tools=[
        get_all_customer_appliances_tool, 
        get_customer_address_tool, 
        get_customer_email_tool, 
        get_customer_phone_number_tool, 
        register_onsite_service_request_tool, 
        validate_and_format_address_tool, 
    ],
    before_agent_callback=before_agent_callback,
)
