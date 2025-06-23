import os
import asyncio
import streamlit as st
import time as py_time_module
from typing import Tuple
from dotenv import load_dotenv

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from customer_agent.agent import root_agent


dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

def _run_coroutine_in_new_loop(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        return loop.run_until_complete(coro)
    
    finally:
        loop.close()
        asyncio.set_event_loop(None) 


@st.cache_resource
def initialize_adk(user_id: str) -> Tuple:
    """
    Initializes the ADK Runner and InMemorySessionService for the application.
    Manages the unique ADK session ID within the Streamlit session state.
    Returns:
        tuple: (Runner instance, active ADK session ID)
    """
    APP_NAME = "LogIQ Customer App"

    initial_state = {
        "customer_full_name": "Amritha Raj",
        "customer_id": st.session_state.customer_id,
    }

    session_service = InMemorySessionService()
    print(f"--- ADK Init: InMemorySessionService instantiated. ---")

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    print(f"--- ADK Init: Runner instantiated for '{root_agent.name}'. ---")

    if 'adk_session_id' not in st.session_state:
        session_id = f"adk_session_{int(py_time_module.time())}_{os.urandom(4).hex()}"
        st.session_state['adk_session_id'] = session_id
        print(f"--- ADK Init: Generated new ADK session ID: {session_id} ---")

        try:
            _run_coroutine_in_new_loop(
                session_service.create_session(
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=session_id,
                    state=initial_state,
                )
            )
            print(f"--- ADK Init: Successfully created new session in ADK ---")

        except Exception as e:
            print(f"--- ADK Init: FATAL ERROR - Could not create session in ADK: {e} ---")
            raise

    else:
        session_id = st.session_state['adk_session_id']
        print(f"--- ADK Init: Reusing existing ADK session ID from streamlit state: {session_id} ---")
        
        existing_session = _run_coroutine_in_new_loop(
            session_service.get_session(app_name=APP_NAME, user_id=user_id, session_id=session_id)
        )

        if not existing_session:
            print(f"--- ADK Init: WARNING - Session {session_id} not found in InMemorySessionService memory (likely due to script restart). Recreating session. State will be lost. ---")
            
            try:
                _run_coroutine_in_new_loop(
                    session_service.create_session(
                        app_name=APP_NAME,
                        user_id=user_id,
                        session_id=session_id,
                        state=initial_state,
                    )
                )
                print(f"--- ADK Init: Successfully recreated session {session_id} in ADK SessionService. ---")
            
            except Exception as e:
                print(f"--- ADK Init: FATAL ERROR - Could not recreate missing session {session_id} in ADK SessionService: {e} ---")
                raise

    print(f"--- ADK Init: Initialization sequence complete. Runner is ready. Active Session ID: {session_id} ---")
    return runner, session_id


async def preprocess_response(event) -> str:
    if event.is_final_response():
        if (
            event.content
            and event.content.parts
            and hasattr(event.content.parts[0], "text")
            and event.content.parts[0].text
        ):
            return event.content.parts[0].text.strip()


async def run_adk_async(user_id: str, runner: Runner, session_id: str, user_message_text: str) -> str:
    """
    Asynchronously executes one turn of the ADK agent conversation.
    Args:
        runner: The initialized ADK Runner.
        session_id: The current ADK session ID.
        user_message_text: The text input from the user for this turn.
    Returns:
        The agent's final text response as a string.
    """
    content = genai_types.Content(
        role='user',
        parts=[genai_types.Part(text=user_message_text)]
    )

    final_response_text = "[Agent encountered an issue and did not produce a final response]"
    start_time = py_time_module.time()

    try:
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
            response = await preprocess_response(event)

            if response:
                final_response_text = response
            else:
                final_response_text = "[Agent finished but produced no text output]"
                print(f"--- ADK Run: WARNING - Final event received, but no text content found. Event: {event} ---")

    except Exception as e:
        print(f"--- ADK Run: !! EXCEPTION during agent execution: {e} !! ---")
        final_response_text = f"Sorry, an error occurred while processing your request. Please check the logs or try again later."

    end_time = py_time_module.time()
    duration = end_time - start_time

    print(f"--- ADK Run: Turn execution completed in {duration:.2f} seconds. ---")
    print(f"--- ADK Run: Final Response (truncated): '{final_response_text[:150]}...' ---")

    return final_response_text


def run_adk_sync(user_id: str , runner: Runner, session_id: str, user_message_text: str) -> str:
    """
    Synchronous wrapper that executes the asynchronous run_adk_async function.
    """
    return asyncio.run(run_adk_async(user_id, runner, session_id, user_message_text))

print("✅ ADK Runner initialization and helper functions defined.")
