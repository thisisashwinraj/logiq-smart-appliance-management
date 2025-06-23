import warnings
from typing import Optional
from datetime import datetime

from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext

from ...config import MODEL_NAME, MODEL_MAX_TOKENS, MODEL_TEMPERATURE
from .prompts import APPLIANCE_REGISTRATION_AGENT_INSTRUCTIONS

from ...tools.customer_agent_tools import (
    get_categories_tool,
    get_sub_categories_tool,
    get_brands_tool,
    get_models_tool,
    register_new_appliance_tool,
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

    timestamp = datetime.now()
    state["request_start_time"] = timestamp

    if "agent_name" not in state:
        state["agent_name"] = "Appliance Registration Agent"

    return None


register_appliance_agent = Agent(
    name="register_appliance_agent",
    model=MODEL_NAME,
    description="""
    Agent to help the customers register a new appliance to their profile. This 
    agent can NOT answer questions about appliance details.
    """,
    instruction=APPLIANCE_REGISTRATION_AGENT_INSTRUCTIONS,
    include_contents="default",
    generate_content_config=types.GenerateContentConfig(
        temperature=MODEL_TEMPERATURE,
        max_output_tokens=MODEL_MAX_TOKENS,
    ),
    tools=[
        get_categories_tool,
        get_sub_categories_tool,
        get_brands_tool,
        get_models_tool,
        register_new_appliance_tool,
    ],
    before_agent_callback=before_agent_callback,
)
