import os
import requests
import time


def upload_asset():
    headers = {'Authorization': f"token {os.environ['GITHUB_TOKEN']}",
               'Content-Type': os.environ['ASSET_CONTENT_TYPE'],}
    params = (('name', os.environ['ASSET_NAME']),)
    with open(os.environ['ASSET_PATH'], 'rb') as f:
        data = f.read()
    # if the upload fails, keep retrying
    while True:
        try:
            response = requests.post(f"{os.environ['UPLOAD_URL']}", headers=headers, params=params, data=data)
            if response.status_code == 201:
              break
        except:
            pass
        time.sleep(1)
        print('Upload failed, retrying...')


if __name__ == '__main__':
    upload_asset()
