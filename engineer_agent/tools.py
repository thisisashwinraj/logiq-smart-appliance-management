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

import logging
import json
import sqlalchemy
import streamlit as st

from google.cloud.sql.connector import Connector
from google.oauth2.service_account import Credentials


def fetch_engineer_details_by_id(engineer_id: str):
    """
    Tool to retrieve complete profile details of a service engineer using their 
    ID.

    This tool gets the detailed information about a specific service engineer 
    from the engineers table in the Cloud SQL database. It returns a structured 
    dictionary containing personal details, address, skills, and other profile 
    related attributes.

    Args:
        engineer_id (str): Id of the engineer whose details are to be retrieved.

    Returns:
        On success:
        dict: A dictionary containing the engineer's full profile details:
            - engineer_id (str): Unique engineer identifier.
            - first_name (str): Engineer's first name.
            - last_name (str): Engineer's last name.
            - email (str): Registered email address.
            - phone_number (str): Engineer's contact number.
            - availability (str): Indicates if the engineer is available or not.
            - active_tickets (int): Count of currently active service tickets.
            - street (str): Street address of the engineer.
            - city (str): City of residence.
            - district (str): Administrative district.
            - state (str): State of residence.
            - country (str): Country name.
            - zip_code (str): Postal or ZIP code.
            - specializations (list): JSON containing an engineer's specialized 
                appliance categories or domains.
            - skills (list): JSON listing the engineer's technical competencies.
            - rating (float): Average performance rating of the engineer.
            - training_id (str): Associated training module identifier.
            - reward_points (int): Current reward points earned by the engineer.
            - profile_picture (str): URL to the engineer's profile image.
            - language_proficiency (list): JSON list of supported languages.
            - created_on (datetime): Timestamp when the profile was created.
        
        On failure:
            dict: A dictionary containing an 'error' key with the error message.

    Example:
        >>> fetch_engineer_details_by_id("ENGR123456")
        {
            "engineer_id": "ENGR123456",
            "first_name": "Rahul",
            "last_name": "Verma",
            "email": "rahul.verma@example.com",
            "phone_number": "+91-9876543210",
            "city": "Pune",
            "skills": ["Calibration", "Maintenance"],
            "specializations": ["Refrigerator", "Washing Machine"],
            ...
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

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                "SELECT * FROM engineers WHERE engineer_id = :engineer_id"
            )

            result = db_conn.execute(
                query, parameters={"engineer_id": engineer_id}
            ).fetchone()

            try:
                response = {
                    "engineer_id": result[0],
                    "first_name": result[1],
                    "last_name": result[2],
                    "email": result[3],
                    "phone_number": result[4],
                    "availability": result[5],
                    "active_tickets": result[6],
                    "street": result[7],
                    "city": result[8],
                    "district": result[9],
                    "state": result[10],
                    "country": result[11],
                    "zip_code": result[12],
                    "specializations": result[13],
                    "skills": result[14],
                    "rating": result[15],
                    "training_id": result[16],
                    "reward_points": result[17],
                    "profile_picture": result[18],
                    "language_proficiency": result[19],
                    "created_on": result[20],
                }

            except Exception as error:
                logging.error(f"Error parsing engineer details: {error}")

            return response
    
    except Exception as error:
        return {"error": str(error)}
