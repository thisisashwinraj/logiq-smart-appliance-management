import warnings
from typing import Optional
from datetime import datetime

from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext

from ...config import MODEL_NAME, MODEL_MAX_TOKENS, MODEL_TEMPERATURE
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

    return None


product_enquiry_agent = Agent(
    name="product_enquiry_agent",
    model=MODEL_NAME,
    description="""
    Agent to help customers query details of various different appliances. This 
    agent does not answer queries related to customer-appliances; instead, it 
    queries details about all appliances from multiple brands registered with 
    LogIQ.
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
