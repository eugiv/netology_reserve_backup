import requests
import json
from pprint import pprint
from datetime import datetime
from tqdm import tqdm
import time


class VK:
    def __init__(self, access_token_vk, user_id, version='5.154'):
        self.token = access_token_vk
        self.id = user_id
        self.version = version
        self.base_params = {'access_token': self.token, 'v': self.version}
        self.api_base_url = "https://api.vk.com"

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

        photos_raw_data = []
        for key in tqdm(photos["response"]["items"], desc="Creating raw photos metadata"):
            time.sleep(0.05)
            max_photo_size = max(key["sizes"], key=lambda x: x.get("height", 0) + x.get("width", 0))
            raw_data = {"likes": key["likes"]["count"],
                        "upload_date": datetime.utcfromtimestamp(key["date"]).strftime('%Y-%m-%d'),
                        "photo_link": max_photo_size["url"],
                        "size": max_photo_size["type"],
                        "photo_id": key["id"]}

            photos_raw_data.append(raw_data)
        return photos_raw_data

    def photos_file(self):
        photos_data = self.photos_raw_data()
        likes_list = [x["likes"] for x in photos_data]
        dates_list = [x["upload_date"] for x in photos_data]
        mutual_list_cnt = list(zip(likes_list, dates_list))

        files_info = []
        for each_dict, mut in tqdm(zip(photos_data, mutual_list_cnt), desc="Making metadata json"):
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
        photos_url = self.photos_raw_data()
        photos_url = [x.get("photo_link", "") for x in photos_url]
        return photos_url


class YA:
    def __init__(self, access_token_ya):
        self.token = access_token_ya
        self.api_base_url = "https://cloud-api.yandex.net"
        self.base_headers = {"Authorization": access_token_ya}

    def ya_create_folder(self):
        url = f'{self.api_base_url}/v1/disk/resources'
        folder_name = "VK_photos"
        params = {"path": f"{folder_name}"}
        requests.put(url, headers=self.base_headers, params=params)
        return folder_name

    def ya_qet_load_link(self):
        url = f'{self.api_base_url}/v1/disk/resources/upload'

        links_ya_upload = []
        for photo_name in tqdm(vk.photos_file(), desc="Performing links for upload to Yandex Disc"):
            time.sleep(0.05)
            photo_name = photo_name.get("file_name", "")
            params = {"path": f"{self.ya_create_folder()}/{photo_name}",
                      "overwrite": True}
            url_for_load = requests.get(url, headers=self.base_headers, params=params).json()
            links_ya_upload.append(url_for_load.get("href", ""))

        return links_ya_upload

    def ya_load_photos(self):
        for link_ya, link_vk in tqdm(zip(self.ya_qet_load_link(), vk.photos_links()),
                                     desc="Uploading photos to a Yandex Disc folder"):
            time.sleep(0.05)
            vk_files = requests.get(link_vk).content
            requests.put(link_ya, files={"file": vk_files})


with open('tokens.txt') as f:
    file = json.loads(f.read())
    access_token_vkt = file["token_vk"]
    user_id = file["access_id"]
    access_token_yan = file["token_ya"]

vk = VK(access_token_vkt, user_id)
# vk.photos_links()
# vk.photos_raw_data()
# vk.photos_file()

ya = YA(access_token_yan)
ya.ya_load_photos()
