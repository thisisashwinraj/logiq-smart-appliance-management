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
import requests
import sqlalchemy
import streamlit as st
from typing import Any, Dict, List

from google.cloud.sql.connector import Connector
from google.oauth2.service_account import Credentials


def add_skills(engineer_id: str, new_skills: List[str]) -> Dict[str, Any]:
    """
    Tool to add new skills to ann engineer's profile.

    This tool allows adding new skills to a service engineer's profile. It
    validates the provided skills against a predefined list of available skills 
    and updates the engineer's record in the database accordingly. Any invalid 
    or unrecognized skills are excluded from the update and returned for 
    reference.

    Args:
        engineer_id (str): Unique identifier of the engineer whose skills 
            need to be updated
        new_skills (list): List of new skills to add to the engineer's profile

    Returns:
        dict: A dictionary containing:
            - status (str): Indicates the operation result 
                - "success", "not_found", or "error".
            - message (str): Success message or a brief description of the error

            On success:
            A dictionary containing:
                - added_skills (list): List of updated skills for the engineer
                - invalid_skills (list): List of skills that were not recognized 
                  and hence not added.

    >>> Example:
        {
            "status": "success",
            "message": "Skills updated for engineer ID ENG123.",
            "added_skills": ["Installation", "Calibration"],
            "invalid_skills (not added)": ["Cooking Assistance"]
        }
    """
    try:
        available_skills = [
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

        skills = [skill for skill in new_skills if skill in available_skills]

        invalid_skills = [
            skill for skill in new_skills if skill not in available_skills
        ]

        credentials = Credentials.from_service_account_info(
            json.loads(st.secrets["CLOUD_SQL_SERVICE_ACCOUNT_KEY"])
        )

        connector = Connector(credentials=credentials)

        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=lambda: connector.connect(
                st.secrets["CLOUD_SQL_MYSQL_INSTANCE_CONNECTION_STRING"],
                st.secrets["CLOUD_SQL_MYSQL_DRIVER"],
                user=st.secrets["CLOUD_SQL_MYSQL_USER"],
                password=st.secrets["CLOUD_SQL_PASSWORD"],
                db=st.secrets["CLOUD_SQL_MYSQL_DB"],
            ),
        )

        with pool.connect() as conn:
            existing_skills_query = sqlalchemy.text("""
                SELECT skills 
                FROM engineers 
                WHERE engineer_id = :engineer_id
            """)

            result = conn.execute(
                existing_skills_query, 
                {"engineer_id": engineer_id}
            ).fetchone()

            existing_skills = json.loads(result[0]) if result and result[0] else []
            updated_skills = list(set(existing_skills + skills))

            update_query = sqlalchemy.text(
                """
                UPDATE engineers
                SET skills = CAST(:skills AS JSON)
                WHERE engineer_id = :engineer_id
                """
            )

            conn.execute(
                update_query, 
                {
                    "skills": json.dumps(updated_skills),
                    "engineer_id": engineer_id
                }
            )

            conn.commit()
            
            return {
                "status": "success",
                "message": f"Skills updated for engineer ID {engineer_id}.",
                "added_skills": skills or None,
                "invalid_skills (not added)": invalid_skills or None
            }

    except Exception as error:
        return {
            "status": "error",
            "message": f"An error occurred while updating skills:\n{str(error)}."
        }


def remove_skills(engineer_id: str, skills_to_remove: List[str]) -> Dict[str, Any]:
    """
    Tool to remove specific skills from an engineer's skill set in the database.

    This tool allows deleting one or more existing skills from an engineer's 
    profile. It retrieves the current list of skills from the database, removes 
    only those specified in the input (if present), and updates the record with 
    the modified skill list.

    If a skill provided for removal does not exist in the engineer's current 
    skill set, it will be reported as an invalid removal request.

    Args:
        engineer_id (str): Unique identifier of the engineer whose skills 
            need to be modified.
        skills_to_remove (list): List of skills to remove from the engineer's 
            profile.

    Returns:
        A dictionary containing:
            - status (str): Indicates the operation result 
                - "success", "not_found", or "error".
            - message (str): Success message or a brief description of the error

            On success:
                - removed_skills (list): List of updated skills for the engineer
                - invalid_skills (list): List of skills that were not found and 
                  hence not removed.

        >>> Example:
            {
                "status": "success",
                "message": "Skills removed for engineer ID ENG123.",
                "removed_skills": ["Installation"],
                "invalid_skills (not found)": ["Cooking Assistance"]
            }

    Raises:
        Exception: If a database connection or query execution error occurs.
    """
    try:
        credentials = Credentials.from_service_account_info(
            json.loads(st.secrets["CLOUD_SQL_SERVICE_ACCOUNT_KEY"])
        )

        connector = Connector(credentials=credentials)

        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=lambda: connector.connect(
                st.secrets["CLOUD_SQL_MYSQL_INSTANCE_CONNECTION_STRING"],
                st.secrets["CLOUD_SQL_MYSQL_DRIVER"],
                user=st.secrets["CLOUD_SQL_MYSQL_USER"],
                password=st.secrets["CLOUD_SQL_PASSWORD"],
                db=st.secrets["CLOUD_SQL_MYSQL_DB"],
            ),
        )

        with pool.connect() as conn:
            fetch_query = sqlalchemy.text("""
                SELECT skills 
                FROM engineers 
                WHERE engineer_id = :engineer_id
            """)

            result = conn.execute(fetch_query, {"engineer_id": engineer_id}).fetchone()

            if not result or not result[0]:
                return {
                    "status": "error",
                    "message": f"No skills found for engineer ID {engineer_id}."
                }

            current_skills = json.loads(result[0])
            removed_skills = [s for s in skills_to_remove if s in current_skills]
            invalid_skills = [s for s in skills_to_remove if s not in current_skills]

            updated_skills = [s for s in current_skills if s not in removed_skills]

            update_query = sqlalchemy.text("""
                UPDATE engineers
                SET skills = CAST(:skills AS JSON)
                WHERE engineer_id = :engineer_id
            """)

            conn.execute(
                update_query,
                {
                    "skills": json.dumps(updated_skills),
                    "engineer_id": engineer_id
                }
            )

            conn.commit()

            return {
                "status": "success",
                "message": f"Skills removed for engineer ID {engineer_id}.",
                "removed_skills": removed_skills or None,
                "invalid_skills (not found)": invalid_skills or None
            }

    except Exception as error:
        return {
            "status": "error",
            "message": f"An error occurred while removing skills:\n{str(error)}."
        }


def add_specializations(
    engineer_id: str, 
    new_specializations: List[str]
) -> Dict[str, Any]:
    """
    Tool to add new specializations to an engineer's profile.

    This tool allows adding new specializations to a service engineer's profile. 
    It validates the provided specializations against a predefined list of 
    supported specializations and updates the engineer's record in the database 
    accordingly. Any invalid or unrecognized specializations are excluded from 
    the update and returned for reference.

    Args:
        engineer_id (str): Unique identifier of the engineer whose 
            specializations need to be updated.
        new_specializations (list): List of new specializations to add 
            to the engineer's profile. (These are appliance sub-categories)
            - Valid options are: "Freestanding Double Oven Gas Range", 
              "Freestanding Gas Range", "Countertop Commercial Microwave Oven", 
              "Countertop Domestic Microwave Oven", "Bottom Mount Refrigerator", 
              "Side-by-Side Refrigerator", "Top Load Washer", "Compact Washer", 
              "Compact Dryer", and "Electric/Gas Dryer".
            - e.g., ["Compact Dryer", "Freestanding Gas Range"]

    Returns:
        dict: A dictionary containing:
            - status (str): Indicates the operation result 
                ("success", "not_found", or "error").
            - message (str): Success message or a brief description of the error.

            On success:
            A dictionary containing:
                - added_specializations (list): List of updated specializations 
                  for the engineer.
                - invalid_specializations (list): List of specializations that 
                  were not recognized and hence not added.

    >>> Example:
        {
            "status": "success",
            "message": "Specializations updated for engineer ID ENG123.",
            "added_specializations": ["Refrigerator", "Washing Machine"],
            "invalid_specializations (not added)": ["Solar Inverter"]
        }
    """
    try:
        credentials = Credentials.from_service_account_info(
            json.loads(st.secrets["CLOUD_SQL_SERVICE_ACCOUNT_KEY"])
        )

        connector = Connector(credentials=credentials)

        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=lambda: connector.connect(
                st.secrets["CLOUD_SQL_MYSQL_INSTANCE_CONNECTION_STRING"],
                st.secrets["CLOUD_SQL_MYSQL_DRIVER"],
                user=st.secrets["CLOUD_SQL_MYSQL_USER"],
                password=st.secrets["CLOUD_SQL_PASSWORD"],
                db=st.secrets["CLOUD_SQL_MYSQL_DB"],
            ),
        )

        with pool.connect() as conn:
            query = sqlalchemy.text(
                """
                SELECT DISTINCT sub_category, brand, model_number
                FROM appliances;
                """
            )

            cursor = conn.execute(query).fetchall()

            specializations = {}

            for sub_category, brand, model_number in cursor:
                if sub_category not in specializations:
                    specializations[sub_category] = {}

                if brand not in specializations[sub_category]:
                    specializations[sub_category][brand] = []

                specializations[sub_category][brand].append(model_number)

            available_specializations = specializations.keys()
            
            valid_specializations = [
                s for s in new_specializations if s in available_specializations
            ]
            invalid_specializations = [
                s for s in new_specializations if s not in available_specializations
            ]

            existing_specializations_query = sqlalchemy.text(
                """
                SELECT specializations 
                FROM engineers 
                WHERE engineer_id = :engineer_id
                """
            )

            result = conn.execute(
                existing_specializations_query, 
                {"engineer_id": engineer_id}
            ).fetchone()

            existing_specializations = (
                json.loads(result[0]) if result and result[0] else []
            )

            updated_specializations = list(
                set(existing_specializations + valid_specializations)
            )

            update_query = sqlalchemy.text(
                """
                UPDATE engineers
                SET specializations = CAST(:specializations AS JSON)
                WHERE engineer_id = :engineer_id
                """
            )

            conn.execute(
                update_query, 
                {
                    "specializations": json.dumps(updated_specializations),
                    "engineer_id": engineer_id
                }
            )

            conn.commit()

            return {
                "status": "success",
                "message": f"Specializations added for engineer ID {engineer_id}.",
                "added_specializations": valid_specializations or None,
                "invalid_specializations (not added)": invalid_specializations or None
            }

    except Exception as error:
        return {
            "status": "error",
            "message": f"An error occurred while updating specializations:\n{str(error)}."
        }


def remove_specializations(engineer_id: str, specializations_to_remove: List[str]) -> Dict[str, Any]:
    """
    Tool to remove existing specializations from an engineer's profile.

    This tool removes one or more existing specializations from a service 
    engineer's profile. The provided specializations are matched against the 
    engineer's current specializations stored in the database, and any matches 
    are removed from their profile.

    Args:
        engineer_id (str): Unique identifier of the engineer whose 
            specializations need to be removed.
        specializations_to_remove (list): List of specializations to remove 
            from the engineer's profile.

    Returns:
        dict: A dictionary containing:
            - status (str): Indicates the operation result 
                ("success", "not_found", or "error").
            - message (str): Success message or a brief description of the error.

            On success:
            A dictionary containing:
                - removed_specializations (list): List of successfully removed 
                  specializations.
                - not_found_specializations (list): List of provided 
                  specializations that were not present in the engineer's profile.

    >>> Example:
        {
            "status": "success",
            "message": "Specializations removed for engineer ID ENG123.",
            "removed_specializations": ["Washing Machine", "Microwave Oven"],
            "not_found_specializations": ["Refrigerator"]
        }
    """
    try:
        credentials = Credentials.from_service_account_info(
            json.loads(st.secrets["CLOUD_SQL_SERVICE_ACCOUNT_KEY"])
        )

        connector = Connector(credentials=credentials)

        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=lambda: connector.connect(
                st.secrets["CLOUD_SQL_MYSQL_INSTANCE_CONNECTION_STRING"],
                st.secrets["CLOUD_SQL_MYSQL_DRIVER"],
                user=st.secrets["CLOUD_SQL_MYSQL_USER"],
                password=st.secrets["CLOUD_SQL_PASSWORD"],
                db=st.secrets["CLOUD_SQL_MYSQL_DB"],
            ),
        )

        with pool.connect() as conn:
            existing_specializations_query = sqlalchemy.text(
                """
                SELECT specializations 
                FROM engineers 
                WHERE engineer_id = :engineer_id
                """
            )

            result = conn.execute(
                existing_specializations_query, 
                {"engineer_id": engineer_id}
            ).fetchone()

            if not result:
                return {
                    "status": "not_found",
                    "message": f"No specializations found for engineer: {engineer_id}."
                }

            existing_specializations = json.loads(result[0]) if result and result[0] else []

            removed_specializations = [
                s for s in specializations_to_remove if s in existing_specializations
            ]
            not_found_specializations = [
                s for s in specializations_to_remove if s not in existing_specializations
            ]

            updated_specializations = [
                s for s in existing_specializations if s not in removed_specializations
            ]

            update_query = sqlalchemy.text("""
                UPDATE engineers
                SET specializations = CAST(:specializations AS JSON)
                WHERE engineer_id = :engineer_id
            """)

            conn.execute(
                update_query,
                {
                    "specializations": json.dumps(updated_specializations),
                    "engineer_id": engineer_id
                }
            )

            conn.commit()

            return {
                "status": "success",
                "message": f"Specializations removed for engineer ID {engineer_id}.",
                "removed_specializations": removed_specializations or None,
                "not_found_specializations": not_found_specializations or None
            }

    except Exception as error:
        return {
            "status": "error",
            "message": f"An error occurred while removing specializations:\n{str(error)}."
        }


def get_district_from_zip(zipcode: str) -> str:
    try:
        url = f"https://api.postalpincode.in/pincode/{zipcode}"
        response = requests.get(url, timeout=5)

        data = response.json()[0]
        post_offices = data.get("PostOffice")
        
        if post_offices and isinstance(post_offices, list):
            return post_offices[0].get("District", "")
        
        return None
    
    except Exception as error:
        return None
    

def update_address(
    engineer_id: str,
    street: str,
    city: str,
    district: str,
    state: str,
    zipcode: str,
    country: str
):
    """
    Tool to update the address details of a service engineer in the database.

    This tool updates an engineer's address information, including street, city, 
    district, state, zip code, and country. It automatically attempts to validate 
    or correct the district name using the provided postal (PIN) code by calling 
    an external postal API via the helper function `get_district_from_zip`. If the 
    API successfully returns a district, it overrides the input district before 
    updating the database record.

    Args:
        engineer_id (str): Id of the engineer whose address needs to be updated.
        street (str): Street name or house address.
        city (str): City name.
        district (str): District name (will be auto-corrected using zipcode).
        state (str): State name.
        zipcode (str): Postal or ZIP code of the address.
        country (str): Country name.

    Returns:
        dict: A dictionary containing:
            - status (str): Indicates the operation result 
                ("success", "not_found", or "error").
            - message (str): Success message or a brief description of the error.

            On success:
            - new_address (str, optional): The updated address in a formatted 
              string if the operation succeeds.

    >>> Example:
        {
            "status": "success",
            "message": "Address updated for engineer ID ENG123.",
            "new_address": "MG Road, Majestic, Bengaluru, Karnataka-560001, India"
        }
    """
    try:
        corrected_district = get_district_from_zip(zipcode)

        if corrected_district:
            district = corrected_district

        credentials = Credentials.from_service_account_info(
            json.loads(st.secrets["CLOUD_SQL_SERVICE_ACCOUNT_KEY"])
        )

        connector = Connector(credentials=credentials)

        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=lambda: connector.connect(
                st.secrets["CLOUD_SQL_MYSQL_INSTANCE_CONNECTION_STRING"],
                st.secrets["CLOUD_SQL_MYSQL_DRIVER"],
                user=st.secrets["CLOUD_SQL_MYSQL_USER"],
                password=st.secrets["CLOUD_SQL_PASSWORD"],
                db=st.secrets["CLOUD_SQL_MYSQL_DB"],
            ),
        )

        with pool.connect() as conn:
            update_query = sqlalchemy.text("""
                UPDATE engineers
                SET street = :street,
                    city = :city,
                    district = :district,
                    state = :state,
                    zip_code = :zip_code,
                    country = :country
                WHERE engineer_id = :engineer_id
            """)

            conn.execute(
                update_query,
                {
                    "street": street,
                    "city": city,
                    "district": district,
                    "state": state,
                    "zip_code": zipcode,
                    "country": country,
                    "engineer_id": engineer_id
                }
            )

            conn.commit()

            return {
                "status": "success",
                "message": f"Address updated for engineer ID {engineer_id}.",
                "new_address": f"{street}, {city}, {district}, {state}-{zipcode}, {country}"
            }

    except Exception as error:
        return {
            "status": "error",
            "message": f"An error occurred while updating address:\n{str(error)}."
        }
