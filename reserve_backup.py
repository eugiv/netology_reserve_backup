from io import BytesIO
import requests
import json
from datetime import datetime
from tqdm import tqdm
import time
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive

FOLDER_NAME = "VK_photos"


class VK:
    def __init__(self, access_token, vk_user_id, version='5.154'):
        self.token = access_token
        self.id = vk_user_id
        self.version = version
        self.base_params = {'access_token': self.token, 'v': self.version}
        self.api_base_url = 'https://api.vk.com'
        self.photos_raw_data_list = []
        self.files_info = []

    def users_info(self):
        url = f'{self.api_base_url}/method/users.get'
        params = {'user_ids': self.id}
        response = requests.get(url, params={**self.base_params, **params})
        return response.json()

    def photos_raw_data(self, album_id="wall", photos_count=5):
        url = f'{self.api_base_url}/method/photos.get'
        params = {'owner_id': self.id,
                  "album_id": album_id,
                  "extended": True,
                  "count": photos_count}
        response = requests.get(url, params={**self.base_params, **params})
        photos = response.json()
        for key in tqdm(photos["response"]["items"], desc="1. Creating raw photos metadata"):
            time.sleep(0.05)
            max_photo_size = max(key["sizes"], key=lambda x: x.get("height", 0) + x.get("width", 0))
            raw_data = {"likes": key["likes"]["count"],
                        "upload_date": datetime.utcfromtimestamp(key["date"]).strftime('%Y-%m-%d'),
                        "photo_link": max_photo_size["url"],
                        "size": max_photo_size["type"],
                        "photo_id": key["id"]}

            self.photos_raw_data_list.append(raw_data)

    def photos_file(self):
        self.photos_raw_data()
        photos_data = self.photos_raw_data_list
        likes_list = [x["likes"] for x in photos_data]
        dates_list = [x["upload_date"] for x in photos_data]
        mutual_list_cnt = list(zip(likes_list, dates_list))

        for each_dict, mut in zip(tqdm(photos_data, desc="2. Saving metadata json"), mutual_list_cnt):
            time.sleep(0.05)
            likes_counter = likes_list.count(each_dict["likes"])
            dates_counter = dates_list.count(each_dict["upload_date"])
            mutual_counter = mutual_list_cnt.count(mut)

            if likes_counter == 1:
                each_dict["file_name"] = f'{each_dict["likes"]}.jpg'
            elif dates_counter == 1 or mutual_counter == 1:
                each_dict["file_name"] = f'{each_dict["likes"]}_{each_dict["upload_date"]}.jpg'
            else:
                each_dict["file_name"] = f'{each_dict["likes"]}_{each_dict["upload_date"]}_{each_dict["photo_id"]}.jpg'

            self.files_info.append({"file_name": each_dict["file_name"],
                                    "size": each_dict["size"]})

        with open("vk_photo_files_metadata.json", "w") as vk_file:
            json.dump(self.files_info, vk_file, indent=3)

    def photos_links(self):
        photos_url = self.photos_raw_data_list
        photos_url = [x.get("photo_link", "") for x in photos_url]
        return photos_url


class YA:
    def __init__(self, access_token, vk_files_info, vk_photos_links):
        self.token = access_token
        self.api_base_url = "https://cloud-api.yandex.net"
        self.base_headers = {"Authorization": access_token}
        self.vk_files_info = vk_files_info
        self.vk_photos_links = vk_photos_links

    def ya_create_folder(self):
        url = f'{self.api_base_url}/v1/disk/resources'
        params = {"path": f"{FOLDER_NAME}"}
        response = requests.get(url, headers=self.base_headers, params=params)
        if response.status_code == 200:
            return FOLDER_NAME
        else:
            requests.put(url, headers=self.base_headers, params=params)
            return FOLDER_NAME

    def ya_qet_load_link(self):
        url = f'{self.api_base_url}/v1/disk/resources/upload'

        links_ya_upload = []
        for photo_name in tqdm(self.vk_files_info, desc="3. Performing links for upload to Yandex Disc"):
            time.sleep(0.05)
            photo_name = photo_name.get("file_name", "")
            params = {"path": f"{self.ya_create_folder()}/{photo_name}",
                      "overwrite": False}

            url_exist = f'{self.api_base_url}/v1/disk/resources/download?path={params["path"]}'
            response = requests.head(url_exist, headers=self.base_headers, params=params)

            if response.status_code == 200:
                pass
            else:
                url_for_load = requests.get(url, headers=self.base_headers, params=params).json()
                links_ya_upload.append(url_for_load.get("href", ""))

        return links_ya_upload

    def ya_load_photos(self):
        for link_ya, link_vk in zip(self.ya_qet_load_link(),
                                    tqdm(self.vk_photos_links, desc="4. Uploading photos to a Yandex Disc folder")):
            time.sleep(0.05)
            if link_ya:
                vk_files = requests.get(link_vk).content
                requests.put(link_ya, files={"file": vk_files})


class GGL:
    def __init__(self, vk_files_info, vk_photos_links):
        self.gauth = GoogleAuth()
        self.gauth.LocalWebserverAuth()
        self.drive = GoogleDrive(self.gauth)
        self.vk_files_info = vk_files_info
        self.vk_photos_links = vk_photos_links

    def ggl_create_folder(self):
        folders_on_drive = self.drive.ListFile({'q': f"title='{FOLDER_NAME}' "
                                                     f"and mimeType='application/vnd.google-apps.folder'"}).GetList()

        if folders_on_drive:
            return folders_on_drive[0]["id"]
        else:
            params = {"title": f"{FOLDER_NAME}",
                      "mimeType": "application/vnd.google-apps.folder"}
            folder = self.drive.CreateFile(params)
            folder.Upload()
            return folder.get("id")

    def ggl_load_photos(self):
        folder_id = self.ggl_create_folder()
        for file_name, link_vk in zip(tqdm(self.vk_files_info, desc="5. Uploading photos to a Google Drive folder"),
                                      self.vk_photos_links):
            time.sleep(0.05)
            photo_on_drive = self.drive.ListFile({'q': f"title='{file_name.get('file_name', '')}' "
                                                       f"and '{folder_id}' in parents"}).GetList()

            if photo_on_drive:
                pass
            else:
                params = {"title": file_name.get('file_name', ''),
                          "parents": [{"id": folder_id}]}
                files = self.drive.CreateFile(params)
                files.content = BytesIO(requests.get(link_vk).content)
                files.Upload()


with open('tokens.txt') as f:
    file = json.loads(f.read())
    access_token_vkt = file["token_vk"]
    user_id = file["access_id"]
    access_token_yan = file["token_ya"]


# vk = VK(access_token_vkt, user_id)
# vk.photos_file()
#
# ya = YA(access_token_yan, vk.files_info, vk.photos_links())
# ya.ya_load_photos()
#
# ggl = GGL(vk.files_info, vk.photos_links())
# ggl.ggl_load_photos()
