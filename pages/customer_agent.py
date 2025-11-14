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
            width: 335px !important; # Set the width to your desired value
        }
    </style>
    """
)

st.html(
    "<style>[data-testid='stHeaderActionElements'] {display: none;}</style>"
)

st.markdown(
    """
    <style>
    section[data-testid="stSidebar"] > div:first-child {
        height: 100vh;
        overflow: hidden;
    }
    </style>
    """,
    unsafe_allow_html=True
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

############################## [SESSION STATES] ###############################

if "customer_id" not in st.session_state:
    st.session_state.customer_id = None

if "current_session" not in st.session_state:
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


@st.cache_data(show_spinner=False)
def fetch_and_cache_profile_picture(session_id, customer_id):
    print(f"... fetch_and_cache_profile_picture ran [{session_id}]")
    try:
        profile_pic_bucket = ProfilePicturesBucket()

        profile_picture_url = (
            profile_pic_bucket.fetch_profile_picture_url(
                user_type="customers",
                user_id=customer_id,
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

    return profile_picture_url


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


AVATAR_AGENT = "assets/avatars/chatbot/agent_logo.png"


if __name__ == "__main__":
    if st.session_state.customer_id:
        with st.spinner("Setting things up...", show_time=True):
            customer_name = get_customer_details(
                full_name=True, 
                session_id=st.session_state.current_session
            )

            if 'messages' not in st.session_state:
                st.session_state['messages'] = []

            profile_picture_url = fetch_and_cache_profile_picture(
                st.session_state.current_session,
                st.session_state.customer_id,
            )

        with st.sidebar:
            selected_menu_item = sac.menu(
                [
                    sac.MenuItem(
                        "LogIQ Support Agent",
                        icon="robot",
                        tag=[sac.Tag('AI', color='orange', icon='stars')]
                    ),
                    sac.MenuItem(
                        "AI Settings and Help",
                        icon="gear",
                    ),
                    sac.MenuItem(" ", disabled=True),
                    sac.MenuItem(type="divider"),
                ],
                open_all=True,
            )

            with st.container(height=416, border=False):
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
                            [1, 2.65], 
                            vertical_alignment="center", 
                            gap='small'
                        )

                        with colx:
                            try:
                                st.image(
                                    profile_picture_url,
                                    width="stretch",
                                )
                            except Exception as error:
                                pass

                        with coly:
                            st.markdown(
                                f"""
                                <B>{str(st.session_state.customer_name)}</B>
                                <BR>Username: {st.session_state.customer_id}
                                """,
                                unsafe_allow_html=True,
                            )

            cola, colb = st.columns([4.5, 1])

            with cola:
                if st.button(
                    "Back to Dashboard",
                    icon=":material/arrow_back:",
                    width="stretch",
                ):
                    #st.cache_data.clear()  #### WHY?
                    st.switch_page('customer_app.py')

            with colb:
                if st.button(
                    "",
                    icon=":material/edit_square:",
                    help="New Chat",
                    width="stretch",
                ):
                    initialize_adk.clear()

                    del st.session_state['messages']
                    del st.session_state['adk_session_id']

                    st.rerun()

        try:
            adk_runner, current_session_id = initialize_adk(
                user_id=st.session_state.customer_id,
                session_id=st.session_state.current_session,
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
                avatar_url = AVATAR_AGENT

            with st.chat_message(
                message["role"], 
                avatar=avatar_url
            ):
                st.markdown(
                    message["content"], 
                    unsafe_allow_html=False
                )

        if prompt := st.chat_input("Type your question here..."):
            st.session_state['messages'].append(
                {"role": "user", "content": prompt}
            )

            with st.chat_message("user", avatar=profile_picture_url):
                st.markdown(prompt, unsafe_allow_html=False)

            with st.chat_message("assistant", avatar=AVATAR_AGENT):
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
                    {
                        "role": "assistant", 
                        "content": agent_response
                    }
                )

                def response_generator(response):
                    for word in response:
                        time.sleep(0.0025)

                        try:
                            yield word.text
                        except Exception as error:
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

        if not st.session_state['messages']:
            st.markdown(
                f"""
                <BR><BR><BR><BR><BR>
                <H1 class='h1-chat-welcome-title'>
                    Hello, {str(st.session_state.customer_name)}
                </H1>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                """
                <H1 class='h1-chat-welcome-subtitle'>
                    How can I help you today?
                </H1>
                """,
                unsafe_allow_html=True,
            )
            st.write(" ")

            welcome_message = f"""
            Your conversations may be reviewed by human evaluators for the 
            purpose of improving the overall quality, reliability, and 
            effectiveness of this product. Please avoid sharing sensitive, 
            personal, or confidential information that you would not be 
            comfortable being accessed, or analyzed!

            Learn more here: 
            github.com/thisisashwinraj/logiq-smart-appliance-management
            """

            if st.session_state.themes["current_theme"] == "dark":
                st.info(
                    welcome_message, 
                    icon=":material/security:"
                )

            else:
                st.warning(
                    welcome_message, 
                    icon=":material/security:"
                )


    else:
        st.switch_page("customer_app.py")
