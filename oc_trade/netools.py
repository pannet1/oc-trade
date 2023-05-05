import requests
import yaml


def yaml_from_github(repo: str, folder: str, filename: str):
    baseurl = "https://raw.githubusercontent.com/pannet1"
    url = f"{baseurl}/{repo}/main/{folder}/{filename}.yaml"
    print(url)
    response = requests.get
    if response.status_code == 200:
        data = yaml.load(response.text, Loader=yaml.FullLoader)
        return data
    else:
        return None


def load_ymls_from_github(repo: str, folder: str):
    url = f"https://api.github.com/repos/pannet1/{repo}/contents/{folder}"
    response = requests.get(url)
    if response.status_code == 200:
        data = []
        files = response.json()
        for file in files:
            if file["type"] == "file" and file["name"].endswith(".yaml"):
                data.append(file["name"][:-5])
        return data
    else:
        return None


def load_dict_from_github(repo: str, folder: str, yml_name: str):
    url = f"https://api.github.com/repos/pannet1/{repo}/contents/{folder}"
    response = requests.get(url)
    data = None
    if response.status_code == 200:
        files = response.json()
        for file in files:
            if file["type"] == "file" and file["name"] == yml_name + ".yaml":
                url = file["download_url"]
                response = requests.get(url)
                if response.status_code == 200:
                    data = yaml.load(response.text, Loader=yaml.FullLoader)
                    print(data)
    return data
