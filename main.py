from concurrent.futures import ThreadPoolExecutor
import os
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import requests


# Google Photos Library API 권한 정의
SCOPES = ["https://www.googleapis.com/auth/photoslibrary.readonly"]
CLIENT_SECRET_FILE = "token.json"
credFile = f"token_photo_sync_user.json"


def download_file(url: str, destination_folder: str, file_name: str):
    response = requests.get(url)
    if response.status_code == 200:
        file = os.path.join(destination_folder, file_name)
        if os.path.exists(file):
            print(f"Already exist file {file_name}")
            return

        print("Downloading file {0}".format(file_name))

        with open(os.path.join(destination_folder, file_name), "wb") as f:
            f.write(response.content)


if __name__ == "__main__":
    creds = None
    if os.path.exists(credFile):
        creds = Credentials.from_authorized_user_file(credFile, SCOPES)

    # 유효한 credential이 없다면 login하도록 한다.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        # 성공하면 기록하도록 한다.
        with open(credFile, "w") as token:
            token.write(creds.to_json())

    # 구글 포토 API 사용
    service = build("photoslibrary", "v1", credentials=creds, static_discovery=False)

    # 즐겨찾기한 사진 가져오기
    body = {
        "pageSize": 100,
        "filters": {
            "featureFilter": {"includedFeatures": ["FAVORITES"]},
            "mediaTypeFilter": {"mediaTypes": ["PHOTO"]},
        },
    }
    with ThreadPoolExecutor(max_workers=50) as executor:
        response = service.mediaItems().search(body=body).execute()
        while response and (media_items := response.get("mediaItems")):
            for item in media_items:
                download_url = item["baseUrl"] + "=d"
                width = item["mediaMetadata"]["width"]
                height = item["mediaMetadata"]["height"]

                if width > height:
                    destination_folder = "/Users/hanson/Pictures/wallpaper/horizontal"
                else:
                    destination_folder = "/Users/hanson/Pictures/wallpaper/vertical"
                # download_file(download_url, destination_folder, item["filename"])
                executor.submit(
                    download_file, download_url, destination_folder, item["filename"]
                )

            if next := response.get("nextPageToken"):
                body.update({"pageToken": next})
                response = service.mediaItems().search(body=body).execute()
            else:
                break

    print("The end")
