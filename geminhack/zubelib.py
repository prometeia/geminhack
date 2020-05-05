import jwt
import datetime
import requests
from urllib.parse import urlparse
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization


def private_key_from_pem(pemfile):
    with open(pemfile, "rb") as pkey:
        return pkey.read()


def refresh_jwt(client_id, private_key):
    now = datetime.datetime.utcnow()
    # JWT expiration time (10 minute maximum)
    duration = datetime.timedelta(seconds=60)
    encoded = jwt.encode({'iat': now, 'exp': now + duration, 'iss': client_id}, 
                         private_key, algorithm='RS256')
    return client_id, encoded


def decode_jwt(jwt_token, public_key=None, verify=False):
    return jwt.decode(jwt_token, public_key, algorithms=['RS256'], verify=False)


class ZubeAPI(object):

    def __init__(self, client_id, private_key, project_id, project_uri="https://zube.io/prometeia/pytho-suite"):
        self.client_id = client_id
        self.private_key = private_key
        self.project_uri = project_uri
        self.project_id = project_id
        self._access_headers = self.create_access_token(self.client_id, self.private_key)

    @property
    def base_uri(self):
        pju = urlparse(self.project_uri)
        return f"{pju.scheme}://{pju.netloc}"

    def get_card_uri(self, number):
        return f"{self.project_uri}/c/{number}"
        
    def create_access_token(self, client_id, private_key):
        client_id, jwt_ticket = refresh_jwt(client_id, private_key)
        headers = {
            "Authorization": "Bearer {}".format(jwt_ticket.decode()),
            "X-Client-ID": client_id,
            "Accept": "application/json"
        }
        ret = requests.post(f"{self.base_uri}/api/users/tokens", headers=headers)
        if ret.status_code // 100 != 2:
            return
        headers["Authorization"] = "Bearer {}".format(ret.json().get("access_token"))
        return headers

    def get(self, *subs):
        uri = "/".join([self.base_uri + '/api'] + [str(x) for x in subs])
        headers = self._access_headers.copy()
        ret = requests.get(uri, headers=headers)
        if not ret.status_code / 100 == 2:
            return
        return ret.json()

    def post(self, jsonbody, *subs):
        uri = "/".join([self.base_uri + '/api'] + [str(x) for x in subs])
        headers = self._access_headers.copy()
        ret = requests.post(uri, json=jsonbody, headers=headers)
        if not ret.status_code / 100 == 2:
            return
        return ret.json()     

    def get_card(self, number):
        cards = (self.get(f'cards?where[number]={number}') or {}).get('data')
        if not cards:
            return {}
        return cards[0]

    def search_cards(self, search=""):
        cards = self.get('projects', self.project_id, f'cards?search={search}&select[]=title&&select[]=number') or {}
        return cards.get('data')

    def create_card(self, title, body, label=None):
        data = dict(project_id=self.project_id, title=title, body=body)
        if label:
            data['label_ids'] = [label]
        return self.post(data, 'cards')
