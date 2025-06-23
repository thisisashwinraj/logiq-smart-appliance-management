import random
import requests
import warnings
import googlemaps
import streamlit as st
from typing import Any, Dict

import dateutil
from datetime import date, datetime, timedelta

import sqlalchemy
import firebase_admin
from firebase_admin import credentials, firestore

from google.cloud.sql.connector import Connector
from google.oauth2.service_account import Credentials
from google.adk.tools.tool_context import ToolContext

warnings.filterwarnings("ignore")


def _initialize_cloud_sql_mysql_db():
    credentials = Credentials.from_service_account_file(
        "config/cloud_sql_editor_service_account_key.json"
    )

    connector = Connector(credentials=credentials)

    def __get_connection_to_cloud_sql():
        return connector.connect(
            st.secrets['CLOUD_SQL_MYSQL_INSTANCE_CONNECTION_STRING'],
            st.secrets['CLOUD_SQL_MYSQL_DRIVER'],
            user=st.secrets['CLOUD_SQL_MYSQL_USER'],
            password=st.secrets["CLOUD_SQL_PASSWORD"],
            db=st.secrets['CLOUD_SQL_MYSQL_DB'],
        )

    pool = sqlalchemy.create_engine(
        "mysql+pymysql://",
        creator=__get_connection_to_cloud_sql,
    )

    return pool


def _initialize_firebase_firestore():
    try:
        cred = credentials.Certificate(
            "config/firebase_service_account_key.json"
        )
        firebase_admin.initialize_app(cred)

    except BaseException:
        pass

    firebase_client = firestore.client()
    return firebase_client


def get_categories_tool() -> Dict[str, Any]:
    """
    Retrieves a comprehensive list of available top-level appliance categories
    from the appliances catalog.

    This tool provides user with the appliance categories to choose from (e.g.,
    "Refrigerator", "Gas Range" etc). It ensures that only valid and currently
    supported appliance categories are presented for registration.

    Args:
        tool_context (ToolContext): Provides context for the tool execution.

    Returns:
        dict: On success, a dictionary containing a list of strings under the
              'available_categories' key.
              Example: {'categories': ['Refrigerator', 'Washer', 'Gas Range']}
              On failure, an error message is returned
    """
    try:
        pool = _initialize_cloud_sql_mysql_db()

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                SELECT DISTINCT category
                FROM appliances
                """
            )

            result = db_conn.execute(query).fetchall()
            categories = [category[0] for category in result]

        return {
            "status": "success",
            "available_categories": categories,
        }

    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def get_sub_categories_tool(
    category: str,
) -> Dict[str, Any]:
    """
    Retrieves a list of valid sub-categories for a given appliance category
    from the product catalog.

    This tool ensures that only sub-categories relevant to the provided
    appliance category are presented to the user, guiding them toward accurate
    product registration.

    Args:
        category (str): The primary appliance category (e.g., 'Washer',
            'Gas Range') for which to retrieve the sub-categories.
        tool_context (ToolContext): Provides context for the tool execution.

    Returns:
        dict: A dictionary containing a list of the appliance sub-categories.
              Returns an error message if the tool encounters an issue.
              Example: {'subcategories': ['Bottom-Mount', ' 'Side-by-Side']}
              for 'Refrigerator'.
    """
    try:
        pool = _initialize_cloud_sql_mysql_db()

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                SELECT DISTINCT sub_category
                FROM appliances
                WHERE category = :category
                """
            )

            result = db_conn.execute(
                query, parameters={"category": category}
            ).fetchall()

        sub_categories = [sub_category[0] for sub_category in result]

        return {
            "status": "success",
            "available_sub_categories": sub_categories,
        }

    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def get_brands_tool(
    category: str,
    sub_category: str,
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """
    Retrieves a list of valid appliance brands associated with a specific
    appliance category and sub-category.

    This tool ensures that customers are presented only with brands that are
    relevant to their previously selected appliance category and sub-category.

    Args:
        category (str): The top-level category of the appliance (e.g. "Washer",
            "Washing Machine").
        sub_category (str): The sub-category of the appliance within the chosen
            category (e.g., "Side-by-Side" for "Refrigerator", "Front Load" for
            "Washing Machine").
        tool_context (ToolContext): Provides context for the tool execution.

    Returns:
        dict: A dictionary containing a list of strings under the 'brands' key.
              Example: {'brands': ['Maytag', 'Amana', 'Mystic']}
    """
    try:
        pool = _initialize_cloud_sql_mysql_db()

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                SELECT DISTINCT brand
                FROM appliances
                WHERE category = :category AND sub_category = :sub_category
                """
            )

            result = db_conn.execute(
                query,
                parameters={
                    "category": category,
                    "sub_category": sub_category,
                },
            ).fetchall()

        brands = [brand[0] for brand in result]

        return {
            "status": "success",
            "available_brands": brands,
        }

    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def get_models_tool(
    category: str, sub_category: str, brand: str, tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Retrieves a list of valid model numbers associated with a specific
    appliance category, sub-category, and brand.

    This tool ensures that customers are presented only with model numbers that
    are valid for their previously selected category, sub-category, and brand.

    Args:
        category (str): The category of the appliance (e.g. "Refrigerator")
        sub_category (str): Sub-category of the appliance (e.g. "Side-by-Side")
        brand (str): The brand of the appliance (e.g., "Amana", "Maytag").
        tool_context (ToolContext): Provides context for the tool execution.

    Returns:
        dict: A dictionary containing a list of strings under the 'models' key.
              Example: {'models': ['MX23198123A', 'ABR982004B', 'RTX552414C']}
    """
    try:
        pool = _initialize_cloud_sql_mysql_db()

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                SELECT DISTINCT model_number
                FROM appliances
                WHERE category = :category
                AND brand = :brand
                AND sub_category = :sub_category
                """
            )

            result = db_conn.execute(
                query,
                parameters={
                    "category": category,
                    "brand": brand,
                    "sub_category": sub_category,
                },
            ).fetchall()

        model_numbers = [model_number[0] for model_number in result]

        return {
            "status": "success",
            "available_model_numbers": model_numbers,
        }

    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def register_new_appliance_tool(
    category: str,
    sub_category: str,
    brand: str,
    model_number: str,
    serial_number: str,
    purchase_date: str,
    purchased_from: str,
    seller: str,
    installation_date: str,
    tool_context: ToolContext,
) -> Dict[str, str]:
    """
    Registers a new household appliance to the customer's profile. This tool is
    the final action in the appliance registration workflow, responsible for
    persisting all the collected appliance details into the backend database.

    It ensures that the customer's ownership of the appliance, along with its
    full specifications and warranty information, is accurately recorded for
    future support, maintenance, and service interactions.

    Args:
        category (str): The top-level category of the appliance
        sub_category (str): The sub-category of the appliance
        brand (str): The brand of the appliance
        model_number (str): The specific model number of the appliance.
        serial_number (str): Serial number of the individual appliance unit.
        purchase_date (str): Date the appliance was purchased (YYYY-MM-DD).
        installation_date (str): Date the appliance was installed (YYYY-MM-DD).
        purchased_from (str): Type of vendor where the appliance was purchased
        seller (str): Specific name of the seller or retailer
        tool_context (ToolContext): Provides context for the tool execution..

    Returns:
        dict: Dictionary indicating the success or failure of the registration.
    """
    try:
        pool = _initialize_cloud_sql_mysql_db()

        purchase_date = datetime.strptime(purchase_date, "%Y-%m-%d")
        installation_date = datetime.strptime(installation_date, "%Y-%m-%d")

        customer_id = tool_context.state.get("customer_id", None)

        if customer_id is None:
            return {
                "status": "error",
                "message": "Unable to validate customer",
                "action_to_take": """
                Inform the user that you are encountering a temporary problem 
                validating their account details & ask them to try again later.
                """
            }

        def _fetch_warranty_period_and_appliance_image_url(
            sub_category: str, brand: str, model_number: str
        ):
            _pool = _initialize_cloud_sql_mysql_db()

            with _pool.connect() as _db_conn:
                query = sqlalchemy.text(
                    """
                    SELECT warranty_period, appliance_image_url
                    FROM appliances
                    WHERE brand = :brand
                    AND sub_category = :sub_category
                    AND model_number = :model_number
                    """
                )

                result = _db_conn.execute(
                    query,
                    parameters={
                        "brand": brand,
                        "sub_category": sub_category,
                        "model_number": model_number,
                    },
                ).fetchone()

            return int(result[0]), result[1]

        warranty_period_in_months, appliance_image_gcs_url = (
            _fetch_warranty_period_and_appliance_image_url(
                sub_category=sub_category,
                brand=brand,
                model_number=model_number,
            )
        )

        warranty_expiration_date = (
            installation_date
            + dateutil.relativedelta.relativedelta(
                months=int(warranty_period_in_months)
            )
        ).strftime("%Y-%m-%d")

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                INSERT INTO customer_appliances (
                customer_id, category, sub_category, brand, model_number, 
                serial_number, purchase_date, warranty_period, 
                warranty_expiration, purchased_from, seller, installation_date, 
                appliance_image_url)
                VALUES (
                :customer_id, :category, :sub_category, :brand, :model_number, 
                :serial_number, :purchase_date, :warranty_period, 
                :warranty_expiration, :purchased_from, :seller, 
                :installation_date, :appliance_image_url)
                """
            )

            db_conn.execute(
                query,
                parameters={
                    "customer_id": customer_id,
                    "category": category,
                    "sub_category": sub_category,
                    "brand": brand,
                    "model_number": model_number,
                    "serial_number": serial_number,
                    "purchase_date": purchase_date,
                    "warranty_period": warranty_period_in_months,
                    "warranty_expiration": warranty_expiration_date,
                    "purchased_from": purchased_from,
                    "seller": seller,
                    "installation_date": installation_date,
                    "appliance_image_url": appliance_image_gcs_url,
                },
            )

            db_conn.commit()

            return {
                "status": "success",
                "message": "Appliance registered successfully!",
            }

    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def get_all_customer_appliances_tool(
    customer_id: str, 
    limit: int, 
    tool_context: ToolContext,
) -> Dict[str, str]:
    """
    Retrieves a list of all appliances registered by a specific customer.

    This tool fetches comprehensive details for each registered appliance,
    allowing the agent to provide information about a customer's owned products

    Args:
        customer_id (str): customer_id of the customer whose appliances are to
                            be retrieved.
        limit (int): The maximum number of appliances to fetch.
                        - Set to -1 to retrieve all registered appliances
                        for the customer.
        tool_context (ToolContext): Provides context for the tool execution.

    Returns:
        dict: A dictionary where keys are the serial numbers of the appliances
              and values are dictionaries containing detailed information for
              each appliance.
    """
    try:
        session_customer_id = tool_context.state.get("customer_id", None)

        if session_customer_id is None or session_customer_id != customer_id:
            return {
                "status": "error",
                "message": "Unable to validate customer",
                "action_to_take": """
                Inform the user that you are encountering a temporary problem 
                validating their account details & ask them to try again later.
                """
            }

        pool = _initialize_cloud_sql_mysql_db()

        with pool.connect() as db_conn:
            if limit == -1:
                query = sqlalchemy.text(
                    """
                    SELECT category, sub_category, brand, model_number, 
                    purchased_from, seller, purchase_date, installation_date, 
                    warranty_period, warranty_expiration, appliance_image_url, 
                    serial_number
                    FROM customer_appliances
                    WHERE customer_id = :customer_id
                    ORDER BY created_on DESC
                    """
                )

            else:
                query = sqlalchemy.text(
                    """
                    SELECT category, sub_category, brand, model_number, 
                    purchased_from, seller, purchase_date, installation_date, 
                    warranty_period, warranty_expiration, appliance_image_url, 
                    serial_number
                    FROM customer_appliances
                    WHERE customer_id = :customer_id
                    ORDER BY created_on DESC
                    LIMIT :limit
                    """
                )

            result = db_conn.execute(
                query, parameters={"customer_id": customer_id, "limit": limit}
            ).fetchall()

        customer_appliances = {}

        for row in result:
            serial_number = row.serial_number

            appliance_details = {
                "category": row[0],
                "sub_category": row[1],
                "brand": row[2],
                "model_number": row[3],
                "serial_number": serial_number,
                "purchased_from": row[4],
                "seller": row[5],
                "purchase_date": row[6].strftime("%Y-%m-%d"),
                "installation_date": row[7].strftime("%Y-%m-%d"),
                "warranty_period": row[8],
                "warranty_expiration": row[9].strftime("%Y-%m-%d"),
                "appliance_image_url": row[10],
                "serial_number": row[11],
            }

            customer_appliances[serial_number] = appliance_details

        return customer_appliances

    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def register_onsite_service_request_tool(
    customer_id: str,
    serial_number: str,
    request_type: str,
    issue_description: str,
    request_title: str,
    phone_number: str,
    email: str,
    street: str,
    city: str,
    state: str,
    zipcode: str,
    tool_context: ToolContext,
) -> Dict[str, str]:
    """
    Registers a new onsite service request for a customer's appliance in the
    backend database.

    This tool is critical for registering a new onsite service request. It
    collects all necessary details, including appliance identification (via
    serial number), the nature of the request, a detailed description of the
    issue, and the customer's contact and location information. It ensures that
    field service engineers receive comprehensive context to prepare for and
    address the service issue effectively.

    Args:
        customer_id (str): Customer's unique identifier.
        serial_number (str): Serial number of the appliance requiring service.
        request_type (str): Type of request (eg. "Calibration", "Installation")
        issue_description (str): Description of the problem or service needed.
        request_title (str): Title of the service request.
        phone_number (str): Customer's phone number.
        email (str): Customer's email address.
        street (str): Street address for the service location.
        city (str): City for the service location.
        state (str): State/province for the service location.
        zipcode (str): Postal code for the service location.
        tool_context (ToolContext): Provides context for the tool execution.

    Returns:
        dict: Dictionary indicating result of the service request registration.
            - On success:
                {
                    'status': 'success',
                    'message': 'Service request registered successfully!',
                    'service_request_id': 'ABCXYZ789'
                }

            - On failure:
                {
                    'status': 'error',
                    'message': 'Failed to register service request.',
                    'error': 'Reason for failure'
                }
    """
    try:
        session_customer_id = tool_context.state.get("customer_id", None)

        if session_customer_id is None or session_customer_id != customer_id:
            return {
                "status": "error",
                "message": "Unable to validate customer",
                "action_to_take": """
                Inform the user that you are encountering a temporary problem 
                validating their account details & ask them to try again later.
                """
            }
        
        firestore_client = _initialize_firebase_firestore()

        def _fetch_appliance_details(
            customer_id: str, serial_number: str
        ) -> Dict:
            _pool = _initialize_cloud_sql_mysql_db()

            with _pool.connect() as _db_conn:
                query = sqlalchemy.text(
                    """
                    SELECT category, sub_category, brand, model_number, 
                    purchased_from, seller, purchase_date, installation_date, 
                    warranty_period, warranty_expiration, appliance_image_url
                    FROM customer_appliances
                    WHERE customer_id = :customer_id
                    AND serial_number = :serial_number
                    """
                )

                result = _db_conn.execute(
                    query,
                    parameters={
                        "customer_id": customer_id,
                        "serial_number": serial_number,
                    },
                ).fetchone()

                customer_appliance_details = {
                    "category": result[0],
                    "sub_category": result[1],
                    "brand": result[2],
                    "model_number": result[3],
                    "serial_number": serial_number,
                    "purchased_from": result[4],
                    "seller": result[5],
                    "purchase_date": result[6],
                    "installation_date": result[7],
                    "warranty_period": result[8],
                    "warranty_expiration": result[9],
                    "appliance_image_url": result[10],
                }

                return customer_appliance_details

        appliance_details = _fetch_appliance_details(
            customer_id=customer_id,
            serial_number=serial_number,
        )

        def _generate_request_id() -> str:
            service_request_id = "2" + "".join(
                [str(random.randint(0, 9)) for _ in range(11)]
            )
            return service_request_id

        service_request_id = _generate_request_id()
        current_timestamp = datetime.utcnow() + timedelta(hours=5, minutes=30)

        onsite_service_request_data = {
            "address": {
                "city": city,
                "state": state,
                "street": street,
                "zipcode": zipcode,
            },
            "appliance_details": {
                "category": appliance_details["category"],
                "sub_category": appliance_details["sub_category"],
                "brand": appliance_details["brand"],
                "model_number": appliance_details["model_number"],
                "serial_number": appliance_details["serial_number"],
                "purchased_from": appliance_details["purchased_from"],
                "seller": appliance_details["seller"],
                "purchase_date": appliance_details["purchase_date"].strftime(
                    "%Y-%m-%d"
                ),
                "installation_date": appliance_details["installation_date"].strftime(
                    "%Y-%m-%d"
                ),
                "warranty_period": appliance_details["warranty_period"],
                "warranty_expiration": appliance_details[
                    "warranty_expiration"
                ].strftime("%Y-%m-%d"),
                "appliance_image_url": appliance_details["appliance_image_url"],
            },
            "assigned_to": "",
            "assigned_on": "",
            "assignment_status": "unassigned",
            "created_on": current_timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "customer_contact": {
                "phone_number": phone_number,
                "email": email,
            },
            "description": issue_description,
            "service_invoice_url": "",
            "request_title": request_title,
            "request_type": request_type,
            "resolution": {
                "action_performed": "",
                "additional_notes": "",
                "end_date": "",
                "feedback": {
                    "comments": "",
                    "rated_on": "",
                    "ratings": "",
                },
                "parts_purchased": "",
                "requested_service": "",
                "start_date": "",
            },
            "ticket_status": "open",
            "total_cost": "",
        }

        (
            firestore_client.collection("service_requests")
            .document("onsite")
            .collection(customer_id)
            .document(service_request_id)
            .set(onsite_service_request_data)
        )

        engineer_assignment_cloud_run_payload = {
            "customer_id": str(customer_id),
            "request_id": str(service_request_id),
        }

        response = requests.post(
            st.secrets['URL_CLOUD_RUN_ONSITE_ENGINEER_ASSIGNMENT_SERVICE'],
            json=engineer_assignment_cloud_run_payload,
        )

        if response.status_code != 200:
            try:
                (
                    firestore_client.collection("service_requests")
                    .document("onsite")
                    .collection(customer_id)
                    .document(service_request_id)
                    .update(
                        {
                            "assigned_to": "ADMIN",
                            "assignment_status": "pending_confirmation",
                        }
                    )
                )

            except Exception as error:
                pass

        return {
            "status": "success",
            "message": "Service request registered successfully!",
            "service_request_id": service_request_id,
        }

    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def update_customer_appliance_details_tool(
    customer_id: str,
    serial_number: str,
    updates: Dict[str, Any],
    tool_context: ToolContext,
) -> Dict[str, Any]:
    """
    Updates specified details for a customer's appliance in the database.

    This tool handles modifications to user-updatable fields of a registered
    appliance. It also performs validation to prevent changes to immutable core
    appliance details.

    Args:
        customer_id (str): Unique identifier of the customer.
        serial_number (str): Serial number of the appliance to update.
        updates (dict): Dictionary of field names and their new values.
                        User-updatable fields include category, sub_category,
                        brand, model_number, serial_number, purchased_from,
                        seller, purchase_date, installation_date.
                        e.g., {'installation_date': '2024-05-01',
                               'seller': 'Online Retailer Inc.'}
        tool_context (ToolContext): Provides context for the tool execution.

    Returns:
        dict: Dictionary indicating the success or failure of the update.
            - On success: `{
                        'status': 'success',
                        'message': 'Appliance details updated successfully!'
                    }`
            - On failure: `{
                        'status': 'failed',
                        'message': 'Failed to update: <reason>'
                    }`
    """
    IMMUTABLE_APPLIANCE_FIELDS = {
        "customer_appliance_id",
        "customer_id",
        "warranty_period",
        "status",
        "warranty_expiration",
        "created_on",
        "updated_on",
        "appliance_image_url",
    }

    try:
        session_customer_id = tool_context.state.get("customer_id", None)

        if session_customer_id is None or session_customer_id != customer_id:
            return {
                "status": "error",
                "message": "Unable to validate customer",
                "action_to_take": """
                Inform the user that you are encountering a temporary problem 
                validating their account details & ask them to try again later.
                """
            }
        
        for field_name in updates.keys():
            if field_name in IMMUTABLE_APPLIANCE_FIELDS:
                return {
                    "status": "error",
                    "message": f"Cannot update immutable field: {field_name}",
                }

        pool = _initialize_cloud_sql_mysql_db()
        
        with pool.connect() as db_conn:
            update_query = "UPDATE customer_appliances SET "
            update_values = {}

            for key, value in updates.items():
                update_query += f"{key} = :{key}, "
                update_values[key] = value

            update_query = update_query[:-2]

            update_query += """ 
            WHERE serial_number = :serial_number 
            AND customer_id = :customer_id;
            """

            update_values["serial_number"] = serial_number
            update_values["customer_id"] = customer_id

            query = sqlalchemy.text(update_query)
            db_conn.execute(query, parameters=update_values)
            db_conn.commit()

        return {
            "status": "success",
            "message": "Appliance details updated successfully!",
        }

    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def delete_customer_appliance_tool(
    customer_id: str, serial_number: str, tool_context: ToolContext
) -> Dict[str, Any]:
    """
    Deletes a specific registered appliance from the customer's database.

    This tool permanently removes an appliance based on its serial number
    and the customer ID. It also ensures that only a verified customer can
    delete their own appliances.

    Args:
        customer_id (str): Unique identifier of the customer.
        serial_number (str): Serial number of the appliance to be deleted.
        tool_context (ToolContext): Provides context for the tool execution.

    Returns:
        dict: Dictionary indicating the deletion status.
            - On success: `{
                'status': 'success',
                'message': 'Appliance deleted successfully.'
            }`
            - On failure: `{
                'status': 'failed',
                'message': 'Failed to delete appliance: <reason>'
            }`
    """
    try:
        session_customer_id = tool_context.state.get("customer_id", None)

        if session_customer_id is None or session_customer_id != customer_id:
            return {
                "status": "error",
                "message": "Unable to validate customer",
                "action_to_take": """
                Inform the user that you are encountering a temporary problem 
                validating their account details & ask them to try again later.
                """
            }
        
        pool = _initialize_cloud_sql_mysql_db()
        
        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                DELETE FROM customer_appliances
                WHERE serial_number = :serial_number
                AND customer_id = :customer_id
                """
            )

            db_conn.execute(
                query,
                parameters={
                    "serial_number": serial_number, "customer_id": customer_id,
                },
            )
            db_conn.commit()

        return {
            "status": "success",
            "message": "Appliance deleted successfully!",
        }

    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }


def get_all_service_requests_briefs_tool(
    customer_id: str, limit: int, tool_context: ToolContext,
) -> Dict[str, Dict[str, str]]:
    """
    Retrieves a brief overview of all service requests for a specific customer.

    This tool fetches a dict of service requests, where each item represents a
    single request with the key being the `request_id` of that request, and the
    corresponding value being a dictionary with information including the
    `request_title`, `request_type`, and `appliance_name`. This tool does not
    provide the complete details of a particular service request.

    Args:
        customer_id (str): Unique identifier of the customer.
        limit (int): Maximum number of service requests to retrieve.
                    - If limit <= 0, all available requests are streamed.

    Returns:
        dict: Dictionary where keys are `request_id` & value is `request_title`
                    - Returns an empty dictionary if no requests are found.
                    - Returns dict with status and error message on error.
    """
    try:
        session_customer_id = tool_context.state.get("customer_id", None)

        if session_customer_id is None or session_customer_id != customer_id:
            return {
                "status": "error",
                "message": "Unable to validate customer",
                "action_to_take": """
                Inform the user that you are encountering a temporary problem 
                validating their account details & ask them to try again later.
                """
            }

        firestore_client = _initialize_firebase_firestore()

        if limit > 0:
            docs = (
                firestore_client.collection("service_requests")
                .document("onsite")
                .collection(customer_id)
                .limit(limit)
                .get()
            )

        else:
            docs = (
                firestore_client.collection("service_requests")
                .document("onsite")
                .collection(customer_id)
                .stream()
            )

        service_requests = {}

        for doc in docs:
            request_data = doc.to_dict()
            service_requests[doc.id] = {
                "request_title": str(request_data["request_title"]),
                "appliance_name": str(
                    request_data["appliance_details"]["brand"]
                    + " "
                    + request_data["appliance_details"]["sub_category"]
                ),
                "request_type": str(request_data["request_type"]),
            }

        return service_requests

    except Exception as error:
        return {
            "status": "error",
            "message": f"Failed to retrieve request briefs: {str(error)}",
        }


def get_service_request_details_tool(
    customer_id: str,
    request_id: str,
    tool_context: ToolContext,
):
    """
    Retrieves comprehensive details for a specific service request.

    This tool fetches all available information for a given service request
    associated with a particular customer.

    Args:
        customer_id (str): Unique identifier of the customer.
        request_id (str): Unique ID of the request to retrieve details for.

    Returns:
        Dict[str, Any]: A dictionary containing all details of the service
        request if found. Returns an empty dictionary ({}) if the request is
        not found for the given customer.
                        - Returns a dictionary with 'status': 'error' and a
                          'message' on an error during retrieval.
    """
    try:
        session_customer_id = tool_context.state.get("customer_id", None)

        if session_customer_id is None or session_customer_id != customer_id:
            return {
                "status": "error",
                "message": "Unable to validate customer",
                "action_to_take": """
                Inform the user that you are encountering a temporary problem 
                validating their account details & ask them to try again later.
                """
            }

        firestore_client = _initialize_firebase_firestore()

        service_request_details_ref = (
            firestore_client.collection("service_requests")
            .document("onsite")
            .collection(customer_id)
            .document(request_id)
        )

        service_request_details = service_request_details_ref.get()

        if service_request_details.exists:
            return service_request_details.to_dict()

        else:
            return {}

    except Exception as error:
        return {
            "status": "error",
            "message": f"Failed to retrieve request briefs: {str(error)}",
        }


def update_service_request_details_tool(
    customer_id: str,
    request_id: str,
    updated_data: Dict[str, str],
    tool_context: ToolContext,
) -> Dict[str, str]:
    """
    Updates specific details of an existing customer service request.

    This tool allows for modifying information related to a service request,
    such as contact details, request title, description, or customer notes. It
    ensures updates are applied only to authorized fields.

    Args:
        customer_id (str): Customer ID of the user who owns the service request
        request_id (str): Unique request ID of the service request to update.
        updated_data (Dict[str, str]): Dictionary of fields to update and their
                                       new values.

    Returns:
        dict: Dictionary indicating the status of the update operation.
    """
    try:
        session_customer_id = tool_context.state.get("customer_id", None)

        if session_customer_id is None or session_customer_id != customer_id:
            return {
                "status": "error",
                "message": "Unable to validate customer",
                "action_to_take": """
                Inform the user that you are encountering a temporary problem 
                validating their account details & ask them to try again later.
                """
            }

        firestore_client = _initialize_firebase_firestore()

        updated_data_fields = updated_data.keys()
        payload = {}

        if "request_title" in updated_data_fields:
            payload["request_title"] = updated_data["request_title"].strip()

        if "description" in updated_data_fields:
            payload["description"] = updated_data["description"].strip()

        if "request_type" in updated_data_fields:
            payload["request_type"] = updated_data["request_type"].strip()

        if "customer_contact_phone_number" in updated_data_fields:
            payload["customer_contact.phone_number"] = updated_data[
                "customer_contact_phone_number"
            ].strip()

        if "customer_contact_email" in updated_data_fields:
            payload["customer_contact.email"] = updated_data[
                "customer_contact_email"
            ].strip()

        if not payload:
            return {
                "status": "error",
                "message": "No valid fields provided for update.",
            }

        doc = (
            firestore_client.collection("service_requests")
            .document("onsite")
            .collection(customer_id)
            .document(request_id)
            .get()
        )

        if doc.exists:
            doc.reference.update(payload)

            return {
                "status": "success",
                "message": "Service request updated successfully!",
            }

    except Exception as error:
        return {
            "status": "error",
            "message": f"Failed to retrieve request briefs: {str(error)}",
        }


def delete_service_request_tool(
    customer_id: str,
    request_id: str,
    tool_context: ToolContext,
) -> Dict[str, str]:
    """
    Deletes a specific service request for a given customer_id from Firestore.

    This tool permanently removes a service request based on its request_id and 
    customer_id. It also ensures that only a verified customer can delete their 
    own appliances.

    Args:
        customer_id (str)): Unique identifier of the customer for whom the service
                     request needs to be deleted. This ID is used to locate
                     the customer's specific service request collection in Firestore.
        request_id: The unique identifier of the service request document to be deleted.
        tool_context: An object providing context for the tool's execution,
                      which includes the current session's state. The
                      `tool_context.state['customer_id']` is used for authentication
                      and validation against the provided `customer_id`.

    Returns:
        A dictionary indicating the outcome of the deletion operation.
        Possible return structures:
        - On successful deletion:
            `{"status": "success", "message": "Service request deleted successfully!"}`
        - If customer ID validation fails (mismatch or session ID missing):
            `{"status": "error", "message": "Unable to validate customer", "action_to_take": "..."}`
            (The 'action_to_take' provides an instruction to the calling agent.)
        - If the specified service request is not found:
            `{"status": "error", "message": "Service request '{request_id}' not found for customer '{customer_id}'."}`
        - On any other unexpected error during the process:
            `{"status": "error", "message": "Failed to delete service request: [error_details]"}`
    """
    try:
        session_customer_id = tool_context.state.get("customer_id", None)

        if session_customer_id is None or session_customer_id != customer_id:
            return {
                "status": "error",
                "message": "Unable to validate customer",
                "action_to_take": """
                Inform the user that you are encountering a temporary problem 
                validating their account details & ask them to try again later.
                """
            }

        firestore_client = _initialize_firebase_firestore()

        doc_ref = (
            firestore_client.collection("service_requests")
            .document("onsite")
            .collection(customer_id)
            .document(request_id)
        )

        doc = doc_ref.get()

        if not doc.exists:
            return {
                "status": "error",
                "message": f"""
                    Service request '{request_id}' not found for customer 
                    '{customer_id}'.
                """,
            }

        doc_ref.delete()

        return {
            "status": "success",
            "message": "Service request deleted successfully!",
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to delete service request: {str(e)}",
        }


def get_customer_details_tool(
    customer_id: str,
    tool_context: ToolContext,
) -> Dict[str, str]:
    """
    Retrieves comprehensive details for a specific customer from the database.

    This tool fetches all relevant profile information based on the provided
    customer ID, ensuring data is returned in a structured dictionary format.
    It includes error handling for cases where the customer is not found or a
    database error occurs.

    Args:
        customer_id (str): Unique identifier (username) of the customer whose
                           details are to be retrieved.

    Returns:
        Dict[str, Any]: Dictionary containing the customer's details if found,
                        or, a dictionary with 'status': 'failed' and a message
                        if the customer is not found or if an error occurs.
    """
    try:
        session_customer_id = tool_context.state.get("customer_id", None)

        if session_customer_id is None or session_customer_id != customer_id:
            return {
                "status": "error",
                "message": "Unable to validate customer",
                "action_to_take": """
                Inform the user that you are encountering a temporary problem 
                validating their account details & ask them to try again later.
                """
            }
        
        pool = _initialize_cloud_sql_mysql_db()

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                "SELECT first_name, last_name, dob, gender, email, street, "
                "phone_number, district, city, state, country, zip_code "
                "FROM customers WHERE username = :username"
            )

            result = db_conn.execute(
                query, parameters={"username": customer_id}
            ).fetchone()

        if result is None:
            return {
                "status": "error",
                "message": f"Customer '{customer_id}' not found.",
            }

        customer_details = {
            "first_name": result.first_name,
            "last_name": result.last_name,
            "dob": result.dob.strftime("%Y-%m-%d"),
            "gender": result.gender,
            "email": result.email,
            "phone_number": result.phone_number,
            "street": result.street,
            "district": result.district,
            "city": result.city,
            "state": result.state,
            "country": result.country,
            "zip_code": result.zip_code,
        }

        return customer_details

    except Exception as error:
        return {
            "status": "error",
            "message": f"Failed to retrieve customer details: {str(error)}",
        }


def update_customer_details_tool(
    customer_id: str,
    updates: Dict[str, str],
    tool_context: ToolContext,
) -> Dict[str, str]:
    """
    Updates specific customer details in the Cloud SQL MySQL database.

    This tool dynamically constructs an SQL UPDATE query based on the provided
    'updates' dictionary. It's designed to only update allowed fields, ensuring
    data integrity for customer profiles.

    Args:
        customer_id (str): Customer's unique identifier.
        updates (dict): Dictionary of fields to update and their new values.
                        Keys must correspond to database column names for
                        updatable fields.

    Returns:
        Dict[str, Any]: Dictionary indicating status of the update operation.
    """
    ALLOWED_UPDATE_FIELDS = {
        "first_name",
        "last_name",
        "dob",
        "gender",
        "email",
        "phone_number",
        "street",
        "district",
        "city",
        "state",
        "country",
        "zip_code",
    }

    try:
        session_customer_id = tool_context.state.get("customer_id", None)

        if session_customer_id is None or session_customer_id != customer_id:
            return {
                "status": "error",
                "message": "Unable to validate customer",
                "action_to_take": """
                Inform the user that you are encountering a temporary problem 
                validating their account details & ask them to try again later.
                """
            }
        
        pool = _initialize_cloud_sql_mysql_db()

        with pool.connect() as db_conn:
            update_query = "UPDATE customers SET "
            update_values = {}

            for key, value in updates.items():
                if key in ALLOWED_UPDATE_FIELDS:
                    update_query += f"{key} = :{key}, "
                    update_values[key] = value

                else:
                    return {
                        "status": "error",
                        "message": f"Cannot update immutable field: {key}",
                    }

            update_query = update_query[:-2]
            update_query += " WHERE username = :customer_id;"

            update_values["customer_id"] = customer_id

            query = sqlalchemy.text(update_query)

            db_conn.execute(query, parameters=update_values)
            db_conn.commit()

        return {
            "status": "success",
            "message": "Customer details updated successfully!",
        }

    except Exception as error:
        return {
            "status": "error",
            "message": f"Failed to update customer details: {str(error)}",
        }


def validate_and_format_address_tool(address: str, state: str) -> Dict[str, Any]:
    """
    Validate and standardize an address using Google's Address Validation API,
    with additional processing for Indian addresses via Postal Pincode API.

    This tool determines the validity of a given address, extracts its
    standardized components, and suggests a recommended address structure.
    It's particularly useful for ensuring correct address details for customer
    profiles.

    Args:
        address (str): Complete address string to be validated and formatted.

    Returns:
        dict: Dictionary containing the validation result:
            - status (str): Status of the overall operation (success or error)
            - is_valid (bool): True if address passes validation, else False
            - recommended_address (dict): Dictionary with standardized address
                                          components (Street, District, City,
                                          State, Country, Zipcode) if a valid
                                          address can be generated. Returns
                                          None if the address is not valid or
                                          cannot be parsed.
            - 'message' (str, only on 'failed' status): An error message if the
                                          operation failed.
    """
    try:
        gmaps = googlemaps.Client(
            key="AIzaSyAnN7CAWwqIrjIlvqx5TZFZg_3D5ldju9I"
        )

        is_valid = False

        response = gmaps.addressvalidation(
            [address],
            regionCode="IN",
            locality=state,
        )

        api_response = response.get("result")
        custom_standardized_address = None

        if api_response:
            verdict = api_response.get("verdict", {})
            address_data = api_response.get("address", {})

            validation_granularity = verdict.get("validationGranularity")

            if validation_granularity in [
                "ROUTE",
                "PREMISE",
                "ROOFTOP",
                "POINT_OF_INTEREST",
                "OTHER",
            ]:
                is_valid = True
            else:
                is_valid = False

        custom_standardized_address = None

        if address_data:
            street_parts = []
            district = ""
            city = ""
            state = ""
            country = ""
            zipcode = ""

            for component in address_data.get("addressComponents", []):
                component_type = component.get("componentType")

                long_text = component.get("componentName").get("text", " ")

                if component_type in [
                    "street_address",
                    "route",
                    "park",
                    "natural_feature",
                    "airport",
                    "premise",
                    "subpremise",
                    "intersection",
                    "political",
                    "rooftop",
                    "point_of_interest",
                    "floor",
                    "establishment",
                    "landmark",
                    "parking",
                    "room",
                    "street_number",
                    "bus_station",
                    "train_station",
                    "transit_station",
                ]:
                    if long_text not in street_parts:
                        street_parts.append(long_text)

                elif component_type == "premise" and long_text not in street_parts:
                    street_parts.append(long_text)
                elif component_type == "sublocality_level_1":
                    district = long_text

                elif component_type == "locality":
                    city = long_text
                elif component_type == "administrative_area_level_1":
                    state = long_text

                elif component_type == "country":
                    country = long_text
                elif component_type == "postal_code":
                    zipcode = long_text

            combined_street = " ".join(street_parts).strip()

            if zipcode:
                try:
                    url = f"https://api.postalpincode.in/pincode/{zipcode}"
                    api_response = requests.get(url).json()[0]

                    post_offices = api_response.get("PostOffice")

                    if (
                        post_offices
                        and isinstance(post_offices, list)
                        and len(post_offices) > 0
                    ):
                        district = post_offices[0].get("District")

                    else:
                        district = city

                except Exception as error:
                    district = city

            custom_standardized_address = {
                "Street": combined_street,
                "District": district,
                "City": city,
                "State": state,
                "Country": country,
                "Zipcode": zipcode,
            }

            if not custom_standardized_address["Street"] and address_data.get(
                "postalAddress", {}
            ).get("addressLines"):
                custom_standardized_address["Street"] = address_data[
                    "postalAddress"]["addressLines"][0]

        if not custom_standardized_address:
            custom_standardized_address = "Could not generate a valid address."

        return {
            "is_address_valid": is_valid,
            "standardized_address": custom_standardized_address,
        }

    except Exception as error:
        return {
            "status": "error",
            "is_address_valid": is_valid,
            "message": f"Operation failed mid-way due to {str(error)}",
        }


def get_filtered_appliances_tool(
    filters: Dict[str, str],
) -> Dict[str, Any]:
    """
    Retrieves a list of available appliances from the database, filtered by
    specified criteria.

    This tool allows dynamic filtering of appliances based on attributes like
    brand, category, energy rating, etc., ensuring only available products are
    returned.

    ALLOWED_FILTER_KEYS = {
        'model_number', 'brand', 'category', 'sub_category',
    }

    Args:
        filters (Dict): Dictionary where keys are appliance attributes (column
                        names) and values are the desired filter values.
                        Example: {'brand': 'Amana', 'category': 'Refrigerator'}

    Returns:
        Dict: Dictionary containing the status and either a list of available
              appliances (each as a dictionary) or an error message.
    """
    ALLOWED_FILTER_KEYS = {
        "model_number",
        "brand",
        "category",
        "sub_category",
    }

    try:
        pool = _initialize_cloud_sql_mysql_db()

        with pool.connect() as db_conn:
            base_query = """
                SELECT DISTINCT model_number, appliance_name, brand, category, 
                sub_category, warranty_period, launch_date, energy_rating
                FROM appliances
                WHERE availability_status = 'available' 
                """

            filter_values = {}

            for key, value in filters.items():
                if key in ALLOWED_FILTER_KEYS:
                    base_query += f" AND {key} = :{key}"
                    filter_values[key] = value

            base_query += """
            ORDER BY energy_rating DESC, warranty_period DESC, launch_date DESC
            LIMIT 10;
            """
            query = sqlalchemy.text(base_query)

            available_appliances_rows = db_conn.execute(
                query, parameters=filter_values
            ).fetchall()

            available_appliances_list = []

            for row in available_appliances_rows:
                appliance_dict = dict(row._mapping)

                if "launch_date" in appliance_dict and isinstance(
                    appliance_dict["launch_date"], (date, datetime)
                ):
                    appliance_dict["launch_date"] = appliance_dict[
                        "launch_date"
                    ].strftime("%Y-%m-%d")

                available_appliances_list.append(appliance_dict)

            return {
                "status": "success",
                "available_appliances": available_appliances_list,
            }

    except Exception as error:
        return {
            "status": "error",
            "message": f"""Unable to retrieve available appliances {str(error)}
            If the issue seems to be with the `sub_category`, first use the 
            get_sub_categories_tool() and select the most appropriate 
            sub_category, and pass it back to get_filtered_appliances_tool() to 
            get the desired list of appliances.
            """,
        }

def get_appliance_specifications_tool(model_number: str,) -> Dict[str, Any]:
    """
    Retrieves the detailed appliance specifications for a given appliance model 
    number from Firestore.

    This tool connects to Firestore database to fetch technical specifications 
    and features associated with a specific appliance model.

    Args:
        model_number (str): Unique identifier for the appliance model.
                            (e.g., "NDG2335AW", "PDET920AY/M/B"). This tool
                            automatically handles '/' characters in the model
                            number by replacing them with underscores for
                            Firestore document ID compatibility.

    Returns:
        Dict[str, Any]: Dictionary containing the status of the operation and 
                        either the appliance specifications or an error message
                        
                        The dictionary can have the following structure:
                        - If successful:
                            {
                                "status": "success",
                                "appliance_specifications": {
                                    "key1": "value1",
                                    "key2": "value2",
                                    ...
                                }
                            }
                            where "appliance_specifications" is a dictionary
                            containing the retrieved data.

                        - If appliance specifications not found for this model:
                            {
                                "status": "error",
                                "appliance_specifications": "Appliance 
                                specifications are unavailable for this model"
                            }

                        - If an internal error occurs:
                            {
                                "status": "error",
                                "message": "Details about the error, e.g., 
                                'Permission denied'"
                            }
    """
    try:
        firestore_client = _initialize_firebase_firestore()

        doc = (
            firestore_client.collection("appliance_specifications")
            .document(model_number.replace('/', '_'))
            .get()
        )

        if doc.exists:
            return {
                "status": "success",
                "appliance_specifications": doc.to_dict()
            }

        else:
            message = "Appliance specifications are unavailable for this model"

            return {
                "status": "error",
                "appliance_specifications": message,
            }

    except Exception as error:
        return {
            "status": "error",
            "message": str(error),
        }
