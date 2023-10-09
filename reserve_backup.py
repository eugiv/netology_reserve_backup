import requests
import json
from pprint import pprint


class VK:
    def __init__(self, access_token, user_id, version='5.154'):
        self.token = access_token
        self.id = user_id
        self.version = version
        self.base_params = {'access_token': self.token, 'v': self.version}
        self.api_base_url = "https://api.vk.com"

    def users_info(self):
        url = f'{self.api_base_url}/method/users.get'
        params = {'user_ids': self.id}
        response = requests.get(url, params={**self.base_params, **params})
        return response.json()

    def photos_info(self):
        url = f'{self.api_base_url}/method/photos.get'
        params = {'owner_id': self.id, "album_id": "wall", "extended": 1}
        response = requests.get(url, params={**self.base_params, **params})
        photos = response.json()

        photos_raw_data = []
        for key in photos["response"]["items"]:
            max_photo_size = max(key["sizes"], key=lambda x: x.get("height", 0) + x.get("width", 0))
            raw_data = {"likes": key["likes"]["count"],
                        "upload_date": key["date"],
                        "photo_link": max_photo_size["url"],
                        "size": max_photo_size["type"],
                        "photo_id": key["id"]}

            photos_raw_data.append(raw_data)

        likes_list = [x["likes"] for x in photos_raw_data]
        dates_list = [x["upload_date"] for x in photos_raw_data]
        mutual_list_cnt = list(zip(likes_list, dates_list))

        files_info = []
        for each_dict, mut in zip(photos_raw_data, mutual_list_cnt):
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
        pprint(files_info)


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
        params = {"path": f"{self.ya_create_folder()}/requirements.txt"}
        url_for_load = requests.get(url, headers=self.base_headers, params=params).json()
        return url_for_load.get("href", "")

    def ya_load_photos(self):
        with open("requirements.txt", "rb") as f:
            requests.put(self.ya_qet_load_link(), files={"file": f})


with open('tokens.txt') as f:
    file = json.loads(f.read())
    access_token_vk = file["token_vk"]
    user_id = file["access_id"]
    access_token_ya = file["token_ya"]

vk = VK(access_token_vk, user_id)
# vk.photos_info()
# vk.users_info()

ya = YA(access_token_ya)
ya.ya_load_photos()

