
import requests

url = "https://api.github.com"

try:
    response = requests.get(url, timeout=5)

    print("HTTP状态码:", response.status_code)

    response.raise_for_status()
    data = response.json()

    print("GitHub API地址:", data["current_user_url"])

except requests.exceptions.RequestException as e:
    print("请求失败:", e)
