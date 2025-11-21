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
import json
import time
import uuid
import bleach

import asyncio
import logging
import requests
import warnings

import datetime
from datetime import timedelta
from dotenv import load_dotenv

import firebase_admin
from firebase_admin import credentials

import streamlit as st
import streamlit_antd_components as sac
from streamlit_folium import folium_static
from streamlit_extras.stylable_container import stylable_container

from backend.utils.geo_operations import LocationServices
from backend.channels.email_client import TransactionalEmails
from backend.channels.sms_client import NotificationSMS

from engineer_agent.runner import initialize_adk, run_adk_sync

from database.cloud_sql.migrations import MigrateEngineers
from database.cloud_sql.queries import Appliances
from database.cloud_sql.queries import QueryCustomers, QueryEngineers

from database.cloud_storage.document_storage import CustomerRecordsBucket
from database.cloud_storage.document_storage import ServiceManualBucket
from database.cloud_storage.multimedia_storage import ProfilePicturesBucket

from database.firebase.firestore import OnsiteServiceRequestCollection


st.set_page_config(
    page_title="LogIQ Engineers",
    page_icon="assets/logos/logiq_favicon.png",
    initial_sidebar_state="expanded",
    layout="wide",
)

load_dotenv()
warnings.filterwarnings("ignore", category=UserWarning, module=".*pydantic.*")
logger = logging.getLogger(__name__)

if "GOOGLE_CLOUD_PROJECT" not in os.environ:
    os.environ["GOOGLE_CLOUD_PROJECT"] = st.secrets["GCP_PROJECT_NAME"]

if "GOOGLE_CLOUD_LOCATION" not in os.environ:
    os.environ["GOOGLE_CLOUD_LOCATION"] = st.secrets["GCP_PROJECT_LOCATION"]

if "GOOGLE_GENAI_USE_VERTEX_AI" not in os.environ:
    os.environ["GOOGLE_GENAI_USE_VERTEX_AI"] = "1"

################################ [CUSTOM CSS] #################################

st.html(
    """
    <style>
        section[data-testid="stSidebar"] {
            width: 323px !important; # Set the width to your desired value
        }
    </style>
    """
)

st.html("<style>[data-testid='stHeaderActionElements'] {display: none;}</style>")

st.html(
    """
    <style>
    section[data-testid="stSidebar"] > div:first-child {
        height: 100vh;
        overflow: hidden;
    }
    </style>
    """
)

st.markdown(
    """
        <style>
               .block-container {
                    padding-top: 0.1rem;
                    padding-bottom: 1.55rem;
                }
        </style>
        """,
    unsafe_allow_html=True,
)

with open("assets/css/engineers.css") as f:
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

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4()).replace("-", "")[:12]

if "engineer_id" not in st.session_state:
    st.session_state.engineer_id = None

if "engineer_details" not in st.session_state:
    st.session_state.engineer_details = None

if "onsite_service_requests" not in st.session_state:
    st.session_state.onsite_service_requests = []

if "service_guide" not in st.session_state:
    st.session_state.service_guide = None

if "ticket_counts" not in st.session_state:
    st.session_state.ticket_counts = {}

if "distinct_appliance_details" not in st.session_state:
    try:
        query_appliances = Appliances()
        st.session_state.distinct_appliance_details = (
            query_appliances.fetch_distinct_appliance_data()
        )
    except Exception as error:
        pass

@st.cache_data(show_spinner=False)
def fetch_and_cache_profile_picture(session_id, engineer_id):
    try:
        profile_pic_bucket = ProfilePicturesBucket()

        profile_picture_url = (
            profile_pic_bucket.fetch_profile_picture_url(
                user_type="engineers",
                user_id=st.session_state.engineer_id,
            )
        )

    except Exception as error:
        profile_picture_url = "assets/avatars/customers/female8.png"

    return profile_picture_url


@st.dialog("Manage Account", width="medium")
def dialog_manage_account():
    selected_tab = sac.tabs(
        [
            sac.TabsItem(label="Personal Details"),
            sac.TabsItem(label="Skills and Specializations"),
            sac.TabsItem(label="Location Details"),
        ],
        variant="outline",
    )

    if selected_tab == "Personal Details":
        col1, col2 = st.columns([1, 6], vertical_alignment='center')

        profile_picture_url = fetch_and_cache_profile_picture(
            st.session_state.session_id,
            st.session_state.engineer_id
        )

        col1.image(
            profile_picture_url,
            width='stretch',
        )

        profile_picture = col2.file_uploader(
            "Profile Picture",
            type=["png", "jpg"],
            accept_multiple_files=False,
        )
        
        cola, colb = st.columns(2)
        first_name = bleach.clean(
            cola.text_input(
                "First Name", value=st.session_state.engineer_details.get("first_name")
            )
        )
        last_name = bleach.clean(
            colb.text_input(
                "Last Name", value=st.session_state.engineer_details.get("last_name")
            )
        )

        phone_number = bleach.clean(
            cola.text_input(
                "Phone Number",
                value=st.session_state.engineer_details.get("phone_number"),
            )
        )
        email = bleach.clean(
            colb.text_input(
                "Email Id", value=st.session_state.engineer_details.get("email")
            )
        )

        cola, colb, _ = st.columns([1.9, 0.35, 2.3])

        if cola.button(
            "Update Profile",
            icon=":material/person_check:",
            width='stretch',
        ):
            migrate_engineers = MigrateEngineers()
            profile_picture_url = None

            with st.spinner("Updating details...", show_time=True):
                if profile_picture:
                    try:
                        profile_pictures_bucket = ProfilePicturesBucket()

                        profile_picture_url = (
                            profile_pictures_bucket.upload_profile_picture(
                                user_type="engineers",
                                user_id=st.session_state.engineer_id,
                                file=profile_picture,
                            )
                        )

                    except Exception as error:
                        st.warning(
                            "Unable to save profile picture", icon=":material/warning:"
                        )

                    finally:
                        if profile_picture_url:
                            response = migrate_engineers.update_engineer(
                                engineer_id=st.session_state.engineer_id,
                                first_name=first_name,
                                last_name=last_name,
                                phone_number=phone_number,
                                email=email,
                                profile_picture=profile_picture_url,
                            )

                        else:
                            response = migrate_engineers.update_engineer(
                                engineer_id=st.session_state.engineer_id,
                                first_name=first_name,
                                last_name=last_name,
                                phone_number=phone_number,
                                email=email,
                            )

                else:
                    response = migrate_engineers.update_engineer(
                        engineer_id=st.session_state.engineer_id,
                        first_name=first_name,
                        last_name=last_name,
                        phone_number=phone_number,
                        email=email,
                    )

            if response:
                st.success("Profile updated succesfully!", icon=":material/check:")

                try:
                    get_engineer_details.clear()
                except Exception as error:
                    pass

                try:
                    get_engineer_name.clear()
                except Exception as error:
                    pass

                st.session_state.engineer_details = None

                try:
                    query_engineers = QueryEngineers()
                    st.session_state.engineer_details = (
                        query_engineers.fetch_engineer_details_by_id(
                            st.session_state.engineer_id
                        )
                    )

                except Exception as error:
                    pass

                time.sleep(3)
                st.rerun()

            else:
                alert_warning = st.warning(
                    "Unable to update your profile. Please try again later.",
                    icon=":material/warning:",
                )
                time.sleep(3)
                alert_warning.empty()

        if colb.button(
            "",
            icon=":material/clear_all:",
            help="Discard and Exit",
            width='stretch',
            key="_dicard_updates_button_1",
        ):
            st.rerun()

    elif selected_tab == "Skills and Specializations":
        specializations_options = list(
            st.session_state.distinct_appliance_details.keys()
        )

        specializations = st.multiselect(
            "Specializations",
            specializations_options,
            default=json.loads(
                st.session_state.engineer_details.get("specializations", None)
            ),
        )

        skills_options = [
            "Installation",
            "Maintenance/Servicing",
            "Calibration",
            "Part Replacement",
            "Noise/Leakage Issue",
            "Software/Firmware Update",
            "Inspection and Diagnosis",
            "Wiring Inspection",
            "Electrical Malfunction",
            "Mechanical Repair",
            "Overheating",
            "General Appliance Troubleshooting",
            "Cooling/Heating Issue",
            "Water Drainage Problem",
            "Vibration/Imbalance",
            "Gas Leakage Detection" "Rust or Corrosion Repair",
            "Control Panel Malfunction",
            "Error Code Diagnosis",
            "Appliance Relocation Assistance",
            "Smart Home Integration Support",
        ]
        skills = st.multiselect(
            "Skills",
            skills_options,
            default=json.loads(st.session_state.engineer_details.get("skills", None)),
        )

        language_options = ["English", "Hindi", "Malayalam", "Tamil"]
        language_proficiency = st.multiselect(
            "Language Proficiency",
            language_options,
            default=json.loads(
                st.session_state.engineer_details.get("language_proficiency", None)
            ),
        )

        cola, colb, _ = st.columns([1.9, 0.35, 2.3])

        if cola.button(
            "Update Profile",
            icon=":material/person_check:",
            width='stretch',
        ):
            migrate_engineers = MigrateEngineers()

            with st.spinner("Updating details...", show_time=True):
                response = migrate_engineers.update_engineer(
                    engineer_id=st.session_state.engineer_id,
                    skills=json.dumps(skills),
                    specializations=json.dumps(specializations),
                    language_proficiency=json.dumps(language_proficiency),
                )

            if response:
                st.success("Profile updated succesfully!", icon=":material/check:")

                try:
                    get_engineer_details.clear()
                except Exception as error:
                    pass

                st.session_state.engineer_details = None

                try:
                    query_engineers = QueryEngineers()
                    st.session_state.engineer_details = (
                        query_engineers.fetch_engineer_details_by_id(
                            st.session_state.engineer_id
                        )
                    )

                except Exception as error:
                    pass

                time.sleep(3)
                st.rerun()

            else:
                alert_warning = st.warning(
                    "Unable to update your profile. Please try again later.",
                    icon=":material/warning:",
                )
                time.sleep(3)
                alert_warning.empty()

        if colb.button(
            "",
            icon=":material/clear_all:",
            help="Discard and Exit",
            width='stretch',
            key="_dicard_updates_button_2",
        ):
            st.rerun()

    else:
        cola, colb = st.columns([3, 1])

        street = bleach.clean(
            cola.text_input(
                "Street", value=st.session_state.engineer_details.get("street")
            )
        )

        city = bleach.clean(
            colb.text_input("City", value=st.session_state.engineer_details.get("city"))
        )

        cola, colb, colc, cold = st.columns(4)

        district = bleach.clean(
            cola.text_input(
                "District", value=st.session_state.engineer_details.get("district")
            )
        )

        state = bleach.clean(
            colb.text_input(
                "State", value=st.session_state.engineer_details.get("state")
            )
        )

        zip_code = bleach.clean(
            colc.text_input(
                "Zip Code", value=st.session_state.engineer_details.get("zip_code")
            )
        )

        country = bleach.clean(
            cold.text_input(
                "Country", value=st.session_state.engineer_details.get("country")
            )
        )

        cola, colb, _ = st.columns([1.9, 0.35, 2.3])

        if cola.button(
            "Update Profile",
            icon=":material/person_check:",
            width='stretch',
        ):
            migrate_engineers = MigrateEngineers()

            with st.spinner("Updating details...", show_time=True):
                response = migrate_engineers.update_engineer(
                    engineer_id=st.session_state.engineer_id,
                    street=street,
                    city=city,
                    district=district,
                    state=state,
                    zip_code=zip_code,
                    country=country,
                )

            if response:
                st.success(
                    "Profile updated succesfully!", 
                    icon=":material/check:"
                )

                try:
                    get_engineer_details.clear()
                except Exception as error:
                    pass

                st.session_state.engineer_details = None

                try:
                    query_engineers = QueryEngineers()
                    st.session_state.engineer_details = (
                        query_engineers.fetch_engineer_details_by_id(
                            st.session_state.engineer_id
                        )
                    )

                except Exception as error:
                    pass

                time.sleep(3)
                st.rerun()

            else:
                alert_warning = st.warning(
                    "Unable to update your profile. Please try again later.",
                    icon=":material/warning:",
                )

                time.sleep(3)
                alert_warning.empty()

        if colb.button(
            "",
            icon=":material/clear_all:",
            help="Discard and Exit",
            width='stretch',
            key="_dicard_updates_button_2",
        ):
            st.rerun()

@st.dialog("Request History", width='medium')
def dialog_display_past_service_request_details(request_details):
    with st.container(border=False):
        with stylable_container(
            key="_ticket_activity_card_details",
            css_styles=f"""
                {{
                    background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["cardColor"]};
                    border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};;
                    border-radius: 0.6rem;
                    padding: calc(1em - 1px)
                }}
                """,
        ):
            st.markdown(
                f"""
                <H3>Request Details</H3>
                <P>
                    <B>Request Title:</B>
                    {request_details.get('request_title')}
                </P>
                <P align='left'>
                    <B>Description:</B>
                    {request_details.get('description')}
                </P>
                <P>
                    <B>Created on:</B>
                    {datetime.datetime.strptime(request_details.get("created_on"), "%Y-%m-%d %H:%M:%S",).strftime("%B %d, %Y")}
                </P>
                """,
                unsafe_allow_html=True,
            )

            st.space(1)

    with st.container(border=False):
        with stylable_container(
            key="_ticket_activity_card_resolution",
            css_styles=f"""
                {{
                    background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["cardColor"]};
                    border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};;
                    border-radius: 0.6rem;
                    padding: calc(1em - 1px)
                }}
                """,
        ):
            st.markdown(
                f"""
                <H3>Engineer Activity and Resolution</H3>
                <P align='left'>
                    {request_details.get('action_performed', '')}
                </P>
                <P align='left'>
                    {request_details.get('additional_notes', '')}
                </P>
                """,
                unsafe_allow_html=True,
            )

            st.space(1)
            

@st.dialog("Password Reset", width="small")
def reset_password():
    api_key = st.secrets["FIREBASE_AUTH_WEB_API_KEY"]

    base_url = (
        "https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={api_key}"
    )

    sac.alert(
        label="Forgot your Password?",
        description="No worries! Enter your email address below, and we'll send you a link to reset your password.",
        color="orange",
        icon=True,
    )

    input_email = bleach.clean(
        st.text_input(
            "Enter your registered email id",
            placeholder="Registered Email Id",
            label_visibility="collapsed",
        )
    )

    if st.button(
        "Send Password Reset Email",
        icon=":material/forward_to_inbox:",
        width='stretch',
    ):
        with st.spinner("Processing request...", show_time=True):
            try:
                query_engineers = QueryEngineers()
                engineer_exists = query_engineers.check_engineer_exists_by_email(
                    input_email
                )

            except Exception as error:
                engineer_exists = None

        if engineer_exists:
            data = {
                "email": input_email,
                "requestType": "PASSWORD_RESET",
            }

            response = requests.post(base_url.format(api_key=api_key), json=data)

            if response.status_code == 200:
                next_steps_message = "We've sent a password reset link to your registered email address. Please check your inbox and follow the instructions to reset your password."

                sac.alert(
                    label=f"Password Reset Link Sent",
                    description=next_steps_message,
                    color="success",
                    icon=True,
                )

            else:
                alert_password_reset_mail_failed = st.error(
                    "We're having trouble sending the password reset email",
                    icon=":material/error:",
                )
                time.sleep(2)
                alert_password_reset_mail_failed.empty()

                alert_password_reset_mail_failed = st.error(
                    "Kindly double-check your email id and try again.",
                    icon=":material/error:",
                )
                time.sleep(2)
                alert_password_reset_mail_failed.empty()

        else:
            st.warning(
                "No engineer found with this username. Please check the username and try again.",
                icon=":material/warning:",
            )


@st.dialog("Attribution and Copyright", width='medium')
def dialog_attribution():
    sac.alert(
        label=f"Acknowledgments and Fair Use Notice",
        description="Google Cloud credits are provided for this project as part of the Google AI Sprint 2024.<BR> Additionally, various documents including but not limited to service guides and manuals from various companies have been referenced during the development of this project. These materials are used under fair use as this project is intended solely for educational purposes and not for commercial gain.<BR><BR>If you have any questions or concerns, please contact me at thisisashwinraj@gmail.com.",
        color="info",
        icon=True,
    )


@st.dialog("Resolve Service Request", width='medium')
def dialog_resolve_service_request(service_request_id, service_request_details):
    if service_request_details.get("resolution").get("start_date") == "":
        sac.alert(
            label=f"Request verification OTP from the customer",
            description="Enter the OTP in the verification field to proceed with the resolution. If you are unable to obtain the OTP, please contact our Support Team at customersupport@logiq.com for further assistance.",
            color="orange",
            icon=True,
        )

    else:
        action_performed = bleach.clean(
            st.text_area(
                "Action Performed",
                placeholder="Describe the actions taken to resolve the issue in detail...",
            )
        )

        additional_notes = bleach.clean(
            st.text_area(
                "Additional Notes",
                placeholder="Add any extra details, observations, or suggestions related to the issue...",
            )
        )

        cola, colb = st.columns(2)

        with cola:
            resolution_otp = bleach.clean(
                st.text_input(
                    "Resolution OTP",
                    placeholder="Enter Customer OTP to resolve ticket",
                )
            )

        with colb:
            st.date_input("Resolution Date", disabled=True)

        cola, _ = st.columns([1, 2.5])

        if cola.button(
            "Mark as Resolved", icon=":material/done_all:", width='stretch'
        ):
            onsite_service_request_collection = OnsiteServiceRequestCollection()

            response, response_code = (
                onsite_service_request_collection.resolve_service_request(
                    service_request_details.get("customer_id"),
                    service_request_id,
                    action_performed,
                    additional_notes,
                    resolution_otp,
                )
            )

            if response:
                st.success(
                    "Service request has been marked as resolved!",
                    icon=":material/check:",
                )

                try:
                    try:
                        query_customers = QueryCustomers()

                        customer_name = (
                            query_customers.fetch_customer_details_by_username(
                                service_request_details.get("customer_id"),
                                ["first_name", "last_name"],
                            )
                        )

                    except Exception as error:
                        customer_name = {
                            "first_name": "LogIQ",
                            "last_name": "User",
                        }

                    transaction_email_channel = TransactionalEmails()

                    transaction_email_channel.send_onsite_service_request_resolved_mail(
                        receiver_full_name=f"{
                            customer_name.get('first_name')} {
                            customer_name.get('last_name')}",
                        receiver_email=service_request_details.get(
                            "customer_contact"
                        ).get("email"),
                        service_request_id=service_request_id,
                        engineer_id=st.session_state.engineer_id,
                        engineer_name=f"{
                            st.session_state.engineer_details.get("first_name")} {
                            st.session_state.engineer_details.get("last_name")}",
                        ticket_activity=action_performed,
                        additional_notes=additional_notes,
                    )

                except Exception as error:
                    pass

                try:
                    notification_sms_channel = NotificationSMS()

                    notification_sms_channel.send_onsite_service_request_resolved_sms(
                        receivers_phone_number=service_request_details.get(
                            "customer_contact"
                        ).get("phone_number"),
                        service_request_id=service_request_id,
                        engineer_name=f"{
                            st.session_state.engineer_details.get("first_name")} {
                            st.session_state.engineer_details.get("last_name")}",
                    )

                except Exception as error:
                    pass

                del st.session_state.onsite_service_requests
                st.session_state.onsite_service_requests = onsite_service_request_collection.fetch_onsite_service_request_details_by_engineer_id(
                    st.session_state.engineer_id
                )

                time.sleep(3)
                st.rerun()

            else:
                if response_code == 401:
                    display_warning = st.warning(
                        "You've provided an invalid OTP. Kindly try again!",
                        icon=":material/warning:",
                    )

                elif response_code == 402:
                    display_warning = st.warning(
                        "OTP not found. Kindly request customer to generate a new OTP",
                        icon=":material/warning:",
                    )

                else:
                    display_warning = st.warning(
                        "Unable to reach server. Kindly try again later!",
                        icon=":material/warning:",
                    )

                time.sleep(3)
                display_warning.empty()


@st.dialog("Resolution Details", width='medium')
def dialog_display_resolution_details(service_request_details):
    with st.container(border=False):
        with stylable_container(
            key="_internal_sidebar_container_with_border_details",
            css_styles=f"""
                {{
                    background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["cardColor"]};
                    border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};;
                    border-radius: 0.6rem;
                    padding: calc(1em - 1px)
                }}
                """,
        ):
            st.markdown(
                f"""
                <H3>
                {service_request_details.get('request_title')}
                </H3><BR>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                f"""
                {service_request_details.get('description')}
                """,
                unsafe_allow_html=True,
            )

        with st.container(border=False):
            with stylable_container(
                key="_internal_sidebar_container_with_border_resolution",
                css_styles=f"""
                    {{
                        background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["cardColor"]};
                        border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};;
                        border-radius: 0.6rem;
                        padding: calc(1em - 1px)
                    }}
                    """,
            ):
                st.markdown(
                    f"""
                    :material/text_snippet: <B>Resolution Notes</B>
                    <P align='left'>
                        {service_request_details.get('resolution').get('action_performed', '')}
                    </P>
                    <P align='left'>
                        {service_request_details.get('resolution').get('additional_notes', '')}
                    </P>
                    """,
                    unsafe_allow_html=True,
                )
                st.space(1)


@st.dialog("Review Service Request", width="small")
def dialog_review_service_request(service_request_id, service_request_details):
    sac.alert(
        label=f"Do you want to assign this ticket to yourself?",
        description="Approving this request'll add it to your work queue. Note: Once selected, this action can not be undone!",
        color="orange",
        icon=True,
    )

    onsite_service_request_collection = OnsiteServiceRequestCollection()
    cola, colb = st.columns(2)

    if cola.button(
        "Approve Request",
        icon=":material/check:",
        width='stretch',
        type="primary",
    ):
        status_updated = onsite_service_request_collection.update_assignment_status(
            service_request_details.get("customer_id"),
            service_request_id,
            "confirmed",
        )

        try:
            query_customers = QueryCustomers()

            customer_name = query_customers.fetch_customer_details_by_username(
                service_request_details.get("customer_id"), ["first_name", "last_name"]
            )

        except Exception as error:
            customer_name = {
                "first_name": "LogIQ",
                "last_name": "User",
            }

        try:
            onsite_service_request_collection = OnsiteServiceRequestCollection()

            onsite_service_request_collection.add_service_request_activity(
                service_request_details.get("customer_id"),
                service_request_id,
                added_by="system",
                notes=f"Onsite service request assigned to {
                    st.session_state.engineer_details.get("first_name")} {
                    st.session_state.engineer_details.get("last_name")} (Engineer Id: {
                    st.session_state.engineer_id})",
            )

        except Exception as error:
            pass

        try:
            transaction_email_channel = TransactionalEmails()

            transaction_email_channel.send_onsite_service_request_engineer_assigned_mail(
                receiver_full_name=f"{
                    customer_name.get('first_name')} {
                    customer_name.get('last_name')}",
                receiver_email=service_request_details.get("customer_contact").get(
                    "email"
                ),
                service_request_id=service_request_id,
                engineer_id=st.session_state.engineer_id,
                engineer_name=f"{
                    st.session_state.engineer_details.get("first_name")} {
                    st.session_state.engineer_details.get("last_name")}",
                engineer_phone=st.session_state.engineer_details.get("phone_number"),
                engineer_email=st.session_state.engineer_details.get("email"),
            )

        except Exception as error:
            pass

        try:
            notification_sms_channel = NotificationSMS()

            notification_sms_channel.send_onsite_service_request_engineer_assigned_sms(
                receivers_phone_number=service_request_details.get(
                    "customer_contact"
                ).get("phone_number"),
                service_request_id=service_request_id,
                engineer_id=st.session_state.engineer_id,
                engineer_name=f"{
                    st.session_state.engineer_details.get("first_name")} {
                    st.session_state.engineer_details.get("last_name")}",
            )

        except Exception as error:
            pass

        if status_updated:
            st.success("Request assigned to you successfully", icon=":material/check:")

        else:
            st.warning(
                "Unable to update staus. Try again later", icon=":material/warning:"
            )

        del st.session_state.onsite_service_requests

        try:
            onsite_service_request_collection = OnsiteServiceRequestCollection()
            st.session_state.onsite_service_requests = onsite_service_request_collection.fetch_onsite_service_request_details_by_engineer_id(
                st.session_state.engineer_id
            )

        except Exception as error:
            pass

        time.sleep(3)
        st.rerun()

    if colb.button("Reject Request", icon=":material/close:", width='stretch'):
        try:
            status_updated = (
                onsite_service_request_collection.assign_service_request_to_admin(
                    service_request_details.get("customer_id"),
                    service_request_id,
                    f"REJECTED_BY_ENGINEER_{st.session_state.engineer_id}",
                )
            )

        except Exception as error:
            pass

        if status_updated:
            st.success("Request removed from queue", icon=":material/cancel:")

        else:
            st.warning(
                "Unable to update staus. Try again later", icon=":material/warning:"
            )

        del st.session_state.onsite_service_requests

        try:
            onsite_service_request_collection = OnsiteServiceRequestCollection()
            st.session_state.onsite_service_requests = onsite_service_request_collection.fetch_onsite_service_request_details_by_engineer_id(
                st.session_state.engineer_id
            )

        except Exception as error:
            pass

        time.sleep(3)
        st.rerun()


@st.dialog("More Options", width='medium')
def dialog_view_more_ticket_options(service_request_id, service_request_details):
    with st.expander(
        "Verify and Start Ticket Resolution", 
        icon=":material/person_check:", 
        expanded=True
    ):
        resolution_start_date = service_request_details.get("resolution").get(
            "start_date"
        )

        if resolution_start_date:
            resolution_start_date = datetime.datetime.strptime(
                resolution_start_date,
                "%Y-%m-%d %H:%M:%S",
            ).strftime("%B %d, %Y")

            sac.alert(
                label=f"You have been verified succesfully",
                description=f"The customer has verified you on {resolution_start_date}",
                color="lime",
                icon=True,
            )

        else:
            cola, colb = st.columns([2.5, 1])
            input_otp = bleach.clean(
                cola.text_input(
                    "Enter your Verification OTP",
                    placeholder="Enter your Verification OTP",
                    label_visibility="collapsed",
                )
            )

            with colb:
                with stylable_container(
                    "button_verify_with_otp",
                    css_styles="""
                    button {
                        background-color: #3367D6;
                        border: #274AB3;
                        color: #FFFFFF;
                    }""",
                ):
                    button_verify_with_otp = st.button(
                        "Verify with OTP", 
                        icon=":material/policy:", 
                        key="_verify_with_otp_button", 
                        width='stretch'
                    )

            if button_verify_with_otp:
                onsite_service_request_collection = OnsiteServiceRequestCollection()
                is_validated, response_code = (
                    onsite_service_request_collection.validate_engineer_verification_otp(
                        service_request_details.get("customer_id"),
                        service_request_id,
                        input_otp,
                    )
                )

                if is_validated:
                    try:
                        try:
                            query_customers = QueryCustomers()

                            customer_name = (
                                query_customers.fetch_customer_details_by_username(
                                    service_request_details.get("customer_id"),
                                    ["first_name", "last_name"],
                                )
                            )

                        except Exception as error:
                            customer_name = {
                                "first_name": "LogIQ",
                                "last_name": "User",
                            }

                        transaction_email_channel = TransactionalEmails()

                        transaction_email_channel.send_onsite_service_request_resolution_started_mail(
                            receiver_full_name=f"{
                                customer_name.get('first_name')} {
                                customer_name.get('last_name')}",
                            receiver_email=service_request_details.get(
                                "customer_contact"
                            ).get("email"),
                            service_request_id=service_request_id,
                            engineer_id=st.session_state.engineer_id,
                            engineer_name=f"{
                                st.session_state.engineer_details.get("first_name")} {
                                st.session_state.engineer_details.get("last_name")}",
                        )

                    except Exception as error:
                        pass

                    try:
                        notification_sms_channel = NotificationSMS()

                        notification_sms_channel.send_onsite_service_request_resolution_started_sms(
                            receivers_phone_number=service_request_details.get(
                                "customer_contact"
                            ).get("phone_number"),
                            service_request_id=service_request_id,
                            engineer_id=st.session_state.engineer_id,
                            engineer_name=f"{
                                st.session_state.engineer_details.get("first_name")} {
                                st.session_state.engineer_details.get("last_name")}",
                        )

                    except Exception as error:
                        pass

                    st.success(
                        "You have been verified successfully", icon=":material/check:"
                    )

                    del st.session_state.onsite_service_requests

                    st.session_state.onsite_service_requests = onsite_service_request_collection.fetch_onsite_service_request_details_by_engineer_id(
                        st.session_state.engineer_id
                    )

                else:
                    if response_code == 401:
                        st.warning(
                            "You've provided an invalid OTP. Kindly try again!",
                            icon=":material/warning:",
                        )

                    elif response_code == 402:
                        st.warning(
                            "OTP expired or not found. Kindly request customer to generate a new OTP",
                            icon=":material/warning:",
                        )

                    else:
                        st.warning(
                            "Unable to reach server. Kindly try again later!",
                            icon=":material/warning:",
                        )

                time.sleep(3)
                st.rerun()

    with st.expander("Report Unsafe Working Condition", icon=":material/report:"):
        if service_request_details.get("unsafe_working_condition_reported"):
            sac.alert(
                label=f"Reported Unsafe Working Conditions",
                description=service_request_details.get(
                    "unsafe_working_condition_reported"
                ),
                color="yellow",
                icon=True,
            )

        else:
            working_condition_description = bleach.clean(
                st.text_area(
                    "Describe the unsafe working condition",
                    placeholder="Please provide a detailed description of the unsafe conditions...",
                    label_visibility="collapsed",
                )
            )
            cola, _ = st.columns([1, 3])

            with cola:
                with stylable_container(
                    "button_report_unsafe_working_condition",
                    css_styles="""
                    button {
                        background-color: #3367D6;
                        border: #274AB3;
                        color: #FFFFFF;
                    }""",
                ):
                    button_report_to_team = st.button(
                        "Report to Team", 
                        icon=":material/report:"
                    )
                    st.space(1)

            if button_report_to_team:
                onsite_service_request_collection = OnsiteServiceRequestCollection()

                response = (
                    onsite_service_request_collection.report_unsafe_working_condition(
                        service_request_details.get("customer_id"),
                        service_request_id,
                        working_condition_description,
                    )
                )

                if response:
                    st.success(
                        "Unsafe working condition reported successfully",
                        icon=":material/check:",
                    )
                    del st.session_state.onsite_service_requests

                    st.session_state.onsite_service_requests = onsite_service_request_collection.fetch_onsite_service_request_details_by_engineer_id(
                        st.session_state.engineer_id
                    )

                else:
                    st.warning(
                        "Unable to report unsafe working condition. Try again later",
                        icon=":material/warning:",
                    )

                time.sleep(3)
                st.rerun()


@st.dialog("Service Request Details", width='medium')
def dialog_view_service_request_details(
    service_request_id, service_request_details, is_approved=True
):
    with st.container(border=False):
        with stylable_container(
            key="sidebar_container_with_border",
            css_styles=f"""
                {{
                    background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                    border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};;
                    border-radius: 0.6rem;
                    padding: calc(1em - 1px)
                }}
                """,
        ):
            cola, colb = st.columns([1, 4])

            with cola:
                st.image(
                    service_request_details.get("appliance_details").get("appliance_image_url"),
                    width='stretch',
                )

            with colb:
                st.markdown(
                    f"""
                    <H2 class="h2-vsrd-1">
                        {service_request_details.get('request_title')}
                    </H2>
                    {service_request_details.get('appliance_details').get('brand')}
                    {service_request_details.get('appliance_details').get('sub_category')}
                    &nbsp;• &nbsp;Model Number:
                    {service_request_details.get('appliance_details').get('model_number')}
                    """,
                    unsafe_allow_html=True,
                )

                st.write(" ")

                try:
                    request_created_on = datetime.datetime.strptime(
                        service_request_details.get("created_on"),
                        "%Y-%m-%d %H:%M:%S",
                    )
                except Exception as error:
                    pass

                if is_approved:
                    try:
                        engineer_assigned_on = datetime.datetime.strptime(
                            service_request_details.get("engineer_assigned_on"),
                            "%Y-%m-%d %H:%M:%S",
                        )
                    except Exception as error:
                        pass

                    st.markdown(
                        f"""
                        :material/view_cozy: Request {service_request_id} created on {request_created_on.strftime('%B %d, %Y')}
                        <BR>
                        :material/event: This ticket was assigned to you on {engineer_assigned_on.strftime('%A, %B %d, %Y')}
                        """,
                        unsafe_allow_html=True,
                    )

                else:
                    st.markdown(
                        f"""
                        :material/view_cozy: Request {service_request_id} created on {request_created_on.strftime('%B %d, %Y')}
                        <BR>
                        :material/event: Ticket assigned by system. Approve to add this to your work queue.
                        """,
                        unsafe_allow_html=True,
                    )

    with st.container(border=False):
        with stylable_container(
            key="sidebar_container_with_border",
            css_styles=f"""
                {{
                    background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                    border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};;
                    border-radius: 0.6rem;
                    padding: calc(1em - 1px)
                }}
                """,
        ):
            st.markdown(
                f"""
                :material/clarify: <B>Request Description:</B>
                <BR>
                {service_request_details.get('description')}
                """,
                unsafe_allow_html=True,
            )


@st.dialog("Route Preview", width='medium')
def display_directions_to_customer_location(
    origin, destination, contact_number="Not Provided", email_id="Not Provided"
):
    with st.container(border=False):
        with stylable_container(
            key="sidebar_container_with_border_directions",
            css_styles=f"""
                {{
                    background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                    border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};;
                    border-radius: 0.6rem;
                    padding: calc(1em - 1px)
                }}
                """,
        ):
            st.markdown(
                f"""
                :material/location_on: **Customer Address:**
                """,
            )
            st.markdown(destination)

            st.markdown(f"""
                :material/mail: **E-mail Id:** {email_id}
                &nbsp;&nbsp;&nbsp;&nbsp;
                :material/phone_in_talk: **Phone Number:**(+91) {contact_number}
                </P>
                """,
                unsafe_allow_html=True,
            )

    with st.spinner("Finding the best route...", show_time=True):
        loc_services = LocationServices()
        map_obj = loc_services.display_route_with_folium(origin, destination)

    with st.container(border=False):
        with stylable_container(
            key="sidebar_container_with_border_route_preview",
            css_styles=f"""
                {{
                    background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                    border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};;
                    border-radius: 0.6rem;
                    padding: calc(1em - 1px)
                }}
                """,
        ):
            try:
                st.markdown(
                    f":material/directions: **Route Preview:**", 
                    unsafe_allow_html=True
                )
                folium_static(map_obj)
            
            except Exception as error:
                pass


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
            "button_face": ":material/dark_mode:"
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
            "button_face": ":material/light_mode:"
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


if __name__ == "__main__":
    st.session_state.engineer_id = "ENGR8T90450"  # For testing purposes only
    if st.session_state.engineer_id:
        @st.cache_data(show_spinner=False)
        def get_engineer_details(session_id, full_details=False):
            query_engineers = QueryEngineers()
            engineer_details = query_engineers.fetch_engineer_details_by_id(
                st.session_state.engineer_id
            )

            st.session_state.engineer_details = engineer_details
            return st.session_state.engineer_details

        get_engineer_details(st.session_state.session_id, full_details=False)

        profile_picture_url = fetch_and_cache_profile_picture(
            st.session_state.session_id, 
            st.session_state.engineer_id
        )

        with st.sidebar:
            selected_menu_item = sac.menu(
                [
                    sac.MenuItem(
                        "My Dashboard",
                        icon="grid",
                    ),
                    sac.MenuItem(
                        "View Requests",
                        icon="inboxes",
                    ),
                    sac.MenuItem(
                        "LogIQ Chatbot",
                        icon="chat-square-text",
                    ),
                    sac.MenuItem(" ", disabled=True),
                    sac.MenuItem(type="divider"),
                ],
                open_all=True,
                color=st.session_state.themes[
                    st.session_state.themes["current_theme"]
                ]["alertColor"],
            )

            sidebar_container = st.container(height=333, border=False)

        if selected_menu_item == "My Dashboard":
            onsite_service_request_collection = OnsiteServiceRequestCollection()

            @st.cache_data(show_spinner=False)
            def fetch_and_cache_onsite_service_requests(session_id, engineer_id):
                st.session_state.onsite_service_requests = onsite_service_request_collection.fetch_onsite_service_request_details_by_engineer_id(
                    engineer_id
                )

                assigned_count = 0
                for service_request in st.session_state.onsite_service_requests:
                    if (service_request.get("assignment_status") == "confirmed") and (
                        service_request.get("ticket_status") != "resolved"
                    ):
                        assigned_count += 1
                st.session_state.ticket_counts["assigned"] = assigned_count

                new_count = 0
                for service_request in st.session_state.onsite_service_requests:
                    if (
                        service_request.get("assignment_status")
                        == "pending_confirmation"
                    ):
                        new_count += 1
                st.session_state.ticket_counts["pending"] = new_count

                resolved_count = 0
                for service_request in st.session_state.onsite_service_requests:
                    if (service_request.get("assignment_status") == "confirmed") and (
                        service_request.get("ticket_status") == "resolved"
                    ):
                        resolved_count += 1
                st.session_state.ticket_counts["resolved"] = resolved_count

            fetch_and_cache_onsite_service_requests(
                st.session_state.session_id, 
                st.session_state.engineer_id
            )

            with sidebar_container:
                with st.container(border=False):
                    with stylable_container(
                        key="_internal_sidebar_container_with_border",
                        css_styles=f"""
                            {{
                                background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["cardColor"]};
                                border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};;
                                border-radius: 0.6rem;
                                padding: calc(1em - 1px)
                            }}
                            """,
                    ):
                        colx, coly, colz = st.columns(
                            [0.77, 2.3, 0.7], vertical_alignment="center"
                        )

                        with colx:
                            st.image(
                                "assets/app_graphics/maintenance_banner.png",
                                width='stretch',
                            )
                        with coly:
                            st.markdown(
                                """
                                <B>Maintenance Break</B>
                                <BR>
                                Nov 26, 2025
                                """,
                                unsafe_allow_html=True,
                            )

                        with colz:
                            if st.button(
                                "",
                                icon=":material/open_in_new:",
                                width='stretch',
                                key="_announcement_1",
                            ):
                                st.toast("Announcement currently unavailable")
                        st.space(1)

                with st.container(border=False):
                    with stylable_container(
                        key="_internal_info_sidebar_container_with_border",
                        css_styles=f"""
                            {{
                                background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["cardColor"]};
                                border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};;
                                border-radius: 0.6rem;
                                padding: calc(1em - 1px)
                            }}
                            """,
                    ):
                        colx, coly, colz = st.columns(
                            [0.77, 2.3, 0.7], vertical_alignment="center"
                        )

                        with colx:
                            st.image(
                                "assets/app_graphics/break_banner.png",
                                width='stretch',
                            )

                        with coly:
                            st.markdown(
                                """
                                <B>Training Reminder</B>
                                <BR>
                                Dec 12, 2025
                                """,
                                unsafe_allow_html=True,
                            )

                        with colz:
                            if st.button(
                                "",
                                icon=":material/open_in_new:",
                                width='stretch',
                                key="_announcement_2",
                            ):
                                st.toast("Announcement currently unavailable")

                        st.space(1)

            with st.sidebar:
                st.write(" ")
                st.markdown("<BR>", unsafe_allow_html=True)

                colp, colq = st.columns([4.5, 1], vertical_alignment="center")

                if colp.button(
                    "Manage Account",
                    icon=":material/manage_accounts:",
                    width='stretch',
                ):
                    dialog_manage_account()
                
                if colq.button(
                    "",
                    icon=":material/logout:",
                    help="Logout"
                ):
                    st.session_state.clear()
                    st.cache_data.clear()
                    st.cache_resource.clear()

                    st.logout()
                    st.stop()

            @st.cache_data(show_spinner=False)
            def get_engineer_name(session_id, full_name=True):
                query_engineers = QueryEngineers()
                engineer_details = query_engineers.fetch_engineer_details_by_id(
                    st.session_state.engineer_id, 
                    ["first_name", "last_name"]
                )

                if full_name:
                    return (
                        engineer_details.get("first_name")
                        + " "
                        + engineer_details.get("last_name")
                    )

                return engineer_details.get("first_name")

            engineer_name = get_engineer_name(
                st.session_state.session_id, 
                full_name=True
            )

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

            ribbon_col_1, ribbon_col_2, ribbon_col_3, ribbon_col_4 = st.columns(
                [4.5, 0.9, 0.32, 0.32], 
                vertical_alignment="center"
            )

            with ribbon_col_1:
                st.markdown(
                    f"<H4>{greeting}, {str(engineer_name)}!</H4>",
                    unsafe_allow_html=True,
                )

            with ribbon_col_2:
                if st.button(
                    "Spare Parts", 
                    icon=":material/manufacturing:", 
                    width='stretch'
                ):
                    st.toast("Marketplace is currently unavailable")

            with ribbon_col_3:
                btn_face = (
                    st.session_state.themes["light"]["button_face"]
                    if st.session_state.themes["current_theme"] == "light"
                    else st.session_state.themes["dark"]["button_face"]
                )

                st.button(
                    "",
                    icon=btn_face,
                    width='stretch',
                    type="secondary",
                    help="Theme",
                    on_click=change_streamlit_theme,
                )

            with ribbon_col_4:
                if st.button(
                    "",
                    icon=":material/refresh:",
                    help="Refresh",
                    width='stretch',
                ):
                    theme_bkp = st.session_state.themes

                    st.session_state.clear()
                    st.cache_data.clear()
                    st.cache_resource.clear()

                    st.session_state.themes = theme_bkp

                    st.rerun()

            st.write(" ")
            col1, col2, col3 = st.columns([2.4, 1, 1], vertical_alignment="center")

            with col1.container(border=False):
                with stylable_container(
                    key=f"_metrics_container_1",
                    css_styles=f"""
                        {{
                            background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                            border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                            border-radius: 0.6rem;
                            padding: calc(1em - 1px)
                        }}
                        """,
                ):
                    cola, colb = st.columns(
                        [1.05, 2.9], 
                        vertical_alignment="top"
                    )

                    with cola:
                        st.image(
                            profile_picture_url,
                            width='stretch',
                        )

                    with colb:
                        st.write(" ")

                        st.markdown(
                            f"""
                            <H5 class="h5-vsrd-3">
                                {st.session_state.engineer_details.get('first_name')} {st.session_state.engineer_details.get('last_name')}
                            </H5>
                            """,
                            unsafe_allow_html=True,
                        )

                        st.markdown(
                            f"""
                            Engineer Id: {st.session_state.engineer_id} 
                            &nbsp; • &nbsp; 
                            Rating: {str(float(st.session_state.engineer_details.get('rating')))} :material/star_rate:
                            """
                        )

                        colp, colq = st.columns([1, 1], vertical_alignment="top")

                        with colp:
                            with stylable_container(
                                "button_manage_account",
                                css_styles="""
                                button {
                                    background-color: #3367D6;
                                    border: #274AB3;
                                    color: #FFFFFF;
                                }""",
                            ):
                                button_manage_account = st.button(
                                    "Manage Account", 
                                    icon=":material/manage_accounts:", 
                                    key="button2", 
                                    width='stretch'
                                )

                        if button_manage_account:
                            dialog_manage_account()

                        button_engineer_availability = colq.button(
                            (
                                "Available"
                                if st.session_state.engineer_details.get("availability") == 1
                                else "Unavailable"
                            ),
                            width='stretch',
                            type="secondary",
                            icon=(
                                ":material/visibility:"
                                if st.session_state.engineer_details.get("availability") == 1
                                else ":material/visibility_off:"
                            ),
                        )

                    if button_engineer_availability:
                        st.space(1)

                        with st.spinner(
                            "Updating availability status...", 
                            show_time=True
                        ):
                            migrate_engineers = MigrateEngineers()
                            response = migrate_engineers.toggle_engineer_availability(
                                st.session_state.engineer_id
                            )

                            st.session_state.engineer_details = None

                        if response:
                            st.success(
                                "Availability status updated succesfully!", 
                                icon=":material/check:"
                            )

                            try:
                                query_engineers = QueryEngineers()
                                st.session_state.engineer_details = (
                                    query_engineers.fetch_engineer_details_by_id(
                                        st.session_state.engineer_id
                                    )
                                )

                            except Exception as error:
                                pass

                        else:
                            alert_warning = st.warning(
                                "Unable to update your availability status. Please try again later.",
                                icon=":material/warning:",
                            )
                            time.sleep(3)

                        st.rerun()

                    st.space(1)

            with sidebar_container:
                if st.session_state.engineer_details.get("availability") != 1:
                    sac.alert(
                        label="You're Marked as Unavailable!", 
                        description='To get new assignments, kindly update your status.', 
                        color='yellow', 
                        icon=False
                    )

            with col2.container(border=False):
                with stylable_container(
                    key=f"_metrics_container_2",
                    css_styles=f"""
                        {{
                            background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                            border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                            border-radius: 0.6rem;
                            padding: calc(1em - 1px)
                        }}
                        """,
                ):
                    col1, _ = st.columns([1.5, 4], vertical_alignment="top")

                    pending_ticket_icon = "assets/app_graphics/pending_tickets_icon.png" if st.session_state.themes["current_theme"] == "dark" else "assets/app_graphics/pending_tickets_icon_light.png"
                    
                    col1.image(
                        pending_ticket_icon, 
                        width='stretch'
                    )
                    st.space(1)

                    st.markdown(
                        "<P class=\"p-metrics-card-text\">Assigned Tickets</P>", 
                        unsafe_allow_html=True
                    )
                    st.markdown(
                        f"""
                        <H2 class="h2-metrics-card-title">
                        {str(st.session_state.ticket_counts.get('assigned')).zfill(2) if st.session_state.ticket_counts.get('assigned') < 10 else str(st.session_state.ticket_counts.get('assigned'))}
                        </H2>
                        """, 
                        unsafe_allow_html=True
                    )

            with col3.container(border=False):
                with stylable_container(
                    key=f"_metrics_container_3",
                    css_styles=f"""
                        {{
                            background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                            border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                            border-radius: 0.6rem;
                            padding: calc(1em - 1px)
                        }}
                        """,
                ):
                    col1, _ = st.columns([1.5, 4], vertical_alignment="top")

                    resolved_ticket_icon = "assets/app_graphics/resolved_tickets_icon.png" if st.session_state.themes["current_theme"] == "dark" else "assets/app_graphics/resolved_tickets_icon_light.png"

                    col1.image(
                        resolved_ticket_icon, 
                        width='stretch'
                    )
                    st.space(1)

                    st.markdown(
                        "<P class=\"p-metrics-card-text\">Resolved Tickets</P>", 
                        unsafe_allow_html=True
                    )
                    st.markdown(
                        f"""
                        <H2 class="h2-metrics-card-title">
                        {str(st.session_state.ticket_counts.get('resolved')).zfill(2) if st.session_state.ticket_counts.get('resolved') < 10 else str(st.session_state.ticket_counts.get('resolved'))}
                        </H2>
                        """, 
                        unsafe_allow_html=True
                    )

            with st.container(border=False):
                tab_request_assignment_status = sac.tabs(
                    [
                        sac.TabsItem(label="Assigned", icon="person-gear"),
                        sac.TabsItem(label="New", icon="person-add"),
                        sac.TabsItem(label="Resolved", icon="person-check"),
                    ],
                    variant="outline",
                )

                if tab_request_assignment_status.lower() == "assigned":
                    assigned_count = 0

                    def get_service_manual_url(category, sub_category):
                        service_manual_bucket = ServiceManualBucket()
                        service_manual_url = service_manual_bucket.fetch_service_manual_url(
                            f"{
                                category.lower().replace(
                                    ' ',
                                    '_').replace(
                                    '-',
                                    '_').replace(
                                    '/',
                                    '_')}/{
                                sub_category.lower().replace(
                                    " ",
                                    "_").replace(
                                    "-",
                                    "_").replace(
                                    "/",
                                    "_")}_service_guide.pdf"
                        )
                        return service_manual_url

                    for service_request in st.session_state.onsite_service_requests:
                        if (
                            service_request.get("assignment_status") == "confirmed"
                        ) and (service_request.get("ticket_status") != "resolved"):
                            assigned_count += 1

                            with stylable_container(
                                key=f"container_with_border_{assigned_count}",
                                css_styles=f"""
                                    {{
                                        background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                        border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                        border-radius: 0.6rem;
                                        padding: calc(1em - 1px)
                                    }}
                                    """,
                            ):
                                cola, colb, colc = st.columns(
                                    [0.75, 2.71, 1.5],
                                    vertical_alignment="center"
                                )

                                cola.image(
                                    service_request.get("appliance_details").get(
                                        "appliance_image_url"
                                    ),
                                    width='stretch',
                                )

                                with colb:
                                    colx, _ = st.columns([20, 0.01])

                                    with colx:
                                        st.markdown(
                                            f"<H5>{service_request.get('request_title')}</H5>",
                                            unsafe_allow_html=True,
                                        )

                                        st.markdown(
                                            f"""
                                            <P class="p-service-request-request-id-serial-number">
                                                {service_request.get('appliance_details').get('sub_category')} &nbsp;•&nbsp; {service_request.get('request_id')}
                                            </P>
                                            """,
                                            unsafe_allow_html=True,
                                        )

                                        st.markdown(
                                            f"""
                                            <div class="div-truncate-text">
                                                <P align='left'>{service_request.get('description')}...</P>
                                            </div>
                                            """,
                                            unsafe_allow_html=True,
                                        )
                                        st.write("")

                                with colc:
                                    st.markdown("<BR>", unsafe_allow_html=True)

                                    st.markdown(
                                        f"""
                                        <P class="p-service-request-status" align='right'>
                                            <font size=4>
                                                <B>
                                                    Status: {service_request.get('ticket_status').capitalize()} &nbsp
                                                </B>
                                            </font>
                                        </P>
                                        """,
                                        unsafe_allow_html=True,
                                    )

                                    st.write(" ")
                                    colx, coly, colz = st.columns([0.6, 0.6, 2])

                                    if colx.button(
                                        "",
                                        icon=":material/location_on:",
                                        width='stretch',
                                        key=f"_edit_service_request_{service_request.get('request_id')}"
                                    ):
                                        query_engineers = QueryEngineers()

                                        engineer_address_data = query_engineers.fetch_engineer_details_by_id(
                                            st.session_state.engineer_id,
                                            [
                                                "street",
                                                "city",
                                                "district",
                                                "state",
                                                "zip_code",
                                            ],
                                        )

                                        engineer_address = f"""{
                                            engineer_address_data.get("street")}, {
                                            engineer_address_data.get("city")}, {
                                            engineer_address_data.get("district")}, {
                                            engineer_address_data.get("state")} - {
                                            engineer_address_data.get("zip_code")}"""

                                        customer_address = f"""{
                                            service_request.get("address").get("street")}, {
                                            service_request.get("address").get("city")}, {
                                            service_request.get("address").get("state")} - {
                                            service_request.get("address").get("zipcode")}"""
                                    
                                        try:
                                            display_directions_to_customer_location(
                                                engineer_address,
                                                customer_address,
                                                service_request.get(
                                                    "customer_contact"
                                                ).get("phone_number"),
                                                service_request.get(
                                                    "customer_contact"
                                                ).get("email"),
                                            )

                                        except Exception as error:
                                            st.toast(
                                                "Location services are currently unavailable"
                                            )

                                    coly.link_button(
                                        "",
                                        url=get_service_manual_url(service_request.get("appliance_details").get("category"), service_request.get("appliance_details").get("sub_category")),
                                        icon=":material/quick_reference:",
                                        width='stretch'
                                    )

                                    if colz.button(
                                        "View Details",
                                        icon=":material/notes:",
                                        width='stretch',
                                        key=f"_button_request_details_{service_request.get('request_id')}"
                                    ):
                                        dialog_view_service_request_details(
                                            service_request.get("request_id"),
                                            service_request,
                                        )
                                        
                                st.space(1)

                    if assigned_count == 0:
                        st.markdown("<BR>" * 4, unsafe_allow_html=True)

                        sac.result(
                            label="No Assigned Requests",
                            description="You currently have no requests assigned to you",
                            status="empty",
                        )

                elif tab_request_assignment_status.lower() == "new":
                    new_count = 0

                    for service_request in st.session_state.onsite_service_requests:
                        if (
                            service_request.get("assignment_status")
                            == "pending_confirmation"
                        ):
                            new_count += 1

                            with stylable_container(
                                key=f"_container_with_border_new_{new_count}",
                                css_styles=f"""
                                    {{
                                        background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                        border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                        border-radius: 0.6rem;
                                        padding: calc(1em - 1px)
                                    }}
                                    """,
                            ):
                                cola, colb, colc = st.columns([0.75, 2.71, 1.5])

                                with cola:
                                    st.image(
                                        service_request.get("appliance_details").get(
                                            "appliance_image_url"
                                        ),
                                        width='stretch',
                                    )

                                with colb:
                                    colx, coly = st.columns([20, 0.01])

                                    with colx:
                                        st.markdown(
                                            f"<H5>{
                                                service_request.get('request_title')}</H5>",
                                            unsafe_allow_html=True,
                                        )

                                        st.markdown(
                                            f"""
                                            <P >
                                                {service_request.get('appliance_details').get('sub_category')} • {service_request.get('request_id')}
                                            </P>
                                            """,
                                            unsafe_allow_html=True,
                                        )

                                        st.markdown(
                                            f"""
                                            <div class="div-truncate-text">
                                                <P align='left'>{service_request.get('description')}...</P>
                                            </div>
                                            """,
                                            unsafe_allow_html=True,
                                        )

                                with colc:
                                    st.markdown("<BR>", unsafe_allow_html=True)

                                    st.markdown(
                                        f"""
                                        <P class="p-service-request-status" align='right'>
                                            <font size=4>
                                                <B>
                                                    Status: Pending &nbsp
                                                </B>
                                            </font>
                                        </P>
                                        """,
                                        unsafe_allow_html=True,
                                    )

                                    st.write(" ")
                                    colx, coly = st.columns([0.9, 3])

                                    with colx:
                                        if st.button(
                                            "",
                                            icon=":material/check_circle:",
                                            width='stretch',
                                            key=f"_edit_service_reques.t_{
                                                service_request.get('request_id')}",
                                        ):
                                            dialog_review_service_request(
                                                service_request.get("request_id"),
                                                service_request,
                                            )

                                    with coly:
                                        if st.button(
                                            "View Details",
                                            icon=":material/page_info:",
                                            width='stretch',
                                            key=f"_recent_service_request_deta.ils_{
                                                service_request.get('request_id')}",
                                        ):
                                            dialog_view_service_request_details(
                                                service_request.get("request_id"),
                                                service_request,
                                                is_approved=False,
                                            )
                                st.space(1)

                    if new_count == 0:
                        st.markdown("<BR>" * 4, unsafe_allow_html=True)

                        sac.result(
                            label="No New Requests",
                            description="No new requests have been assigned to you",
                            status="empty",
                        )

                else:
                    resolved_count = 0

                    for service_request in st.session_state.onsite_service_requests:
                        if (
                            service_request.get("assignment_status") == "confirmed"
                        ) and (service_request.get("ticket_status") == "resolved"):
                            resolved_count += 1

                            with stylable_container(
                                key=f"container_with_border_{resolved_count}",
                                css_styles=f"""
                                    {{
                                        background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                        border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                        border-radius: 0.6rem;
                                        padding: calc(1em - 1px)
                                    }}
                                    """,
                            ):
                                cola, colb, colc = st.columns(
                                    [0.75, 2.71, 1.5],
                                    vertical_alignment="center"
                                )

                                cola.image(
                                    service_request.get("appliance_details").get(
                                        "appliance_image_url"
                                    ),
                                    width='stretch',
                                )

                                with colb:
                                    colx, _ = st.columns([20, 0.01])

                                    with colx:
                                        st.markdown(
                                            f"<H5>{service_request.get('request_title')}</H5>",
                                            unsafe_allow_html=True,
                                        )

                                        st.markdown(
                                            f"""
                                            <P class="p-service-request-request-id-serial-number">
                                                {service_request.get('appliance_details').get('sub_category')} &nbsp;•&nbsp; {service_request.get('request_id')}
                                            </P>
                                            """,
                                            unsafe_allow_html=True,
                                        )

                                        st.markdown(
                                            f"""
                                            <div class="div-truncate-text">
                                                <P align='left'>{service_request.get('description')}...</P>
                                            </div>
                                            """,
                                            unsafe_allow_html=True,
                                        )
                                        st.write("")

                                with colc:
                                    st.markdown("<BR>", unsafe_allow_html=True)

                                    st.markdown(
                                        f"""
                                        <P class="p-service-request-status" align='right'>
                                            <font size=4>
                                                <B>
                                                    Status: {service_request.get('ticket_status').capitalize()} &nbsp
                                                </B>
                                            </font>
                                        </P>
                                        """,
                                        unsafe_allow_html=True,
                                    )

                                    st.write(" ")

                                    _, colx, coly = st.columns([0.7, 0.9, 3.5])

                                    with colx:
                                        st.link_button(
                                            "",
                                            url="",
                                            icon=":material/description:",
                                            help="Invoice",
                                            width='stretch',
                                        )

                                    with coly:
                                        if st.button(
                                            "Resolution Notes",
                                            icon=":material/notes:",
                                            width='stretch',
                                            key=f"_recent_service_request_deta.ils_{
                                                service_request.get('request_id')}",
                                        ):
                                            dialog_display_resolution_details(
                                                service_request
                                            )
                                
                                st.space(1)

                    if resolved_count == 0:
                        st.markdown("<BR>" * 4, unsafe_allow_html=True)

                        sac.result(
                            label="No Resolved Requests",
                            description="You have no service requests marked resolved",
                            status="empty",
                        )

        elif selected_menu_item == "View Requests":
            open_service_requests = {}

            for service_request in st.session_state.onsite_service_requests:
                if (service_request.get("assignment_status") == "confirmed") and (
                    service_request.get("ticket_status") != "resolved"
                ):
                    open_service_requests[service_request.get("request_id")] = (
                        service_request
                    )

            with sidebar_container:
                request_id_to_view = st.selectbox(
                    "Request Id",
                    open_service_requests.keys(),
                    index=None,
                    placeholder="Select Request Id to View",
                    label_visibility="collapsed"
                )

                if request_id_to_view:
                    st.markdown(
                        f"""
                        <style>
                            a {{
                                color: {st.session_state.themes["dark" if st.session_state.themes["current_theme"] == "light" else "light"]["theme.textColor"]} !important;
                                text-decoration: none; /* Optional: Removes underline */
                            }}

                            a:hover, a:visited, a:active {{
                                color: {st.session_state.themes["dark" if st.session_state.themes["current_theme"] == "light" else "light"]["theme.textColor"]} !important;
                            }}
                        </style>
                        """,
                        unsafe_allow_html=True,
                    )

                    @st.cache_data(show_spinner=False)
                    def get_service_manual(session_id, request_id):
                        service_manual_bucket = ServiceManualBucket()
                        service_manual_url = service_manual_bucket.fetch_service_manual_url(
                            f"{
                                open_service_requests.get(request_id).get("appliance_details").get("category").lower().replace(
                                    ' ',
                                    '_').replace(
                                    '-',
                                    '_').replace(
                                    '/',
                                    '_')}/{
                                open_service_requests.get(request_id).get("appliance_details").get("sub_category").lower().replace(
                                    " ",
                                    "_").replace(
                                    "-",
                                    "_").replace(
                                    "/",
                                    "_")}_service_guide.pdf"
                        )
                        return service_manual_url

                    service_manual_url = get_service_manual(st.session_state.session_id, request_id_to_view)

                    @st.cache_data(show_spinner=False)
                    def get_warranty_certificate_url(session_id, request_id):
                        customer_records_bucket = CustomerRecordsBucket()

                        try:
                            warranty_certificate_url = (
                                customer_records_bucket.fetch_warranty_certificate_url(
                                    open_service_requests.get(request_id).get(
                                        "customer_id"
                                    ),
                                    open_service_requests.get(request_id)
                                    .get("appliance_details")
                                    .get("serial_number"),
                                    open_service_requests.get(request_id)
                                    .get("appliance_details")
                                    .get("sub_category"),
                                )
                            )

                        except Exception as error:
                            warranty_certificate_url = "www.example.com"
                        return warranty_certificate_url

                    warranty_certificate_url = get_warranty_certificate_url(
                        st.session_state.session_id, 
                        request_id_to_view
                    )

                    with st.container(border=False):
                        with stylable_container(
                            key="_sidebar_container_service_manual_card",
                            css_styles=f"""
                                {{
                                    background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["cardColor"]};
                                    border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};
                                    border-radius: 0.6rem;
                                    padding: calc(1em - 1px)
                                }}
                                """,
                        ):
                            with st.container(border=False):
                                st.markdown(
                                    "<B>Reference Documents</B>",
                                    unsafe_allow_html=True
                                )
                                cola, colb = st.columns([0.9, 4], vertical_alignment="center")

                                with cola:
                                    st.image(
                                        "assets/app_graphics/troubleshoot_guide_banner.png",
                                        width='stretch',
                                    )
                                with colb:
                                    st.link_button(
                                        "Open Service Manual",
                                        url=service_manual_url,
                                        icon=":material/developer_guide:",
                                        width='stretch',
                                        type="secondary"
                                    )

                                cola, colb = st.columns([0.9, 4], vertical_alignment="center")

                                with cola:
                                    st.image(
                                        "assets/app_graphics/warranty_document_banner.png",
                                        width='stretch',
                                    )
                                with colb:
                                    st.link_button(
                                        "Warranty Certificate",
                                        url=warranty_certificate_url,
                                        icon=":material/picture_as_pdf:",
                                        width='stretch',
                                        type="secondary"
                                    )

                                st.space(1)

                else:
                    st.markdown("<BR><BR>", unsafe_allow_html=True)

            with st.sidebar:
                st.write(" ")
                st.markdown("<BR>", unsafe_allow_html=True)

                cola, colb = st.columns([4.5, 1])

                with cola:
                    if st.button(
                        "Manage Account",
                        icon=":material/manage_accounts:",
                        width='stretch',
                    ):
                        dialog_manage_account()

                with colb:
                    if st.button(
                        "",
                        icon=":material/logout:",
                        help="Log Out",
                        width='stretch',
                    ):
                        previous_theme = "dark"
                        tdict = st.session_state.themes["dark"]

                        for vkey, vval in tdict.items():
                            if vkey.startswith("theme"):
                                st._config.set_option(vkey, vval)

                        st.session_state.themes["refreshed"] = False
                        st.session_state.themes["current_theme"] = "light"

                        st.session_state.clear()
                        st.cache_data.clear()
                        st.cache_resource.clear()

                        st.rerun()

            if request_id_to_view:
                with st.container(border=False):
                    with stylable_container(
                        key="sidebar_container_with_border",
                        css_styles=f"""
                            {{
                                background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};;
                                border-radius: 0.6rem;
                                padding: calc(1em - 1px)
                            }}
                            """,
                    ):
                        with st.container(border=False):
                            cola, colb = st.columns([0.7, 4], vertical_alignment="center")

                            with cola:
                                st.image(
                                    open_service_requests.get(request_id_to_view)
                                    .get("appliance_details")
                                    .get("appliance_image_url"),
                                    width='stretch',
                                )
                            
                            with colb:
                                colx, coly = st.columns([2.5, 1])

                                with colx:
                                    st.markdown(
                                        f"""
                                        <P class="p-ticket-details-ribbon-title">
                                            Request Id: {request_id_to_view}
                                        </P>
                                        <H4 class="h4-ticket-details-ribbon-title">
                                            {open_service_requests.get(request_id_to_view).get('request_title')}
                                        </H4>
                                        """,
                                        unsafe_allow_html=True,
                                    )

                                with coly:
                                    st.markdown(
                                        f"""
                                        <BR>
                                        <H5 class="h5-ticket-details-status" align='right'>
                                            Status: {open_service_requests.get(request_id_to_view).get('ticket_status').capitalize()} 
                                        """,
                                        unsafe_allow_html=True,
                                    )

                                cola, colb = st.columns([1.6, 1], vertical_alignment="center")

                                cola.markdown(
                                    f"""
                                    {open_service_requests.get(request_id_to_view).get('appliance_details').get('brand')} {open_service_requests.get(request_id_to_view).get('appliance_details').get('sub_category')} • Model No.: {open_service_requests.get(request_id_to_view).get('appliance_details').get('model_number')}
                                    <BR>
                                    Serial No.: {open_service_requests.get(request_id_to_view).get('appliance_details').get('serial_number')} • Warranty Valid Until: {datetime.datetime.strptime(open_service_requests.get(request_id_to_view).get('appliance_details').get('warranty_expiration'), "%Y-%m-%d").strftime("%B %d, %Y")}
                                    """,
                                    unsafe_allow_html=True,
                                )

                                with colb:
                                    colx, coly, colz = st.columns(
                                        [1.1, 2.75, 2.72], 
                                        vertical_alignment="top"
                                    )

                                    with colx:
                                        if st.button(
                                            "",
                                            icon=":material/format_list_bulleted:",
                                            width='stretch',
                                            key=f"_more_options_button"
                                        ):
                                            dialog_view_more_ticket_options(
                                                request_id_to_view,
                                                open_service_requests.get(request_id_to_view),
                                            )

                                    with coly:
                                        if st.button(
                                            "Directions",
                                            icon=":material/location_on:",
                                            width='stretch',
                                            key="_commute_button"
                                        ):
                                            query_engineers = QueryEngineers()

                                            engineer_address_data = (
                                                query_engineers.fetch_engineer_details_by_id(
                                                    st.session_state.engineer_id,
                                                    ["street", "city", "district", "state", "zip_code"],
                                                )
                                            )

                                            engineer_address = f"""{engineer_address_data.get("street")}, 
                                            {engineer_address_data.get("city")},
                                            {engineer_address_data.get("district")},
                                            {engineer_address_data.get("state")} - 
                                            {engineer_address_data.get("zip_code")}
                                            """

                                            customer_address = f"""{open_service_requests.get(request_id_to_view).get("address").get("street")},
                                            {open_service_requests.get(request_id_to_view).get("address").get("city")},
                                            {open_service_requests.get(request_id_to_view).get("address").get("state")} -
                                            {open_service_requests.get(request_id_to_view).get("address").get("zipcode")}
                                            """
                                            
                                            try:
                                                display_directions_to_customer_location(
                                                    engineer_address,
                                                    customer_address,
                                                    contact_number=open_service_requests.get(
                                                        request_id_to_view
                                                    )
                                                    .get("customer_contact")
                                                    .get("phone_number"),
                                                    email_id=open_service_requests.get(request_id_to_view)
                                                    .get("customer_contact")
                                                    .get("email"),
                                                )

                                            except Exception as error:
                                                pass

                                    with colz:
                                        with stylable_container(
                                            "button_resolve_ticket",
                                            css_styles="""
                                            button {
                                                background-color: #3367D6;
                                                border: #274AB3;
                                                color: #FFFFFF;
                                            }""",
                                        ):
                                            button_resolve_ticket = st.button(
                                                "Resolve", 
                                                icon=":material/task:", 
                                                key="_resolve_button", 
                                                width='stretch'
                                            )

                                        if button_resolve_ticket:
                                            dialog_resolve_service_request(
                                                request_id_to_view,
                                                open_service_requests.get(request_id_to_view),
                                            )

                            st.space(1)

                colp, colq = st.columns([2.15, 1])

                with colp:
                    with st.container(border=False):
                        with stylable_container(
                            key="sidebar_container_with_border_desc",
                            css_styles=f"""
                                {{
                                    background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                    border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};;
                                    border-radius: 0.6rem;
                                    padding: calc(1em - 1px)
                                }}
                                """,
                        ):
                            request_created_on = datetime.datetime.strptime(
                                open_service_requests.get(request_id_to_view).get("created_on"),
                                "%Y-%m-%d %H:%M:%S",
                            )
                                    
                            with st.container(border=False):
                                st.markdown(
                                    f"""
                                    <H5>Description</H5>
                                    {open_service_requests.get(request_id_to_view).get('description')}
                                    <BR><BR>
                                    """,
                                    unsafe_allow_html=True,
                                )

                                st.markdown(
                                    f"""<B>Created on: </B>
                                    {request_created_on.strftime("%B %d, %Y at %I:%M %p")}
                                    <BR>
                                    """,
                                    unsafe_allow_html=True,
                                )

                            st.space(1)

                with colq:
                    with st.container(border=False):
                        with stylable_container(
                            key="sidebar_container_with_border_contact_card",
                            css_styles=f"""
                                {{
                                    background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                    border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};;
                                    border-radius: 0.6rem;
                                    padding: calc(1em - 1px)
                                }}
                                """,
                        ):
                            request_created_on = datetime.datetime.strptime(
                                open_service_requests.get(request_id_to_view).get("created_on"),
                                "%Y-%m-%d %H:%M:%S",
                            )
                            
                            with st.container(border=False):
                                st.markdown(
                                    f"""
                                    <H5>Contact Information</H5>
                                    <B>Phone: </B>
                                    {open_service_requests.get(request_id_to_view).get('customer_contact').get('phone_number')}
                                    <BR><B>Email: </B>
                                    {open_service_requests.get(request_id_to_view).get('customer_contact').get('email')}
                                    <BR><BR>
                                    """,
                                    unsafe_allow_html=True,
                                )

                                customer_address = f"""
                                {open_service_requests.get(request_id_to_view).get("address").get("street")},
                                {open_service_requests.get(request_id_to_view).get("address").get("city")},
                                {open_service_requests.get(request_id_to_view).get("address").get("state")} -
                                {open_service_requests.get(request_id_to_view).get("address").get("zipcode")}
                                """
                                st.markdown(
                                    f"""
                                    <B>Address: </B> {customer_address}
                                    """,
                                    unsafe_allow_html=True,
                                )

                            st.space(1)

                with colp.container(border=False, height=475):
                    with stylable_container(
                        key="_sidebar_container_with_border_activity_card",
                        css_styles=f"""
                            {{
                                background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};;
                                border-radius: 0.6rem;
                                padding: calc(1em - 1px)
                            }}
                            """,
                    ):
                        with st.container(border=False):
                            st.markdown(
                                f"""
                                <H5>Activity</H5>
                                """,
                                unsafe_allow_html=True,
                            )

                            @st.cache_data(show_spinner=False)
                            def fetch_and_cache_ticket_activity(session_id, customer_id, request_id):
                                onsite_service_request_collection = (
                                    OnsiteServiceRequestCollection()
                                )
                                return onsite_service_request_collection.fetch_service_request_activity(
                                    customer_id, request_id
                                )

                            with st.form(
                                key="_form_post_ticket_activity",
                                clear_on_submit=True,
                                border=False
                            ):
                                with st.expander(
                                    "Post Update", 
                                    expanded=False,
                                    icon=":material/edit_square:"
                                ):
                                    engineer_notes = bleach.clean(
                                        st.text_area(
                                            "Enter Engineer notes",
                                            placeholder="Share new update to post...",
                                            label_visibility="collapsed",
                                        )
                                    )

                                    with stylable_container(
                                        "button_post_update",
                                        css_styles="""
                                        button {
                                            background-color: #3367D6;
                                            border: #274AB3;
                                            color: #FFFFFF;
                                        }""",
                                    ):
                                        button_post_update = st.form_submit_button(
                                            "Post Update",
                                            icon=":material/library_add:",
                                        )

                                    if button_post_update:
                                        if len(engineer_notes) > 0:
                                            onsite_service_request_collection = (
                                                OnsiteServiceRequestCollection()
                                            )

                                            onsite_service_request_collection.add_service_request_activity(
                                                open_service_requests.get(
                                                    request_id_to_view
                                                ).get("customer_id"),
                                                request_id_to_view,
                                                "Engineer",
                                                engineer_notes,
                                            )

                                            try:
                                                fetch_and_cache_ticket_activity.clear()
                                            except Exception as error:
                                                pass

                                            del st.session_state.onsite_service_requests

                                            st.session_state.onsite_service_requests = onsite_service_request_collection.fetch_onsite_service_request_details_by_engineer_id(
                                                st.session_state.engineer_id
                                            )

                                            st.toast("Update posted!")
                                            time.sleep(3)
                                            st.rerun()

                                        else:
                                            alert = st.warning(
                                                "Enter notes to add", icon=":material/warning:"
                                            )
                                            time.sleep(3)
                                            alert.empty()

                                    st.space(1)

                            ticket_activity = fetch_and_cache_ticket_activity(
                                st.session_state.session_id,
                                open_service_requests.get(request_id_to_view).get(
                                    "customer_id"
                                ),
                                request_id_to_view,
                            )

                            for activity in ticket_activity:
                                with st.container(border=False):
                                    with stylable_container(
                                        key=f"_ticket_detailed_activity_card_{activity.get('timestamp')}",
                                        css_styles=f"""
                                            {{
                                                background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["cardColor"]};
                                                border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};;
                                                border-radius: 0.6rem;
                                                padding: calc(1em - 1px)
                                            }}
                                            """,
                                    ):
                                        added_by = activity.get("added_by")

                                        if added_by.lower() == "engineer":
                                            image_path = "assets/avatars/chatbot/engineer_avatar.jpg"
                                        elif added_by.lower() == "customer":
                                            image_path = "assets/avatars/chatbot/customer_avatar.jpg"
                                        else:
                                            image_path = "assets/avatars/chatbot/system_avatar.jpg"

                                        timestamp = datetime.datetime.strptime(
                                            activity.get("timestamp"), "%Y-%m-%d %H:%M:%S"
                                        ).strftime("%B %d, %Y (%H:%M Hrs)")
                                            
                                        with st.container(border=False):
                                            colx, coly = st.columns([1, 18], vertical_alignment="center")

                                            try:
                                                colx.image(image_path)
                                            except Exception as error:
                                                colx.image("assets/avatars/chatbot/agent_logo.png")

                                            coly.markdown(
                                                f"{added_by.capitalize()} • {timestamp}", 
                                                unsafe_allow_html=True
                                            )
                                            st.markdown(activity.get("notes"))
                                        
                                        st.space(1)
                            st.space(1)

                with colq.container(border=False):
                    with stylable_container(
                        key="sidebar_container_with_border_past_ticket_details",
                        css_styles=f"""
                            {{
                                background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};;
                                border-radius: 0.6rem;
                                padding: calc(1em - 1px)
                            }}
                            """,
                    ):
                        st.markdown(
                            f"""
                            <H5>Service History</H5>
                            """,
                            unsafe_allow_html=True,
                        )
                        st.write(" ")

                        @st.cache_data(show_spinner=False)
                        def fetch_and_cache_appliance_service_request_history(
                            session_id, customer_id, serial_number
                        ):
                            onsite_service_request_collection = OnsiteServiceRequestCollection()

                            appliance_service_request_history = onsite_service_request_collection.fetch_resolution_details_by_appliance_serial_number(
                                customer_id, 
                                serial_number
                            )

                            if request_id_to_view in appliance_service_request_history:
                                del appliance_service_request_history[
                                    request_id_to_view
                                ]

                            return appliance_service_request_history

                        appliance_service_request_history = (
                            fetch_and_cache_appliance_service_request_history(
                                st.session_state.session_id,
                                open_service_requests.get(request_id_to_view).get(
                                    "customer_id"
                                ),
                                open_service_requests.get(request_id_to_view)
                                .get("appliance_details")
                                .get("serial_number"),
                            )
                        )

                        if len(appliance_service_request_history) == 0:
                            st.markdown("<BR>", unsafe_allow_html=True)
                            sac.result(
                                label="No History Available",
                                description="This appliance has no recorded service history",
                                status="empty",
                            )

                        else:
                            service_history_request_ids = list(
                                appliance_service_request_history.keys()
                            )

                            with st.expander(
                                "Search by Id", 
                                expanded=False,
                                icon=":material/manage_search:"
                            ):
                                selected_request_id = st.selectbox(
                                    "Select Request Id",
                                    service_history_request_ids,
                                    index=None,
                                    placeholder="Select Request Id",
                                    label_visibility="collapsed"
                                )

                                with stylable_container(
                                    "button_post_update_search_by_id",
                                    css_styles="""
                                    button {
                                        background-color: #3367D6;
                                        border: #274AB3;
                                        color: #FFFFFF;
                                    }""",
                                ):
                                    button_view_details = st.button(
                                        "View Details",
                                        icon=":material/notes:",
                                        width='stretch',
                                        key="_view_service_history_request_button"
                                    )

                                st.space(1)

                                if button_view_details:
                                    dialog_display_past_service_request_details(
                                        appliance_service_request_history.get(
                                            selected_request_id
                                        )
                                    )

                            for count, request_id in enumerate(
                                service_history_request_ids
                            ):
                                if count > 2: break

                                with st.container(border=False):
                                    with stylable_container(
                                        key=f"_ticket_activity_card_{request_id}",
                                        css_styles=f"""
                                            {{
                                                background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["cardColor"]};
                                                border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};;
                                                border-radius: 0.6rem;
                                                padding: calc(1em - 1px)
                                            }}
                                            """,
                                    ):
                                        colx, coly = st.columns(
                                            [1, 7], 
                                            vertical_alignment="center"
                                        )

                                        colx.image("assets/placeholders/trident_green.png")
                                        coly.markdown(
                                            f"Request Id: {request_id}",
                                            unsafe_allow_html=True
                                        )
                                        st.write(" ")

                                        st.markdown(
                                            f"""<B>
                                            {appliance_service_request_history.get(request_id).get("request_title", "Title Unavailable")}
                                            </B><BR>
                                            Raised On: {datetime.datetime.strptime(appliance_service_request_history.get(request_id).get("created_on", "Not Found"), "%Y-%m-%d %H:%M:%S").strftime("%B %d, %Y")}
                                            <BR>""",
                                            unsafe_allow_html=True
                                        )
                                        st.write("")
                                        if st.button(
                                            "View Details", 
                                            icon=":material/notes:",
                                            width='stretch', 
                                            key=f"_{request_id}_view_details_button"
                                        ):
                                            dialog_display_past_service_request_details(
                                                appliance_service_request_history.get(
                                                    request_id
                                                )
                                            )

            else:
                @st.cache_data(show_spinner=False)
                def fetch_and_cache_optimized_route(
                    session_id, 
                    onsite_service_requests
                ):
                    addresses = []

                    for request in onsite_service_requests:
                        if request.get("ticket_status").lower() == "open" and request.get("assignment_status").lower() == "confirmed":
                            street = request.get("address").get("street")
                            city = request.get("address").get("city")
                            state = request.get("address").get("state")
                            zipcode = request.get("address").get("zipcode")

                            full_address = f"{street}, {city}, {state}-{zipcode}"
                            
                            request_id = request.get("request_id")
                            request_title = request.get("request_title")

                            addresses.append(
                                {
                                    "request_id": request_id,
                                    "full_address": full_address,
                                    "request_title": request_title
                                }
                            )

                    location_services = LocationServices()
                    optimized_route = location_services.optimize_route(addresses)

                    return optimized_route

                optimized_route = fetch_and_cache_optimized_route(
                    st.session_state.session_id,
                    st.session_state.onsite_service_requests
                )

                st.write(" ")
                st.write(" ")
                st.markdown("<BR>"*5, unsafe_allow_html=True)
                #st.write(optimized_route)

                section_1, _, section_2 = st.columns([1.1, 0.1, 0.9], vertical_alignment="center")

                with section_1:
                    st.markdown("<BR>", unsafe_allow_html=True)
                    st.markdown(
                        f"""
                        <BR>
                        <H1 class='h1-home-welcome-title'>
                            Hello, {st.session_state.engineer_details.get("first_name")} {st.session_state.engineer_details.get("last_name")}
                        </H1>
                        """,
                        unsafe_allow_html=True,
                    )

                    st.markdown(
                        """
                        <H2 class='h1-home-welcome-subtitle'>
                            Select a Request to View Details
                        </H2><BR>
                        """,
                        unsafe_allow_html=True,
                    )

                with section_2:
                    st.markdown("<H6>Recommended Resolution Order</H6>", unsafe_allow_html=True)

                    for route in optimized_route.get("optimized_route"):
                        with st.container(border=False):
                            with stylable_container(
                                key=f"_container_route_optimization_{route.get('request_id')}",
                                css_styles=f"""
                                    {{
                                        background-color: {st.session_state.themes[st.session_state.themes["current_theme"]]["containerColor"]};
                                        border: 1px solid {st.session_state.themes[st.session_state.themes["current_theme"]]["containerBoundaryColor"]};;
                                        border-radius: 0.6rem;
                                        padding: calc(1em - 1px)
                                    }}
                                    """,
                            ):
                                colx, coly = st.columns([0.3, 2], vertical_alignment="center")

                                colx.image("assets/app_graphics/location_icon.png")
                                coly.markdown(f"<P class='p-route-optimization-card'>Request Id: {route.get('request_id')}</P><B>{route.get('request_title')}</B>", unsafe_allow_html=True)
                                coly.write(" ")
                                st.space(1)

            st.markdown("<BR>", unsafe_allow_html=True)

        else:
            AVATAR_AGENT = "assets/avatars/chatbot/agent_logo.png"

            try:
                adk_runner, current_session_id = initialize_adk(
                    st.session_state.session_id,
                    user_id=st.session_state.engineer_id
                )

            except Exception as e:
                st.error(
                    f"""
                    **Fatal Error:** Could not initialize the ADK Runner or 
                    Session Service. Please try reloading the app or contact 
                    support.
                    """,
                    icon=":material/cancel:"
                )

                st.stop()

            if 'messages' not in st.session_state:
                st.session_state['messages'] = []

            with st.sidebar:
                st.space(size=25)

                colx, coly = st.columns([4.5, 1])

                if coly.button(
                    "",
                    icon=":material/logout:",
                    help="Logout"
                ):
                    st.session_state.clear()
                    st.cache_data.clear()
                    st.cache_resource.clear()

                    st.logout()
                    st.stop()

                if colx.button(
                    "New Chat",
                    icon=":material/edit_square:",
                    width="stretch",
                    help="New Chat"
                ):
                    try:
                        initialize_adk.clear()

                        del st.session_state['messages']
                        del st.session_state['adk_session_id']

                        st.rerun()

                    except Exception as error: pass
            
            for message in st.session_state['messages']:
                if message["role"] == "user":
                    avatar_url = profile_picture_url
                else:
                    avatar_url = AVATAR_AGENT

                with st.chat_message(message["role"], avatar=avatar_url):
                    st.markdown(message["content"], unsafe_allow_html=False)
            
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
                                st.session_state.engineer_id, 
                                adk_runner, 
                                current_session_id, 
                                prompt
                            )

                        except Exception as error:
                            agent_response = f"""
                            Sorry, an error occurred while 
                            processing your request. Please try again later.
                            Error: {error}
                            """

                        st.session_state.messages.append(
                            {
                                "role": "assistant", 
                                "content": agent_response
                            }
                        )

                    def response_generator(response):
                        for word in response:
                            asyncio.run(asyncio.sleep(0.0025))

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
                    <H1 class='h1-home-welcome-title'>
                        Hello, {st.session_state.engineer_details.get("first_name")} {st.session_state.engineer_details.get("last_name")}
                    </H1>
                    """,
                    unsafe_allow_html=True,
                )

                st.markdown(
                    """
                    <H1 class='h1-home-welcome-subtitle'>
                        How can I help you today?
                    </H1><BR>
                    """,
                    unsafe_allow_html=True,
                )

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

        try:
            firebase_credentials = credentials.Certificate(
                json.loads(st.secrets["FIREBASE_SERVICE_ACCOUNT_KEY"])
            )
            firebase_admin.initialize_app(firebase_credentials)

        except Exception as error:
            pass

        col_login_forum, col_image = st.columns(2)

        with col_image:
            st.write(" ")

            if st.session_state.themes["current_theme"] == "dark":
                st.image("assets/app_graphics/welcome_banner_dark.png")

            else:
                st.image("assets/app_graphics/welcome_banner_light.png")

        with col_login_forum:
            colx, _ = st.columns([1.15, 3.85])
            colx.markdown("<BR>", unsafe_allow_html=True)

            if st.session_state.themes["current_theme"] == "dark":
                try:
                    colx.image(
                        "assets/logos/logiq_logo_dark.png", 
                        width='stretch'
                    )
                except: pass

            else:
                try:
                    colx.image(
                        "assets/logos/logiq_logo_light.png", 
                        width='stretch'
                    )
                except: pass

            st.markdown("<BR>" * 2, unsafe_allow_html=True)
            st.markdown(
                "<H2>Welcome to LogIQ!</H2>LogIn to access the Engineer Application. Authorized access by engineers only.",
                unsafe_allow_html=True,
            )

            st.write(" ")
            colx, _ = st.columns([8, 1])

            email = bleach.clean(
                colx.text_input(
                    "Username",
                    placeholder="Enter your username",
                    label_visibility="collapsed",
                )
            )

            password = bleach.clean(
                colx.text_input(
                    "Password",
                    placeholder="Enter your password",
                    type="password",
                    label_visibility="collapsed",
                )
            )

            col1, col2, _ = st.columns([1.5, 1, 0.1], vertical_alignment="top")
            checkbox_remember_me = col1.checkbox("Remember me", value=True)

            if col2.button(
                label="Forgot Password?", width='stretch', type="tertiary"
            ):
                reset_password()

            cola, colb, _ = st.columns([7.1, 0.9, 1])

            button_login = cola.button(
                "LogIn to the Engineer App", width='stretch', type="primary"
            )

            if colb.button(
                "",
                icon=":material/copyright:",
                help="Attribution",
                width='stretch',
            ):
                dialog_attribution()

            if st.session_state.engineer_id is False:
                colx, _ = st.columns([8, 1])

                warning_message = colx.error(
                    "Invalid Username or Password", icon=":material/error:"
                )

                time.sleep(3)
                st.session_state.engineer_id = None

                warning_message.empty()

            if button_login:
                email = email.lower()

                try:
                    api_key = st.secrets["FIREBASE_AUTH_WEB_API_KEY"]
                    base_url = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={api_key}"

                    if "@" not in email:
                        username = email.upper()
                        user = firebase_admin.auth.get_user(username)
                        email = user.email

                    query_engineers = QueryEngineers()
                    engineer_exists = query_engineers.check_engineer_exists_by_email(
                        email
                    )

                    if engineer_exists:
                        data = {"email": email, "password": password}

                        response = requests.post(
                            base_url.format(api_key=api_key), json=data
                        )

                        if response.status_code == 200:
                            st.toast("Logging you in to the engineer app")
                            data = response.json()

                            st.cache_data.clear()
                            st.cache_resource.clear()

                            st.session_state.engineer_id = (
                                firebase_admin.auth.get_user_by_email(email).uid
                            )
                            st.rerun()

                        else:
                            st.session_state.engineer_id = False
                            st.rerun()

                    else:
                        st.toast(
                            "No engineer found with this username. Please check the username and try again."
                        )

                        st.session_state.engineer_id = False
                        time.sleep(5)

                        st.rerun()

                except Exception as error:
                    st.session_state.engineer_id = False
                    st.rerun()
