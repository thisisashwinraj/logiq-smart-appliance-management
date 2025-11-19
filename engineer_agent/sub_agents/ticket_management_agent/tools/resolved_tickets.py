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

import json
import streamlit as st
from typing import Any, Dict

import firebase_admin
from firebase_admin import credentials, firestore


def _initialize_firestore_client():
    """
    Initializes and returns a Firestore client instance using Firebase Admin 
    SDK credentials.

    This function reads the Firebase service account credentials stored in 
    streamlit's `st.secrets` under the `FIREBASE_SERVICE_ACCOUNT_KEY` key, 
    initializes the Firebase Admin app if it has not already been initialized, 
    and returns a Firestore client object for database operations.

    The function gracefully handles re-initialization attempts by suppressing 
    exceptions if the Firebase app is already initialized.

    Returns:
        firestore.Client: An authenticated Firestore client instance for 
        performing read and write operations.

    Notes:
        - The function assumes that the Firebase service account key is stored 
          securely in `st.secrets["FIREBASE_SERVICE_ACCOUNT_KEY"]`
        - Errors with reinitialization are silently ignored to prevent failures
    """
    try:
        cred = credentials.Certificate(
            json.loads(st.secrets["FIREBASE_SERVICE_ACCOUNT_KEY"])
        )
        firebase_admin.initialize_app(cred)

    except BaseException:
        pass

    firebase_client = firestore.client()
    return firebase_client


def list_resolved_tickets(engineer_id: str) -> Dict[str, Any]:
    """
    Tool to fetch all resolved service tickets assigned to a specific engineer.

    This tool connects to Firestore, iterates through all service requests and 
    retrieves tickets where the `assigned_to` field matches the given 
    `engineer_id`. Only **resolved** tickets are included in the result.

    Args:
        engineer_id (str): The unique identifier of the service engineer.

    Returns:
        dict: A dictionary containing:
            - status (str): Indicates the operation result 
                - ("success", "not_found", or "error").

            On success:
            If found. Each ticket contains:
                - resolved_tickets (list[dict], optional): List of resolved tickets.
                    - request_id (str): The ticket ID.
                    - title (str): Title of the service request.
                    - description (str): Description of the issue or request.
                    - created_on (str): Timestamp when the ticket was created.
                    - type (str): The type/category of the service request.
                    - status (str): The current ticket status.

            If no tickets are found:
                - resolved_tickets (list): An empty list.

            On error:
            - message (str, optional): Error message if the operation fails.

    Example:
        >>> list_resolved_tickets("engineer_123")
        >>> Tool Respone:
            {
                "status": "success",
                "resolved_tickets": [{
                    "request_id": "123456789",
                    "title": "Washing machine leaking",
                    "description": "Water leaking from bottom after spin cycle",
                    "created_on": "2025-02-21 22:26:58",
                    "type": "Mechanical Repair",
                    "status": "open"
                }, ...]
            }
    """
    try:
        db = _initialize_firestore_client()
        docs = db.collection("service_requests").document("onsite").collections()

        resolved_tickets = []

        if not docs:
            return {
                "status": "not_found",
                "resolved_tickets": []
            }

        for customer_collection in docs:
            for ticket_doc in customer_collection.where(
                "assigned_to", "==", engineer_id
            ).stream():
                ticket_details = {}
                service_request = ticket_doc.to_dict()

                status = service_request.get("ticket_status", "")
                if status.lower() != "resolved":
                    continue

                ticket_details["request_id"] = ticket_doc.id
                ticket_details["customer_id"] = customer_collection.id

                ticket_details["title"] = service_request.get("request_title")
                ticket_details["description"] = service_request.get("description")
                ticket_details["created_on"] = service_request.get("created_on")

                ticket_details["type"] = service_request.get("request_type")
                ticket_details["status"] = service_request.get("ticket_status")

                resolved_tickets.append(ticket_details)

        if resolved_tickets:
            return {
                "status": "success", 
                "resolved_tickets": resolved_tickets
            }

        return {
            "status": "not_found", 
            "resolved_tickets": []
        }

    except Exception as error:
        return {
            "status": "error",
            "message": f"An error occurred while listing resolved tickets: {error}"
        }


def get_resolution_history(customer_id: str, serial_number: str) -> Dict[str, Any]:
    """
    Tool to fetch the resolution history of all resolved service requests for a 
    specific appliance.

    For each resolved service request, the tool extracts and returns relevant
    resolution details such as:
    - request ID
    - request title
    - problem description
    - resolution details (excluding OTPs and feedback)
    - created date

    Args:
        customer_id (str): The unique identifier of the customer whose service 
            history is to be fetched.
        serial_number (str): The serial number of the appliance for which the 
            resolution history is required.

    Returns:
        dict: A dictionary containing:
            - status (str): Indicates the operation result 
                - ("success", "not_found", or "error").

            On success:
            If found. Each ticket contains:
            - resolution_history (dict, optional): A dictionary containing the 
                request and resolution details. Each key is a request ID.
                - request_id (str): The ticket ID.
                - request_title (str): Title of the service request.
                - problem_description (str): Description of the issue.
                - resolution_details (dict): Details of the resolution provided.
                - created_on (str): Timestamp when the ticket was created.
            
            If not found:
            - message (str): Message indicating 

            On error:
            - message (str): Error message if the operation fails.

    Example:
        >>> get_resolution_history("CUST12345", "SN987654321")
        >>> Tool Response:
        {
            "205771230020": {
                "end_date": "2025-02-24 19:13:59",
                "additional_notes": "...",
                "start_date": "2025-02-24 18:45:41",
                "action_performed": "...",
                "request_id": "205771230020",
                "request_title": "Microwave oven not heating",
                "description": "My microwave is not heating food...",
                "created_on": "2024-12-10 22:54:11"
            }
        }
    """
    try:
        db = _initialize_firestore_client()

        docs = (
            db.collection("service_requests")
            .document("onsite")
            .collection(customer_id)
        )

        if docs:
            past_resolution_notes = {}

            for ticket_doc in docs.where(
                "appliance_details.serial_number", "==", serial_number
            ).stream():
                service_request = ticket_doc.to_dict()
                request_id = ticket_doc.id

                resolution_details = service_request.get("resolution", None)

                if service_request.get("ticket_status").lower() != "resolved":
                    continue

                if resolution_details:
                    if "feedback" in resolution_details:
                        del resolution_details["feedback"]

                    resolution_details["request_id"] = request_id
                    resolution_details["request_title"] = service_request.get(
                        "request_title"
                    )
                    resolution_details["description"] = service_request.get(
                        "description"
                    )
                    resolution_details["created_on"] = service_request.get(
                        "created_on"
                    )

                    resolution_details.pop("otp", None)
                    past_resolution_notes[request_id] = resolution_details

            return {
                "status": "success",
                "resolution_history": past_resolution_notes
            }

        return {
            "status": "not_found",
            "message": "No records found for given customer or serial number."
        }

    except Exception as error:
        return {
            "status": "error",
            "message": f"An error occurred while fetching resolution history: {error}"
        }
    

def get_resolution_notes(
    customer_id: str, 
    serial_number: str
) -> Dict[str, Any]:
    """
    Tool to retrieve resolution notes for all resolved service requests for a 
    specific appliance owned by a customer.

    This tool searches the customer's service request records and for each
    resolved service request, it collects relevant resolution details such as 
    the issue description, request title, and resolution summary.

    Args:
        customer_id (str): The unique identifier of the customer whose 
            service resolution history is to be fetched.
        serial_number (str): The serial number of the appliance for which 
            past resolution notes are required.

    Returns:
        dict: A dictionary containing:
            - status (str): Indicates the operation result 
                - ("success", "not_found", or "error").
            
            On success:
            - resolution_history: Dictionary mapping each service request ID to 
                its corresponding resolution details.

            If not found or on error:
            - message: A descriptive message explaining the outcome or error.

    Example:
        >>> get_resolution_notes("CUST1023", "SN0987654321")
        >>> Tool Respone:
        {
            "status": "success",
            "resolution_history": {
                "12349876546": {
                    "request_title": "Microwave oven not heating",
                    "description": "Microwave fails to heat food ...",
                    "created_on": "2024-12-10 22:54:11",
                    "action_performed": "Replaced faulty magnetron ...",
                    "end_date": "2025-02-24 19:13:59",
                    "additional_notes": "Advised customer to avoid running ..."
                },
                ...
            }
        }
    """
    try:
        db = _initialize_firestore_client()

        docs = (
            db.collection("service_requests")
            .document("onsite")
            .collection(customer_id)
        )

        if docs:
            past_resolution_notes = {}

            for ticket_doc in docs.where(
                "appliance_details.serial_number", "==", serial_number
            ).stream():
                service_request = ticket_doc.to_dict()
                request_id = ticket_doc.id

                resolution_details = service_request.get("resolution", None)

                if service_request.get("ticket_status").lower() != "resolved":
                    continue

                if resolution_details:
                    if "feedback" in resolution_details:
                        del resolution_details["feedback"]

                    resolution_details["request_title"] = service_request.get(
                        "request_title"
                    )
                    resolution_details["description"] = service_request.get(
                        "description"
                    )
                    resolution_details["created_on"] = service_request.get(
                        "created_on"
                    )

                    past_resolution_notes[request_id] = resolution_details

            return {
                "status": "success",
                "resolution_history": past_resolution_notes
            }

        return {
            "status": "not_found",
            "message": "No records found for given customer or serial number."
        }
    
    except Exception as error:
        return {
            "status": "error",
            "message": f"An error occurred while fetching resolution notes: {error}"
        }
