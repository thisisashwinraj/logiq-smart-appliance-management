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
import warnings

from google.genai import types
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm

from .config import MODEL_DEEPSEEK_V3, MODEL_MAX_TOKENS, MODEL_TEMPERATURE
from .prompts import ROOT_AGENT_INSTRUCTIONS, GLOBAL_INSTRUCTIONS

from .sub_agents.appliance_support_and_troubleshooting_agent.agent import (
    appliance_support_and_troubleshooting_agent,
)
from .sub_agents.customer_appliances_agent.agent import customer_appliances_agent
from .sub_agents.product_enquiry_agent.agent import product_enquiry_agent
from .sub_agents.register_appliance_agent.agent import register_appliance_agent
from .sub_agents.register_onsite_service_request.agent import (
    register_onsite_service_request_agent,
)
from .sub_agents.service_requests_agent.agent import service_requests_agent
from .sub_agents.update_customer_profile_agent.agent import (
    update_customer_profile_agent,
)

warnings.filterwarnings("ignore")


root_agent = Agent(
    name="customer_agent",
    model=LiteLlm(
        model=MODEL_DEEPSEEK_V3,
        api_key=os.getenv("OPENROUTER_API_KEY")
    ),
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
)
