import requests

# 请求的URL
url = "https://sss.unmeta.cn/songlist"

# 要发送的表单数据
data = {
    "url": "https://y.qq.com/n/ryqq/playlist/7275687885"
}

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://music.unmeta.cn/"
}

# 发送POST请求
response = requests.post(url, data=data, headers=headers)

# 检查请求是否成功
if response.status_code == 200:
    # 打印响应JSON数据
    response_data = response.json()
    if response_data["code"] == 1:
        print("Playlist Name:", response_data["data"]["name"])
        print("Songs Count:", response_data["data"]["songs_count"])
        print("Songs List:")
        for song in response_data["data"]["songs"]:
            print("-", song)
    else:
        print("Error:", response_data["msg"])
else:
    print("Failed to retrieve data, Status Code:", response.status_code)
