import warnings
from typing import Optional
from datetime import datetime

from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext

from ...config import MODEL_NAME, MODEL_MAX_TOKENS, MODEL_TEMPERATURE
from .prompts import CUSTOMER_APPLIANCES_AGENT_INSTRUCTIONS

from ...tools.customer_agent_tools import (
    get_all_customer_appliances_tool,
    get_appliance_specifications_tool,
    update_customer_appliance_details_tool,
    delete_customer_appliance_tool,
)

warnings.filterwarnings("ignore")


def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    state = callback_context.state

    if "customer_appliances" not in state:
        try:
            customer_appliances = get_all_customer_appliances_tool(
                customer_id=callback_context.state["customer_id"],
                limit=-1,
            )
        except Exception as error:
            customer_appliances = {
                "Data Unavailable. Use get_all_customer_appliances_tool()"}

        state["customer_appliances"] = customer_appliances

    if "start_time" not in state:
        state["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print("\t...delegating to customer_appliances_agent()")

    return None


customer_appliances_agent = Agent(
    name="customer_appliances_agent",
    model=MODEL_NAME,
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
