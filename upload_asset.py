import os
import requests
import time


def upload_asset():
    headers = {'Authorization': f"Bearer {os.environ['GITHUB_TOKEN']}",
               'Content-Type': os.environ['ASSET_CONTENT_TYPE'],}
    with open(os.environ['ASSET_PATH'], 'rb') as f:
        data = f.read()
    # if the upload fails, keep retrying
    while True:
        try:
            response = requests.post(os.environ['UPLOAD_URL'].replace('{?name,label}', f"?name={os.environ['ASSET_NAME']}", headers=headers, data=data)
            if response.status_code == 201:
              break
        except:
            pass
        time.sleep(1)


if __name__ == '__main__':
    upload_asset()
