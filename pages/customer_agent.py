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
import time
import uuid
import warnings
from dotenv import load_dotenv

import datetime
from datetime import timedelta

import streamlit as st
import streamlit_antd_components as sac
from streamlit_extras.stylable_container import stylable_container

from customer_agent.runner import initialize_adk, run_adk_sync
from database.cloud_storage.multimedia_storage import ProfilePicturesBucket
from database.cloud_sql.queries import QueryCustomers


st.set_page_config(
    page_title="LogIQ Customers: Support",
    page_icon="assets/logos/logiq_favicon.png",
    layout="wide",
    initial_sidebar_state="expanded",
)

warnings.filterwarnings("ignore")

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)


st.html(
    """
    <style>
        section[data-testid="stSidebar"] {
            width: 325px !important; # Set the width to your desired value
        }
    </style>
    """
)

st.markdown(
    """
        <style>
               .block-container {
                    padding-top: 0.2rem;
                    padding-bottom: 1.55rem;
                }
        </style>
        """,
    unsafe_allow_html=True,
)

with open("assets/css/customers.css") as f:
    css = f.read()

st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

st.markdown(
    """
    <style>
        #MainMenu  {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <style>
        .stMarkdown a {
            text-decoration: none;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


if "customer_id" not in st.session_state:
    st.session_state.customer_id = None

if "current_session_id" not in st.session_state:
    st.session_state.current_session = str(uuid.uuid4()).replace("-", "")[:12]

if "customer_name" not in st.session_state:
    st.session_state.customer_name = ""

if "customer_email" not in st.session_state:
    st.session_state.customer_email = ""

if "customer_details" not in st.session_state:
    st.session_state.customer_details = ""

if "themes" not in st.session_state:
    st.session_state.themes = {
        "current_theme": "light",
        "refreshed": True,
        "light": {
            "theme.base": "dark",
            "theme.backgroundColor": "#131314",
            "theme.primaryColor": "#8AB4F8",
            "theme.secondaryBackgroundColor": "#18191B",
            "theme.textColor": "#EAE9FC",
            "cardColor": "#f9fafb",
            "containerColor": "#f0f2f6",
            "containerBoundaryColor": "rgba(229, 231, 235, 1)",
            "alertColor": "#3367D6",
            "button_face": ":material/dark_mode:",
        },
        "dark": {
            "theme.base": "light",
            "theme.backgroundColor": "#FFFFFF",
            "theme.primaryColor": "#3367D6",
            "theme.secondaryBackgroundColor": "#F1F3F4",
            "theme.textColor": "#040316",
            "cardColor": "#202124",
            "containerColor": "#18191B",
            "containerBoundaryColor": "rgba(49, 51, 63, 0.2)",
            "alertColor": "#8AB4F8",
            "button_face": ":material/light_mode:",
        },
    }


def change_streamlit_theme():
    previous_theme = st.session_state.themes["current_theme"]
    tdict = (
        st.session_state.themes["light"]
        if st.session_state.themes["current_theme"] == "light"
        else st.session_state.themes["dark"]
    )

    for vkey, vval in tdict.items():
        if vkey.startswith("theme"):
            st._config.set_option(vkey, vval)

    st.session_state.themes["refreshed"] = False

    if previous_theme == "dark":
        st.session_state.themes["current_theme"] = "light"

    elif previous_theme == "light":
        st.session_state.themes["current_theme"] = "dark"


if st.session_state.themes["refreshed"] == False:
    st.session_state.themes["refreshed"] = True
    st.rerun()


@st.cache_data(show_spinner=False, ttl="30 minutes")
def get_greetings(is_ist, session_id):
    morning_start = timedelta(hours=5)
    afternoon_start = timedelta(hours=12)
    evening_start = timedelta(hours=17)
    night_start = timedelta(hours=21)

    ist_now = datetime.datetime.utcnow() + timedelta(hours=5, minutes=30)

    current_time = timedelta(hours=ist_now.hour, minutes=ist_now.minute)

    if morning_start <= current_time < afternoon_start:
        greeting = "Good Morning"
    elif afternoon_start <= current_time < evening_start:
        greeting = "Good Afternoon"
    elif evening_start <= current_time < night_start:
        greeting = "Good Evening"
    else:
        greeting = "Hello"

    return greeting


@st.cache_data(show_spinner=False)
def get_customer_details(full_name, session_id):
    query_customers = QueryCustomers()

    customer_details = query_customers.fetch_customer_details_by_username(
        st.session_state.customer_id,
    )

    st.session_state.customer_details = customer_details

    try:
        if full_name:
            st.session_state.customer_name = (
                customer_details.get("first_name")
                + " "
                + customer_details.get("last_name")
            )
        else:
            st.session_state.customer_name = customer_details.get("first_name")

    except Exception as error:
        st.session_state.customer_name = "LogIQ User"

    return st.session_state.customer_name


adk_logo = "https://google.github.io/adk-docs/assets/agent-development-kit.png"


if __name__ == "__main__":
    if st.session_state.customer_id:
        if 'messages' not in st.session_state:
            st.session_state['messages'] = []

            welcome_message = f"""
            Hi **{str(st.session_state.customer_name.strip().split()[0])}**, 
            welcome to LogIQ. I'm your AI guide dedicated to making your 
            appliance ownership seamless and simple. How can I help you 
            today...?"""

            st.session_state.messages.append(
                {"role": "assistant", "content": welcome_message}
            )

        greeting = get_greetings(
            is_ist=True, session_id=st.session_state.current_session)
        
        customer_name = get_customer_details(
            full_name=True, session_id=st.session_state.current_session)

        with st.sidebar:
            with st.container(height=493, border=False):
                with stylable_container(
                    key="sidebar_container_with_border",
                    css_styles=f"""
                        {{
                            background-color: {st.session_state.themes[
                                st.session_state.themes[
                                    "current_theme"]]["cardColor"]};
                            border: 1px solid {st.session_state.themes[
                                st.session_state.themes[
                                    "current_theme"]][
                                        "containerBoundaryColor"
                                    ]};;
                            border-radius: 0.6rem;
                            padding: calc(1em - 1px)
                        }}
                        """,
                ):
                    with st.container(border=False):
                        colx, coly = st.columns(
                            [1, 2.65], vertical_alignment="center", gap='small'
                        )

                        with colx:
                            try:
                                profile_picture_bucket = ProfilePicturesBucket()

                                profile_picture_url = (
                                    profile_picture_bucket.fetch_profile_picture_url(
                                        user_type="customers",
                                        user_id=st.session_state.customer_id,
                                    )
                                )

                            except Exception as error:
                                if (
                                    st.session_state.customer_details.get(
                                        "gender"
                                    ).lower()
                                    == "male"
                                ):
                                    profile_picture_url = (
                                        "assets/avatars/customers/male8.png"
                                    )

                                else:
                                    profile_picture_url = (
                                        "assets/avatars/customers/female8.png"
                                    )

                            st.image(
                                profile_picture_url,
                                use_container_width=True,
                            )

                        with coly:
                            st.markdown(
                                f"""
                                <B>{str(st.session_state.customer_name)}</B>
                                <BR>Username: {st.session_state.customer_id}
                                """,
                                unsafe_allow_html=True,
                            )

                st.write("<HR>", unsafe_allow_html=True)

                alert = """LogIQ can make mistakes. 
                Please double-check responses."""

                sac.alert(
                    label="You are interacting with an AI",
                    description=alert,
                    color='yellow',
                )

            cola, colb = st.columns([4.5, 1])

            with cola:
                if st.button(
                    "Back to Dashboard",
                    icon=":material/arrow_back:",
                    use_container_width=True,
                ):
                    st.cache_data.clear()
                    st.switch_page('customer_app.py')

            with colb:
                if st.button(
                    "",
                    icon=":material/add_notes:",
                    help="New Session",
                    use_container_width=True,
                ):
                    initialize_adk.clear()
                    del st.session_state['messages']
                    del st.session_state['adk_session_id']

                    st.rerun()

        try:
            adk_runner, current_session_id = initialize_adk(
                user_id=st.session_state.customer_id
            )

        except Exception as e:
            st.error(f"""
                **Fatal Error:** Could not initialize the ADK Runner or Session 
                Service: {e}", icon=":material/cancel:"""
            )

            st.stop()

        for message in st.session_state['messages']:
            if message["role"] == "user":
                avatar_url = profile_picture_url
            else:
                avatar_url = adk_logo

            with st.chat_message(message["role"], avatar=avatar_url):
                st.markdown(message["content"], unsafe_allow_html=False)

        if prompt := st.chat_input("Type your question here..."):
            st.session_state['messages'].append(
                {"role": "user", "content": prompt}
            )

            with st.chat_message("user", avatar=profile_picture_url):
                st.markdown(prompt, unsafe_allow_html=False)

            with st.chat_message("assistant", avatar=adk_logo):
                message_placeholder = st.empty()

                with st.spinner("Thinking.....", show_time=True):
                    try:
                        agent_response = run_adk_sync(
                            st.session_state.customer_id, 
                            adk_runner, 
                            current_session_id, 
                            prompt
                        )

                    except Exception as error:
                        agent_response = """Sorry, an error occurred while 
                        processing your request. Please try again later."""

                st.session_state.messages.append(
                    {"role": "assistant", "content": agent_response}
                )

                def response_generator(response):
                    for word in response:
                        time.sleep(0.025)

                        try:
                            yield word.text
                        except Exception as err:
                            yield word

                try:
                    response = st.write_stream(
                        response_generator(agent_response)
                    )

                except Exception as err:
                    fallback_message = (
                        f"Sorry, I am unable to answer this."
                    )

                    response = st.write_stream(
                        response_generator(fallback_message)
                    )

    else:
        st.switch_page("customer_app.py")
