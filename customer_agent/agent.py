import warnings

from google.genai import types
from google.adk.agents import Agent

from .config import MODEL_NAME, MODEL_MAX_TOKENS, MODEL_TEMPERATURE
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
    model=MODEL_NAME,
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
