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


class CustomerRecordsBucket:
    def __init__(self):
        credentials = Credentials.from_service_account_info(
            json.loads(st.secrets["CLOUD_STORAGE_SERVICE_ACCOUNT_KEY"])
        )

        self.storage_client = storage.Client(credentials=credentials)

    def upload_purchase_invoice(
        self, customer_id, serial_number, sub_category, file,
    ):
        bucket = self.storage_client.bucket("customer_records_bucket")

        blob = bucket.blob(
            f"purchase_invoices/{
                customer_id.replace(
                    '/',
                    '_').replace(
                    '-',
                    '_').replace(
                    ' ',
                    '_').lower()}_{
                        serial_number.replace(
                            '/',
                            '_').replace(
                                '-',
                                '_').replace(
                                    ' ',
                                    '_').lower()}_{
                                        sub_category.replace(
                                            '/',
                                            '_').replace(
                                                '-',
                                                '_').replace(
                                                    ' ',
                                            '_').lower()}_purchase_invoice.pdf"
        )
        blob.upload_from_file(file)

        return True

    def download_purchase_invoice(
        self, customer_id, serial_number, sub_category, downloaded_file_path,
    ):
        bucket = self.storage_client.bucket("customer_records_bucket")

        blob = bucket.blob(
            f"purchase_invoices/{
                customer_id.replace(
                    '/',
                    '_').replace(
                    '-',
                    '_').replace(
                    ' ',
                    '_').lower()}_{
                        serial_number.replace(
                            '/',
                            '_').replace(
                                '-',
                                '_').replace(
                                    ' ',
                                    '_').lower()}_{
                                        sub_category.replace(
                                            '/',
                                            '_').replace(
                                                '-',
                                                '_').replace(
                                                    ' ',
                                            '_').lower()}_purchase_invoice.pdf"
        )

        blob.download_to_filename(downloaded_file_path)
        return downloaded_file_path

    def fetch_product_invoice_url(
        self,
        customer_id,
        serial_number,
        sub_category,
        expire_in=datetime.today() + timedelta(3),
    ):
        bucket = self.storage_client.bucket("customer_records_bucket")

        image_url = bucket.blob(
            f"purchase_invoices/{
                customer_id.replace(
                    '/',
                    '_').replace(
                    '-',
                    '_').replace(
                    ' ',
                    '_').lower()}_{
                        serial_number.replace(
                            '/',
                            '_').replace(
                                '-',
                                '_').replace(
                                    ' ',
                                    '_').lower()}_{
                                        sub_category.replace(
                                            '/',
                                            '_').replace(
                                                '-',
                                                '_').replace(
                                                    ' ',
                                            '_').lower()}_purchase_invoice.pdf"
        ).generate_signed_url(expire_in)
        return image_url

    def upload_warranty_certificate(
        self, customer_id, serial_number, sub_category, file,
    ):
        bucket = self.storage_client.bucket("customer_records_bucket")

        blob = bucket.blob(
            f"warranty_certificates/{
                customer_id.replace(
                    '/',
                    '_').replace(
                    '-',
                    '_').replace(
                    ' ',
                    '_').lower()}_{
                        serial_number.replace(
                            '/',
                            '_').replace(
                                '-',
                                '_').replace(
                                    ' ',
                                    '_').lower()}_{
                                        sub_category.replace(
                                            '/',
                                            '_').replace(
                                                '-',
                                                '_').replace(
                                                    ' ',
                                            '_').lower()
                                            }_warranty_certificate.pdf"
        )
        blob.upload_from_file(file)

        return True

    def download_warranty_certificate(
        self, customer_id, serial_number, sub_category, downloaded_file_path,
    ):
        bucket = self.storage_client.bucket("customer_records_bucket")

        blob = bucket.blob(
            f"warranty_certificates/{
                customer_id.replace(
                    '/',
                    '_').replace(
                    '-',
                    '_').replace(
                    ' ',
                    '_').lower()}_{
                        serial_number.replace(
                            '/',
                            '_').replace(
                                '-',
                                '_').replace(
                                    ' ',
                                    '_').lower()}_{
                                        sub_category.replace(
                                            '/',
                                            '_').replace(
                                                '-',
                                                '_').replace(
                                                    ' ',
                                            '_').lower()
                                            }_warranty_certificate.pdf"
        )
        blob.download_to_filename(downloaded_file_path)

        return downloaded_file_path

    def fetch_warranty_certificate_url(
        self,
        customer_id,
        serial_number,
        sub_category,
        expire_in=datetime.today() + timedelta(3),
    ):
        bucket = self.storage_client.bucket("customer_records_bucket")

        image_url = bucket.blob(
            f"warranty_certificates/{
                customer_id.replace(
                    '/',
                    '_').replace(
                    '-',
                    '_').replace(
                    ' ',
                    '_').lower()}_{
                        serial_number.replace(
                            '/',
                            '_').replace(
                                '-',
                                '_').replace(
                                    ' ',
                                    '_').lower()}_{
                                        sub_category.replace(
                                            '/',
                                            '_').replace(
                                                '-',
                                                '_').replace(
                                                    ' ',
                                            '_').lower()
                                            }_warranty_certificate.pdf"
        ).generate_signed_url(expire_in)
        return image_url


class ServiceManualBucket:
    def __init__(self):
        credentials = Credentials.from_service_account_info(
            json.loads(st.secrets["CLOUD_STORAGE_SERVICE_ACCOUNT_KEY"])
        )

        self.storage_client = storage.Client(credentials=credentials)

    def upload_service_manual(self, local_file_path, cloud_storage_path):
        bucket = self.storage_client.bucket("service_manual_bucket")

        blob = bucket.blob(cloud_storage_path)
        blob.upload_from_filename(local_file_path)

        return cloud_storage_path

    def download_service_manual(self, cloud_storage_path, local_file_path):
        bucket = self.storage_client.bucket("service_manual_bucket")

        blob = bucket.blob(cloud_storage_path)
        blob.download_to_filename(local_file_path)

        return local_file_path

    def fetch_service_manual_url(
        self, file_name, expire_in=datetime.today() + timedelta(3)
    ):
        bucket = self.storage_client.bucket("service_manual_bucket")

        service_manual_url = bucket.blob(
            file_name).generate_signed_url(expire_in)

        return service_manual_url
