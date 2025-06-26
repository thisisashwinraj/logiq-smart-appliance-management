import warnings
from typing import Optional
from datetime import datetime

from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext

from ...config import MODEL_NAME, MODEL_MAX_TOKENS, MODEL_TEMPERATURE
from .prompts import UPDATE_CUSTOMER_PROFILE_AGENT_INSTRUCTIONS

from ...tools.customer_agent_tools import (
    get_customer_details_tool,
    update_customer_details_tool,
    validate_and_format_address_tool,
    get_customer_details_callback_func,
)

warnings.filterwarnings("ignore")


def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    state = callback_context.state

    if "customer_details" not in state:
        try:
            customer_details = get_customer_details_callback_func(
                customer_id=state["customer_id"],
            )
        except Exception as error:
            customer_details = {
                "Data Unavailable. Use get_customer_details_tool()"}

        state["customer_details"] = customer_details

    if "current_date" not in state:
        state["current_date"] = datetime.now().strftime("%Y-%m-%d")

    if "start_time" not in state:
        state["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return None


update_customer_profile_agent = Agent(
    name="update_customer_profile_agent",
    model=MODEL_NAME,
    description="""
    Agent to help customers update their personal profile and contact details. 
    This agent can update and query user's first and last name, date of birth, 
    address, gender, email and phone number of the customer.
    """,
    instruction=UPDATE_CUSTOMER_PROFILE_AGENT_INSTRUCTIONS,
    include_contents="default",
    generate_content_config=types.GenerateContentConfig(
        temperature=MODEL_TEMPERATURE,
        max_output_tokens=MODEL_MAX_TOKENS,
    ),
    tools=[
        get_customer_details_tool,
        update_customer_details_tool,
        validate_and_format_address_tool,
    ],
    before_agent_callback=before_agent_callback,
)
