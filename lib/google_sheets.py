"""
Shamelessly copied from Farmhouse
"""

import os.path

import json
from typing import List, Optional, Any, Dict, Tuple
from collections import namedtuple

from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


# The official google python client requires a file, not a set of variables. So
# take in the variables from environment variables and save it to a file
# https://developers.google.com/identity/protocols/oauth2/service-account#python
SERVICE_ACCOUNT_FILE = "/tmp/google-service-account.json"
SERVICE_ACCOUNT_FILE_CONTENT = {
    "type": "service_account",
    "project_id": os.environ['PROJECT_ID'],
    "private_key_id": os.environ['PRIVATE_KEY_ID'],
    "client_email": os.environ['CLIENT_EMAIL'],
    "client_id": os.environ['CLIENT_ID'],
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.environ['CLIENT_X509_CERT_URL'],
    "private_key": os.environ['PRIVATE_KEY'].replace("\\n", "\n"),
}
SHEET_ID = os.environ['SHEET_ID']
SHEET_READ_RANGE = "database!A3:G"
SHEET_OCCUPIED_RANGE = "database!E3:E"

PhoneboothSheetRow = namedtuple('PhoneboothSheetRow', 'name description location id occupied ip_address mac_address')


def _configure_service_account_file() -> service_account.Credentials:
    """
    Create the google service account file that the python client
    requires to interact with google services.
    """
    if os.path.exists(SERVICE_ACCOUNT_FILE):
        os.remove(SERVICE_ACCOUNT_FILE)

    with open(SERVICE_ACCOUNT_FILE, "w") as fh:
        json.dump(SERVICE_ACCOUNT_FILE_CONTENT, fh)
    return service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )


def _get_google_sheet_object() -> Optional[Any]:
    credentials = _configure_service_account_file()
    service = build("sheets", "v4", credentials=credentials)
    return service.spreadsheets()


def _write_google_sheet_rows(sheet_range: str, sheet_values: List[Tuple[Any]]) -> Dict:
    """
    Write a dataset to a sheet
    :param sheet_values: 2D array of values to populate the sheet with
    documentation: https://developers.google.com/sheets/api/reference/rest/v4/ValueInputOption
    :return: raw response from google about the result
    """
    sheet = _get_google_sheet_object()

    return (
        sheet.values()
        .update(
            spreadsheetId=SHEET_ID,
            range=sheet_range,
            valueInputOption="USER_ENTERED",
            body={"values": sheet_values},
        )
        .execute()
    )


def write_occupied_values(values: List[bool]) -> Dict:
    formatted_values = [(value,) for value in values]
    return _write_google_sheet_rows(SHEET_OCCUPIED_RANGE, formatted_values)


def read_google_sheet_rows() -> List[PhoneboothSheetRow]:
    sheet = _get_google_sheet_object()
    result = sheet.values().get(spreadsheetId=SHEET_ID, range=SHEET_READ_RANGE).execute()
    rows = result.get("values", [])
    return [PhoneboothSheetRow(*row) for row in rows]
