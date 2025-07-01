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

import asyncio
import warnings
from dotenv import load_dotenv

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from customer_agent.agent import root_agent

load_dotenv()
warnings.filterwarnings("ignore")


USER_ID = str(input("Enter your customer id: "))
in_memory_session_service = InMemorySessionService()

initial_state = {
    "customer_full_name": "Test Customer",
    "USER_ID": USER_ID,
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

    print("\nWelcome to LogIQ's Customer Agent Sandbox!")
    print("Type 'exit' or 'quit' to end the conversation.\n")

    while True:
        user_input = input("USER: ")

        if user_input.lower() in ["exit", "quit", "bye"]:
            print("AGENT: Goodbye! Have a nice day.")
            break

        await call_agent_async(runner, USER_ID, SESSION_ID, user_input)


if __name__ == "__main__":
    asyncio.run(main_async())
