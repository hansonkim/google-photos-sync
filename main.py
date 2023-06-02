from concurrent.futures import ThreadPoolExecutor
import os
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from datetime import datetime, timedelta
import requests
import json


# Google Photos Library API 권한 정의
TOKEN = None
SCOPES = ["https://www.googleapis.com/auth/photoslibrary.readonly"]
CLIENT_SECRET_FILE = "token.json"
credFile = f"token_photo_sync_user.json"


def download_file(url: str, destination_folder: str, file_name: str):
    with requests.get(
        url, headers={"Authorization": f"Bearer {TOKEN}"}, stream=True
    ) as response:
        if response.status_code == 200:
            file = os.path.join(destination_folder, file_name)
            if os.path.exists(file):
                print(f"Already exist file {file_name}")
                return

            print("Downloading file {0}".format(file_name))

            with open(file, "wb") as f:
                for c in response.iter_content(chunk_size=1024 * 1024):
                    if c:
                        f.write(c)


def download_video(service):
    # 즐겨찾기한 사진 가져오기
    body = {
        "pageSize": 100,
        "filters": {
            "mediaTypeFilter": {"mediaTypes": ["VIDEO"]},
        },
    }
    sum = 0
    with ThreadPoolExecutor(max_workers=50) as executor:
        response = service.mediaItems().search(body=body).execute()
        while response and (media_items := response.get("mediaItems")):
            for item in media_items:
                _id = item["id"]
                # download_url = f"https://photoslibrary.googleapis.com/v1/mediaItems/{_id}"
                download_url = item["baseUrl"] + "=dv"
                destination_folder = "/Users/hanson/Movies/google_photo"

                creation_time = item.get("mediaMetadata", {}).get("creationTime")
                if creation_time:
                    creation_time = datetime.fromisoformat(creation_time) + timedelta(
                        hours=9
                    )
                    creation_time = creation_time.strftime("%Y%m%dT%H%M%S")

                executor.submit(
                    download_file,
                    download_url,
                    destination_folder,
                    f"{creation_time}_{item['filename']}",
                )
            if next := response.get("nextPageToken"):
                body.update({"pageToken": next})
                response = service.mediaItems().search(body=body).execute()
            else:
                break


def download_favorites(service):
    # 즐겨찾기한 사진 가져오기
    body = {
        "pageSize": 100,
        "filters": {
            "featureFilter": {"includedFeatures": ["FAVORITES"]},
            "mediaTypeFilter": {"mediaTypes": ["PHOTO"]},
        },
    }
    sum = 0
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
            sum += len(media_items)
            if next := response.get("nextPageToken"):
                body.update({"pageToken": next})
                response = service.mediaItems().search(body=body).execute()
            else:
                break


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

    with open(credFile, "r") as f:
        t = f.read()
        token_json = json.loads(t)
        TOKEN = token_json["token"]

    # 구글 포토 API 사용
    service = build("photoslibrary", "v1", credentials=creds, static_discovery=False)

    download_video(service)
    # download_favorites(service)

    print("The end")
