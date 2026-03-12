import os
import pickle
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def get_authenticated_service():
    creds = None

    # Load saved login token if exists
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    # If no valid creds → authenticate
    if not creds or not creds.valid:

        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())

        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json",
                SCOPES
            )

            # ✅ FIX: run_local_server handles redirect_uri automatically
            # It opens the browser, catches the callback, and exchanges the code
            creds = flow.run_local_server(port=0)

        # Save token for next runs
        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("youtube", "v3", credentials=creds)


def upload_to_youtube(video_path, title, description, tags):

    youtube = get_authenticated_service()

    body = {
        "snippet": {
            "title": title[:95],
            "description": description,
            "tags": tags[:15],
            "categoryId": "22"
        },
        "status": {
            "privacyStatus": "public"
        }
    }

    media = MediaFileUpload(
        video_path,
        chunksize=256 * 1024,
        resumable=True
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media
    )

    print("\n🚀 Uploading to YouTube...\n")

    response = None
    while response is None:
        status, response = request.next_chunk()

        if status:
            print(f"📤 Upload {int(status.progress() * 100)}%")

    print("\n✅ Upload Complete!")

    return response["id"]