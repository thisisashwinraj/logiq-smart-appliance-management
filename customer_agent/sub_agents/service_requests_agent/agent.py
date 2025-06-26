import warnings
from typing import Optional
from datetime import datetime

from google.genai import types
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext

from ...config import MODEL_NAME, MODEL_MAX_TOKENS, MODEL_TEMPERATURE
from .prompts import ONSITE_SERVICE_REQUEST_AGENT_INSTRUCTIONS

from ...tools.customer_agent_tools import (
    get_all_service_requests_briefs_tool,
    get_service_request_details_tool,
    update_service_request_details_tool,
    delete_service_request_tool,
    get_all_service_requests_briefs_callback_func,
)

warnings.filterwarnings("ignore")


def before_agent_callback(callback_context: CallbackContext) -> Optional[types.Content]:
    state = callback_context.state

    if "customer_service_requests" not in state:
        try:
            service_requests = get_all_service_requests_briefs_callback_func(
                customer_id=callback_context.state["customer_id"],
                limit=-1,
            )

        except Exception as error:
            service_requests = {
                "Data Unavailable. Use get_all_service_requests_briefs_tool()"}
            
        state["customer_service_requests"] = service_requests

    if "start_time" not in state:
        state["start_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if "current_date" not in state:
        state["current_date"] = datetime.now().strftime("%Y-%m-%d")

    return None


service_requests_agent = Agent(
    name="service_requests_agent",
    model=MODEL_NAME,
    description="""
    Agent to help customers query and update details of their service requests. 
    This agent can NOT register a new service request ticket, but can update or 
    delete existing requests from the customer's profile.
    """,
    instruction=ONSITE_SERVICE_REQUEST_AGENT_INSTRUCTIONS,
    include_contents="default",
    generate_content_config=types.GenerateContentConfig(
        temperature=MODEL_TEMPERATURE,
        max_output_tokens=MODEL_MAX_TOKENS,
    ),
    tools=[
        get_all_service_requests_briefs_tool,
        get_service_request_details_tool,
        update_service_request_details_tool,
        delete_service_request_tool,
    ],
    before_agent_callback=before_agent_callback,
)
