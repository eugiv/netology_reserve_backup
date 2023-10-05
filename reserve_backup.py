import requests


class VK:
    def __init__(self, access_token, user_id, version='5.131'):
        self.token = access_token
        self.id = user_id
        self.version = version
        self.params = {'access_token': self.token, 'v': self.version}

    def users_info(self):
        url = 'https://api.vk.com/method/users.get'
        params = {'user_ids': self.id}
        response = requests.get(url, params={**self.params, **params})
        return response.json()

    def photos_info(self):
        url = ''

with open ('tokens.txt') as f:
    for i in [f.readlines()]:
        access_token = i[0]
        user_id = i[1]

vk = VK(access_token, user_id)
print(vk.users_info())