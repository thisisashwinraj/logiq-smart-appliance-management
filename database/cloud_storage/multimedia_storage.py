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
import warnings

import streamlit as st
from dotenv import load_dotenv
from datetime import datetime, timedelta

from google.cloud import storage
from google.oauth2.service_account import Credentials

load_dotenv()
warnings.filterwarnings("ignore")


class AppliancesBucket:
    def __init__(self):
        credentials = Credentials.from_service_account_info(
            json.loads(st.secrets["CLOUD_STORAGE_SERVICE_ACCOUNT_KEY"])
        )

        self.storage_client = storage.Client(credentials=credentials)

    def upload_appliance_image(self, brand, sub_category, local_image_path):
        bucket = self.storage_client.bucket("appliance_catalogue_bucket")

        blob = bucket.blob(
            f"appliance_images/{
                brand.replace(
                    '-',
                    '_').replace(
                    ' ',
                    '_').lower()}_{
                sub_category.replace(
                    '-',
                    '_').replace(
                    ' ',
                    '_').lower()}.jpg"
        )
        blob.upload_from_filename(local_image_path)

        return True

    def download_appliance_image(
        self, brand, sub_category, downloaded_file_path,
    ):
        bucket = self.storage_client.bucket("appliance_catalogue_bucket")

        blob = bucket.blob(
            f"appliance_images/{
                brand.replace(
                    '-',
                    '_').replace(
                    ' ',
                    '_').lower()}_{
                sub_category.replace(
                    '-',
                    '_').replace(
                    ' ',
                    '_').lower()}.jpg"
        )
        blob.download_to_filename(downloaded_file_path)

        return downloaded_file_path

    def fetch_appliance_image_url(
        self, brand, sub_category, expire_in=datetime.today() + timedelta(3)
    ):
        bucket = self.storage_client.bucket("appliance_catalogue_bucket")

        image_url = bucket.blob(
            f"appliance_images/{
                brand.replace(
                    '-',
                    '_').replace(
                    ' ',
                    '_').lower()}_{
                sub_category.replace(
                    '-',
                    '_').replace(
                    ' ',
                    '_').lower()}.jpg"
        ).generate_signed_url(expire_in)
        return image_url


class InventoryItems:
    def __init__(self):
        credentials = Credentials.from_service_account_info(
            json.loads(st.secrets["CLOUD_STORAGE_SERVICE_ACCOUNT_KEY"])
        )

        self.storage_client = storage.Client(credentials=credentials)

    def upload_item_image(self, local_file_path, cloud_storage_path):
        bucket = self.storage_client.bucket("inventory_items_bucket")

        blob = bucket.blob(cloud_storage_path)
        blob.upload_from_filename(local_file_path)

        return cloud_storage_path

    def download_item_image(self, cloud_storage_path, local_file_path):
        bucket = self.storage_client.bucket("inventory_items_bucket")

        blob = bucket.blob(cloud_storage_path)
        blob.download_to_filename(local_file_path)

        return local_file_path

    def fetch_appliance_image_url(
        self, file_name, expire_in=datetime.today() + timedelta(3)
    ):
        bucket = self.storage_client.bucket("inventory_items_bucket")
        image_url = bucket.blob(file_name).generate_signed_url(expire_in)

        return image_url


class ProfilePicturesBucket:
    def __init__(self):
        credentials = Credentials.from_service_account_info(
            json.loads(st.secrets["CLOUD_STORAGE_SERVICE_ACCOUNT_KEY"])
        )

        self.storage_client = storage.Client(credentials=credentials)

    def upload_profile_picture(self, user_type, user_id, file):
        try:
            bucket = self.storage_client.bucket("profile_pictures_bucket")

            blob = bucket.blob(
                f"{user_type}/{
                    user_id.replace(
                        '/',
                        '_').replace(
                        '-',
                        '_').replace(
                        ' ',
                        '_').lower()}.png"
            )
            blob.upload_from_file(file)

            return True

        except Exception as error:
            return False

    def fetch_profile_picture_url(
        self, 
        user_type, 
        user_id, 
        expire_in=datetime.today() + timedelta(minutes=5),
    ):
        bucket = self.storage_client.bucket("profile_pictures_bucket")

        blob = bucket.blob(
            f"{user_type}/{
                user_id.replace(
                    '/',
                    '_').replace(
                    '-',
                    '_').replace(
                    ' ',
                    '_').lower()}.png"
        )

        blob.reload()
        updated_time = str(int(blob.updated.timestamp()))

        return blob.generate_signed_url(expire_in) + f"&updated={updated_time}"


class OnsiteServiceRequestsBucket:
    def __init__(self):
        credentials = Credentials.from_service_account_info(
            json.loads(st.secrets["CLOUD_STORAGE_SERVICE_ACCOUNT_KEY"])
        )

        self.storage_client = storage.Client(credentials=credentials)

    def upload_customer_attachment(
        self, request_id, image_file, image_filename,
    ):
        bucket = self.storage_client.bucket("onsite_service_requests_bucket")

        blob = bucket.blob(
            f"{request_id}/customer_attachments/{
                image_filename.replace(
                    '/',
                    '_').replace(
                    '-',
                    '_').replace(
                    ' ',
                    '_').lower()}"
        )
        blob.upload_from_file(image_file)

        return True
