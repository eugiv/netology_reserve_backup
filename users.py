from reserve_backup import VK, YA, GGL

if __name__ == '__main__':
    print("Enter your VK user_id:\n")
    user_id = input()
    print("Enter your VK token:\n")
    token = input()
    vk = VK(token, user_id)
    vk.photos_file()

    print("Enter your Yandex token(started with 'OAuth ':\n")
    token = input()
    ya = YA(token, vk.files_info, vk.photos_links())
    ya.ya_load_photos()

    # ggl = GGL(vk.files_info, vk.photos_links())  # works only locally (because of auth)
    # ggl.ggl_load_photos()
