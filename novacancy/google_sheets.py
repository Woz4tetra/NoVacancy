"""
Shamelessly copied from Farmhouse
"""

import os.path

import json
from typing import List, Optional, Any, Dict, Tuple
from collections import namedtuple
import warnings

from google.oauth2 import service_account
from googleapiclient.discovery import build

from lib.recursive_namespace import RecursiveNamespace

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
DATABASE_SHEET_READ_RANGE = "database!A3:H"
GROUPS_SHEET_READ_RANGE = "groups!A2:Z"
DEVICES_SHEET_READ_RANGE = "devices!A2:D"
SHEET_OCCUPIED_RANGE = "database!F3:F"

PhoneboothSheetRow = namedtuple('PhoneboothSheetRow', 'name link description location id occupied ip_address mac_address')


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


def to_column_letter(column_int: int) -> str:
    # https://stackoverflow.com/questions/23861680/convert-spreadsheet-number-to-column-letter
    start_index = 1   #  it can start either at 0 or at 1
    letter = ''
    while column_int > 25 + start_index:   
        letter += chr(65 + int((column_int-start_index)/26) - 1)
        column_int = column_int - (int((column_int-start_index)/26))*26
    letter += chr(65 - start_index + (int(column_int)))
    return letter



def read_database() -> List[PhoneboothSheetRow]:
    sheet = _get_google_sheet_object()
    result = sheet.values().get(spreadsheetId=SHEET_ID, range=DATABASE_SHEET_READ_RANGE).execute()
    if "values" in result:
        rows = result["values"]
        return [PhoneboothSheetRow(*row) for row in rows]
    else:
        return []


def read_groups_config() -> RecursiveNamespace:
    sheet = _get_google_sheet_object()
    result = sheet.values().get(spreadsheetId=SHEET_ID, range=GROUPS_SHEET_READ_RANGE).execute()
    if "values" in result:
        rows = result["values"]
        ns = RecursiveNamespace()
        for row in rows:
            try:
                name = str(row[0])
                bigsign_device = str(row[1])
                vacancy_devices = list(map(str, row[2:]))
            except BaseException as e:
                warnings.warn("Failed to read groups config: %s" % str(e))
                return RecursiveNamespace()

            ns[name] = RecursiveNamespace(bigsign=bigsign_device, devices=vacancy_devices)
        return ns
    else:
        return RecursiveNamespace()


def read_devices_config() -> RecursiveNamespace:
    sheet = _get_google_sheet_object()
    result = sheet.values().get(spreadsheetId=SHEET_ID, range=DEVICES_SHEET_READ_RANGE).execute()
    if "values" in result:
        rows = result["values"]
        ns = RecursiveNamespace(weights={}, weight_directions={}, distances={})
        for row in rows:
            try:
                board_id = str(row[0])
                weight_threshold = int(row[1])
                weight_threshold_direction = row[2].lower() == "true"
                distance_threshold = float(row[3])
            except BaseException as e:
                warnings.warn("Failed to read devices config: %s" % str(e))
                return RecursiveNamespace()
            ns.weights[board_id] = weight_threshold
            ns.weight_directions[board_id] = weight_threshold_direction
            ns.distances[board_id] = distance_threshold

        return ns
    else:
        return RecursiveNamespace()
