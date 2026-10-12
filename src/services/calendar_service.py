from __future__ import print_function
from datetime import datetime, timedelta

import os.path
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar"]


def get_calendar_service():
    creds = None

    # Check whether we already have valid credentials, authenticate with Google

    token_path = Path("token.json")

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(
            "token.json",
            SCOPES
        )

    # If we don't have valid credentials, authenticate with Google.

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run.
        token_path.write_text(creds.to_json())

    service = build(
        "calendar",
        "v3",
        credentials=creds
    )

    return service


def create_calendar_event(person: str, start_time: str):

    service = get_calendar_service()
    start_time = datetime.fromisoformat(
        start_time)

    end_time = start_time + timedelta(minutes=30)

    event = {
        "summary": f"Meeting with {person}",
        "description": "Created by Voice Scheduler",
        "start": {
            "dateTime": start_time.isoformat(),
            "timeZone": "America/Halifax",
        },
        "end": {
            "dateTime": end_time.isoformat(),
            "timeZone": "America/Halifax",
        },
        "reminders": {
            "useDefault": False,
            "overrides": [
                {
                    "method": "popup",
                    "minutes": 10,
                }
            ],
        },
    }

    created_event = service.events().insert(
        calendarId="primary",
        body=event
    ).execute()

    return created_event
