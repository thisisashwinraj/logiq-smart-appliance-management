import asyncio
import warnings

import streamlit as st
from datetime import datetime
from dotenv import load_dotenv

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from customer_agent.agent import root_agent


if "customer_id" not in st.session_state:
    st.session_state.customer_id = "testcustomer"

load_dotenv()
warnings.filterwarnings("ignore")

in_memory_session_service = InMemorySessionService()

initial_state = {
    "customer_full_name": "Amritha Raj",
    "customer_id": st.session_state.customer_id,
}


async def preprocess_response(event):
    if event.is_final_response():
        if (
            event.content
            and event.content.parts
            and hasattr(event.content.parts[0], "text")
            and event.content.parts[0].text
        ):
            return event.content.parts[0].text.strip()


async def call_agent_async(runner, user_id, session_id, query):
    content = types.Content(role="user", parts=[types.Part(text=query)])

    async for event in runner.run_async(
        user_id=user_id, session_id=session_id, new_message=content
    ):
        response = await preprocess_response(event)

        if response:
            print(f"AGENT: {response}")


async def main_async():
    APP_NAME = "LogIQ Customer Agent"
    USER_ID = "amritharaj"

    new_session = await in_memory_session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state=initial_state,
    )

    SESSION_ID = new_session.id
    print(f"Created new session: {SESSION_ID}")

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=in_memory_session_service,
    )

    print("\nWelcome to LogIQ's Customer Agent Chat!")
    print("Type 'exit' or 'quit' to end the conversation.\n")

    while True:
        user_input = input("USER: ")

        if user_input.lower() in ["exit", "quit", "bye"]:
            print("AGENT: Goodbye! Have a nice day.")
            break

        await call_agent_async(runner, USER_ID, SESSION_ID, user_input)


if __name__ == "__main__":
    asyncio.run(main_async())
