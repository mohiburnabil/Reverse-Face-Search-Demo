import time
import requests
def search_by_face(image_file,api_key):
    TESTING_MODE = False
    if TESTING_MODE:
        print(
            "****** TESTING MODE search, results are inacurate, and queue wait is long, but credits are NOT deducted ******"
        )

    site = "https://facecheck.id"
    headers = {"accept": "application/json", "Authorization": api_key}
    files = {"images": open(image_file, "rb"), "id_search": None}
    response = requests.post(
        site + "/api/upload_pic", headers=headers, files=files
    ).json()

    if response["error"]:
        return f"{response['error']} ({response['code']})", None

    id_search = response["id_search"]
    # print(response["message"] + " id_search=" + id_search)
    json_data = {
        "id_search": id_search,
        "with_progress": False,
        "status_only": False,
        "demo": TESTING_MODE,
    }

    while True:
        response = requests.post(
            site + "/api/search", headers=headers, json=json_data
        ).json()
        if response["error"]:
            return f"{response['error']} ({response['code']})", None
        if response["output"]:
            return None, response["output"]["items"]
        print(f'{response["message"]} progress: {response["progress"]}%')
        time.sleep(1)