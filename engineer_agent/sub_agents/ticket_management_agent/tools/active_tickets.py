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
from datetime import datetime, timedelta, timezone
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


def list_active_tickets(engineer_id: str) -> Dict[str, Any]:
    """
    Tool to fetch all active service tickets assigned to a specific engineer.

    This tool connects to Firestore, iterates through all service requests and 
    retrieves tickets where the `assigned_to` field matches the given 
    `engineer_id`. Only unresolved active tickets are included in the result.

    Args:
        engineer_id (str): The unique identifier of the service engineer.

    Returns:
        dict: A dictionary containing:
            - status (str): Indicates the operation result 
                - ("success", "not_found", or "error").

            On success:
            If found. Each ticket contains:
                - active_tickets (list[dict], optional): List of active tickets.
                    - request_id (str): The ticket ID.
                    - title (str): Title of the service request.
                    - description (str): Description of the issue or request.
                    - created_on (str): Timestamp when the ticket was created.
                    - type (str): The type/category of the service request.
                    - status (str): The current ticket status.

            If no tickets are found:
                - active_tickets (list): An empty list.

            On error:
            - message (str, optional): Error message if the operation fails.

    Example:
        >>> list_active_tickets("engineer_123")
        >>> Tool Respone:
            {
                "status": "success",
                "active_tickets": [{
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

        active_tickets = []

        if not docs:
            return {
                "status": "not_found",
                "active_tickets": []
            }

        for customer_collection in docs:
            for ticket_doc in customer_collection.where(
                "assigned_to", "==", engineer_id
            ).stream():
                ticket_details = {}
                service_request_details = ticket_doc.to_dict()

                status = service_request_details.get("ticket_status", "")
                if status.lower() == "resolved":
                    continue

                ticket_details["request_id"] = ticket_doc.id
                ticket_details["customer_id"] = customer_collection.id

                ticket_details["title"] = service_request_details.get("request_title")
                ticket_details["description"] = service_request_details.get("description")
                ticket_details["created_on"] = service_request_details.get("created_on")

                ticket_details["type"] = service_request_details.get("request_type")
                ticket_details["status"] = service_request_details.get("ticket_status")

                active_tickets.append(ticket_details)

        if active_tickets:
            return {
                "status": "success", 
                "active_tickets": active_tickets
            }

        return {
            "status": "not_found", 
            "active_tickets": []
        }

    except Exception as error:
        return {
            "status": "error",
            "message": "An error occurred while fetching active tickets."
        }


def get_ticket_details(customer_id: str, ticket_id: str) -> Dict[str, Any]:
    """
    Tool to fetch detailed information about a specific active service ticket.

    This tool connects to Firestore and retrieves the details of a service 
    request ticket identified by the `ticket_id`. It returns comprehensive 
    information about the ticket if found.

    Args:
        customer_id (str): The unique identifier of the customer.
        ticket_id (str): The unique identifier of the service ticket.

    Returns:
        Dict[str, Any]: A dictionary containing the status of the request and 
            the ticket details if found.

    Example:
        >>> get_ticket_details("CUST1023", "REQ8901")
        >>> Tool Respone:
        {
            "status": "success",
            "ticket_details": {
                "request_title": "Refrigerator not cooling properly",
                "description": "The refrigerator is running but not maintaining temperature.",
                "ticket_status": "active",
                "appliance_details": {
                    "serial_number": "RF1023AB45",
                    "model": "Whirlpool FrostFree 300L"
                },
                "created_on": "2024-12-10 22:54:11",
                "assigned_to": "ENGR204"
            }
        }
    """
    try:
        db = _initialize_firestore_client()

        ticket_doc = db.collection(
            "service_requests").document(
                "onsite").collection(
                    customer_id).document(
                        ticket_id).get()

        if not ticket_doc.exists:
            return {
                "status": "not_found",
                "ticket_details": {}
            }

        ticket_details = ticket_doc.to_dict()

        ticket_details.pop("resolution", None)
        ticket_details.pop("ticket_activity", None)

        return {
            "status": "success",
            "ticket_details": ticket_details
        }

    except Exception as error:
        return {
            "status": "error",
            "message": f"An error occurred while fetching ticket: {error}"
        }
    

def add_new_activity(
    customer_id: str, 
    ticket_id: str, 
    notes: str
) -> Dict[str, Any]:
    """
    Tool to add a new activity note to the specified service request ticket.

    This tool adds a new activity note to the specified service request. If the 
    `ticket_activity` field already exists, the new activity is appended to the 
    existing list. Otherwise, a new field is created.

    Args:
        customer_id (str): The unique ID of the customer.
        ticket_id (str): The unique ID of the specific service request ticket.
        notes (str): The activity or update note added by the engineer.

    Returns:
        dict: A dictionary containing:
            - status (str): Indicates the operation result 
                - ("success", "not_found", or "error").
            - `"message"`: A message describing the outcome of the operation.

    Example:
        >>> add_new_activity("cust1234", "tkt1234", "Replaced motor gears")
        >>> Tool Respone:
        {
            "status": "success",
            "message": "New activity added successfully."
        }
    """
    try:
        db = _initialize_firestore_client()

        doc = (
            db.collection("service_requests")
            .document("onsite")
            .collection(customer_id)
            .document(ticket_id)
            .get()
        )

        IST_TIMEZONE = timezone(timedelta(hours=5, minutes=30))
        current_time = datetime.now(IST_TIMEZONE)

        new_activity = {
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "added_by": "Engineer",
            "notes": notes,
        }

        if doc.exists and "ticket_activity" in doc.to_dict():
            doc.reference.update(
                {
                    "ticket_activity": firestore.ArrayUnion([new_activity])
                }
            )

        else:
            doc.reference.set(
                {
                    "ticket_activity": [new_activity]
                },
                merge=True,
            )

        return {
            "status": "success",
            "message": "New activity added successfully."
        }

    except Exception as error:
        return {
            "status": "error",
            "message": f"An error occurred while adding activity: {error}"
        }


def report_unsafe_working_condition(
    customer_id: str,
    service_request_id: str,
    working_condition_description: str
):
    """
    Tool to report unsafe working conditions encountered during service visit.

    This tool allows an engineer to record details about unsafe or hazardous 
    working environments observed at a customer's location. The description of 
    the unsafe condition is stored in the corresponding service request field.

    Args:
        customer_id (str): The unique ID of the customer.
        service_request_id (str): ID of the service request being updated.
        working_condition_description (str): Textual description of the unsafe 
            working condition encountered by the engineer.

    Returns:
        dict: A dictionary containing:
            - status (str): Indicates the operation result 
                - ("success", "not_found", or "error").
            - message (str): A descriptive message summarizing the outcome.

    Example:
        >>> report_unsafe_working_condition("cust1023", "req687", "Exposed...")
        >>> Tool Respone:
        {
            "status": "success",
            "message": "Unsafe working conditions reported."
        }
    """
    try:
        db = _initialize_firestore_client()

        service_request_ref = (
            db.collection("service_requests")
            .document("onsite")
            .collection(customer_id)
            .document(service_request_id)
        )

        if service_request_ref:
            service_request_ref.update(
                {
                    "unsafe_working_condition_reported": working_condition_description,
                }
            )

            return {
                "status": "success",
                "message": f"Unsafe conditions reported for {service_request_id}"
            }

        else:
            return {
                "status": "not_found",
                "message": "No records found for given customer or serial number."
            }
        
    except Exception as error:
        return {
            "status": "error",
            "message": f"An error occurred while reporting unsafe conditions: {error}"
        }
