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
import asyncio
import streamlit as st
from typing import Tuple
import time as py_time_module
from dotenv import load_dotenv

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types

from engineer_agent.agent import root_agent

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
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
def initialize_adk(session_id: str, user_id: str) -> Tuple:
    APP_NAME = "LogIQ Engineer App"

    initial_state = {
        "engineer_id": user_id,
    }

    session_service = InMemorySessionService()

    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    if "adk_session_id" not in st.session_state:
        random_hex = os.urandom(4).hex()
        session_id = f"adk_session_{int(py_time_module.time())}_{random_hex}"

        st.session_state["adk_session_id"] = session_id

        try:
            _run_coroutine_in_new_loop(
                session_service.create_session(
                    app_name=APP_NAME,
                    user_id=user_id,
                    session_id=session_id,
                    state=initial_state,
                )
            )

        except Exception as error:
            raise

    else:
        session_id = st.session_state["adk_session_id"]

        existing_session = _run_coroutine_in_new_loop(
            session_service.get_session(
                app_name=APP_NAME,
                user_id=user_id,
                session_id=session_id,
            )
        )

        if not existing_session:

            try:
                _run_coroutine_in_new_loop(
                    session_service.create_session(
                        app_name=APP_NAME,
                        user_id=user_id,
                        session_id=session_id,
                        state=initial_state,
                    )
                )

            except Exception as error:
                raise

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


async def run_adk_async(
    user_id: str,
    runner: Runner,
    session_id: str,
    user_message_text: str,
) -> str:
    content = genai_types.Content(
        role="user", parts=[genai_types.Part(text=user_message_text)]
    )

    final_response_text = """
    [Error Code: 251] Sorry, an error occurred while processing your request.
    Please try again later.
    """

    try:
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=content,
        ):
            response = await preprocess_response(event)

            if response:
                final_response_text = response
            else:
                final_response_text = """
                [Error Code: 252] Sorry, an error occurred while processing
                your request. Please try again later.
                """

    except Exception as e:
        final_response_text = f"""
        [Error Code: 253] Sorry, an error occurred while processing your 
        request. Please try again later. {e}
        """

    return final_response_text


def run_adk_sync(
    user_id: str,
    runner: Runner,
    session_id: str,
    user_message_text: str,
) -> str:
    return asyncio.run(
        run_adk_async(user_id, runner, session_id, user_message_text,)
    )
