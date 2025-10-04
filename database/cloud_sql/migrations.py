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
import logging
import warnings
import sqlalchemy

import streamlit as st
from dotenv import load_dotenv

from google.cloud.sql.connector import Connector
from google.oauth2.service_account import Credentials

load_dotenv()
logger = logging.getLogger(__name__).setLevel(logging.ERROR)
warnings.filterwarnings("ignore")


class MigrateAppliances:
    def __init__(self):
        credentials = Credentials.from_service_account_info(
            json.loads(st.secrets["CLOUD_SQL_SERVICE_ACCOUNT_KEY"])
        )

        self.connector = Connector(credentials=credentials)

    def _get_connection(self):
        conn = self.connector.connect(
            st.secrets["CLOUD_SQL_MYSQL_INSTANCE_CONNECTION_STRING"],
            st.secrets["CLOUD_SQL_MYSQL_DRIVER"],
            user=st.secrets["CLOUD_SQL_MYSQL_USER"],
            password=st.secrets["CLOUD_SQL_PASSWORD"],
            db=st.secrets["CLOUD_SQL_MYSQL_DB"],
        )
        return conn

    def update_appliance(self, model_number, **kwargs):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            update_query = "UPDATE appliances SET "
            update_values = {}

            for key, value in kwargs.items():
                update_query += f"{key} = :{key}, "
                update_values[key] = value

            update_query = update_query[:-2]

            update_query += " WHERE model_number = :model_number;"
            update_values["model_number"] = model_number

            query = sqlalchemy.text(update_query)
            db_conn.execute(query, parameters=update_values)
            db_conn.commit()

    def delete_appliance(self, model_number):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                DELETE FROM appliances
                WHERE model_number = :model_number
                """
            )
            db_conn.execute(query, parameters={"model_number": model_number})

            db_conn.commit()


class MigrateCustomers:
    def __init__(self):
        credentials = Credentials.from_service_account_info(
            json.loads(st.secrets["CLOUD_SQL_SERVICE_ACCOUNT_KEY"])
        )

        self.connector = Connector(credentials=credentials)

    def _get_connection(self):
        conn = self.connector.connect(
            st.secrets["CLOUD_SQL_MYSQL_INSTANCE_CONNECTION_STRING"],
            st.secrets["CLOUD_SQL_MYSQL_DRIVER"],
            user=st.secrets["CLOUD_SQL_MYSQL_USER"],
            password=st.secrets["CLOUD_SQL_PASSWORD"],
            db=st.secrets["CLOUD_SQL_MYSQL_DB"],
        )
        return conn

    def update_customer(self, username, **kwargs):
        try:
            pool = sqlalchemy.create_engine(
                "mysql+pymysql://",
                creator=self._get_connection,
            )

            with pool.connect() as db_conn:
                update_query = "UPDATE customers SET "
                update_values = {}

                for key, value in kwargs.items():
                    update_query += f"{key} = :{key}, "
                    update_values[key] = value

                update_query = update_query[:-2]

                update_query += " WHERE username = :username;"
                update_values["username"] = username

                query = sqlalchemy.text(update_query)
                db_conn.execute(query, parameters=update_values)
                db_conn.commit()

                return True

        except Exception as error:
            return False

    def delete_customer(self, username):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                DELETE FROM customers
                WHERE username = :username
                """
            )

            db_conn.execute(query, parameters={"username": username})

            db_conn.commit()


class MigrateEngineers:
    def __init__(self):
        credentials = Credentials.from_service_account_info(
            json.loads(st.secrets["CLOUD_SQL_SERVICE_ACCOUNT_KEY"])
        )

        self.connector = Connector(credentials=credentials)

    def _get_connection(self):
        conn = self.connector.connect(
            st.secrets["CLOUD_SQL_MYSQL_INSTANCE_CONNECTION_STRING"],
            st.secrets["CLOUD_SQL_MYSQL_DRIVER"],
            user=st.secrets["CLOUD_SQL_MYSQL_USER"],
            password=st.secrets["CLOUD_SQL_PASSWORD"],
            db=st.secrets["CLOUD_SQL_MYSQL_DB"],
        )
        return conn

    def update_engineer(self, engineer_id, **kwargs):
        try:
            pool = sqlalchemy.create_engine(
                "mysql+pymysql://",
                creator=self._get_connection,
            )

            with pool.connect() as db_conn:
                update_query = "UPDATE engineers SET "
                update_values = {}

                for key, value in kwargs.items():
                    update_query += f"{key} = :{key}, "
                    update_values[key] = value

                update_query = update_query[:-2]

                update_query += " WHERE engineer_id = :engineer_id;"
                update_values["engineer_id"] = engineer_id

                query = sqlalchemy.text(update_query)
                db_conn.execute(query, parameters=update_values)
                db_conn.commit()

                return True

        except Exception as error:
            return False

    def toggle_engineer_availability(self, engineer_id):
        try:
            pool = sqlalchemy.create_engine(
                "mysql+pymysql://",
                creator=self._get_connection,
            )

            with pool.connect() as db_conn:
                update_query = """
                    UPDATE engineers
                    SET availability = NOT availability
                    WHERE engineer_id = :engineer_id;
                """
                update_values = {"engineer_id": engineer_id}
                query = sqlalchemy.text(update_query)

                db_conn.execute(query, parameters=update_values)
                db_conn.commit()

                return True

        except Exception as error:
            return False

    def delete_engineer(self, engineer_id):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                DELETE FROM engineers
                WHERE engineer_id = :engineer_id
                """
            )

            db_conn.execute(query, parameters={"engineer_id": engineer_id})
            db_conn.commit()


class MigrateServiceGuides:
    def __init__(self):
        credentials = Credentials.from_service_account_info(
            json.loads(st.secrets["CLOUD_SQL_SERVICE_ACCOUNT_KEY"])
        )

        self.connector = Connector(credentials=credentials)

    def _get_connection(self):
        conn = self.connector.connect(
            st.secrets["CLOUD_SQL_MYSQL_INSTANCE_CONNECTION_STRING"],
            st.secrets["CLOUD_SQL_MYSQL_DRIVER"],
            user=st.secrets["CLOUD_SQL_MYSQL_USER"],
            password=st.secrets["CLOUD_SQL_PASSWORD"],
            db=st.secrets["CLOUD_SQL_MYSQL_DB"],
        )
        return conn

    def update_service_guide(self, guide_id, **kwargs):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            update_query = "UPDATE service_guides SET "
            update_values = {}

            for key, value in kwargs.items():
                update_query += f"{key} = :{key}, "
                update_values[key] = value

            update_query = update_query[:-2]

            update_query += " WHERE guide_id = :guide_id;"
            update_values["guide_id"] = guide_id

            query = sqlalchemy.text(update_query)
            db_conn.execute(query, parameters=update_values)
            db_conn.commit()

    def delete_service_guide(self, guide_id):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                DELETE FROM service_guides
                WHERE guide_id = :guide_id
                """
            )

            db_conn.execute(query, parameters={"guide_id": guide_id})
            db_conn.commit()


class MigrateCustomerAppliances:
    def __init__(self):
        credentials = Credentials.from_service_account_info(
            json.loads(st.secrets["CLOUD_SQL_SERVICE_ACCOUNT_KEY"])
        )

        self.connector = Connector(credentials=credentials)

    def _get_connection(self):
        conn = self.connector.connect(
            st.secrets["CLOUD_SQL_MYSQL_INSTANCE_CONNECTION_STRING"],
            st.secrets["CLOUD_SQL_MYSQL_DRIVER"],
            user=st.secrets["CLOUD_SQL_MYSQL_USER"],
            password=st.secrets["CLOUD_SQL_PASSWORD"],
            db=st.secrets["CLOUD_SQL_MYSQL_DB"],
        )
        return conn

    def update_customer_appliance_by_serial_number(
        self, 
        serial_number, 
        **kwargs
    ):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            update_query = "UPDATE customer_appliances SET "
            update_values = {}

            for key, value in kwargs.items():
                update_query += f"{key} = :{key}, "
                update_values[key] = value

            update_query = update_query[:-2]

            update_query += " WHERE serial_number = :serial_number;"
            update_values["serial_number"] = serial_number

            query = sqlalchemy.text(update_query)
            db_conn.execute(query, parameters=update_values)
            db_conn.commit()

    def delete_customer_appliance(self, serial_number):
        pool = sqlalchemy.create_engine(
            "mysql+pymysql://",
            creator=self._get_connection,
        )

        with pool.connect() as db_conn:
            query = sqlalchemy.text(
                """
                DELETE FROM customer_appliances
                WHERE serial_number = :serial_number
                """
            )

            db_conn.execute(query, parameters={"serial_number": serial_number})
            db_conn.commit()
