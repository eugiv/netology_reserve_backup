import requests
import json
from datetime import datetime
from tqdm import tqdm
import time
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from googleapiclient.http import MediaFileUpload


class VK:
    def __init__(self, access_token, user_id, version='5.154'):
        self.token = access_token
        self.id = user_id
        self.version = version
        self.base_params = {'access_token': self.token, 'v': self.version}
        self.api_base_url = "https://api.vk.com"
        self.photos_raw_data_list = []

    def users_info(self):
        url = f'{self.api_base_url}/method/users.get'
        params = {'user_ids': self.id}
        response = requests.get(url, params={**self.base_params, **params})
        return response.json()

    def photos_raw_data(self):
        url = f'{self.api_base_url}/method/photos.get'
        params = {'owner_id': self.id,
                  "album_id": "wall",
                  "extended": True}
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

        files_info = []
        for each_dict, mut in zip(tqdm(photos_data, desc="2. Making metadata json"), mutual_list_cnt):
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

            files_info.append({"file_name": each_dict["file_name"],
                               "size": each_dict["size"]})

        with open("vk_photofiles_metadata.json", "w") as f:
            json.dump(files_info, f, indent=2)

        return files_info

    def photos_links(self):
        photos_url = self.photos_raw_data_list
        photos_url = [x.get("photo_link", "") for x in photos_url]
        return photos_url


class YA:
    def __init__(self, access_token):
        self.token = access_token
        self.api_base_url = "https://cloud-api.yandex.net"
        self.base_headers = {"Authorization": access_token}

    def ya_create_folder(self):
        url = f'{self.api_base_url}/v1/disk/resources'
        folder_name = "VK_photos"
        params = {"path": f"{folder_name}"}
        requests.put(url, headers=self.base_headers, params=params)
        return folder_name

    def ya_qet_load_link(self):
        url = f'{self.api_base_url}/v1/disk/resources/upload'

        links_ya_upload = []
        for photo_name in tqdm(vk.photos_file(), desc="3. Performing links for upload to Yandex and Google"):
            time.sleep(0.05)
            photo_name = photo_name.get("file_name", "")
            params = {"path": f"{self.ya_create_folder()}/{photo_name}",
                      "overwrite": True}
            url_for_load = requests.get(url, headers=self.base_headers, params=params).json()
            links_ya_upload.append(url_for_load.get("href", ""))

        return links_ya_upload

    def ya_load_photos(self):
        for link_ya, link_vk in zip(self.ya_qet_load_link(),
                                    tqdm(vk.photos_links(), desc="4. Uploading photos to a Yandex Disc folder")):
            time.sleep(0.05)
            vk_files = requests.get(link_vk).content
            requests.put(link_ya, files={"file": vk_files})


class GGL:
    def __init__(self):
        self.gauth = GoogleAuth()
        self.gauth.LocalWebserverAuth()
        self.drive = GoogleDrive(self.gauth)

    def ggl_create_folder(self):
        params = {"title": "VK_Photos",
                  "mimeType": "application/vnd.google-apps.folder"}
        folder = self.drive.CreateFile(params)
        folder.Upload()
        return folder.get("id")

    def ggl_load_photos(self):
        for link_vk in tqdm(vk.photos_links(), desc="4. Uploading photos to a Google Drive folder"):
            time.sleep(0.05)
            params = {"name": f"{requests.get(link_vk).content}",
                      "parents": [self.ggl_create_folder()]}
            MediaFileUpload(f"{requests.get(link_vk).content}", mimetype='image/jpeg', resumable=True)



with open('tokens.txt') as f:
    file = json.loads(f.read())
    access_token_vkt = file["token_vk"]
    user_id = file["access_id"]
    access_token_yan = file["token_ya"]


vk = VK(access_token_vkt, user_id)
# vk.photos_links()
vk.photos_raw_data()
vk.photos_file()

ya = YA(access_token_yan)
# ya.ya_load_photos()

ggl = GGL()
ggl.ggl_load_photos()
