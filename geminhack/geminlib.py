import requests
import json
import re
from functools import cached_property
from requests_ntlm import HttpNtlmAuth
from logging import getLogger

log = getLogger(__name__)


def last_commenter(tick):
    cms = tick["Comments"]
    if not cms:
        return ""
    return cms[0].get("BaseEntity", {}).get("Fullname") or ""


def stripsignature(text):
    splitters = [r'<br>\s*<br>\s*<img.*?width="159" height="51"', '<table']
    for sp in splitters:
        text = re.split(sp, text)[0]
    text = re.sub(r'(<br>\s*)+', r'<br>\n', text)
    return text


def last_comment(tick):
    cms = tick["Comments"]
    if not cms:
        return ""
    comment = cms[0].get("BaseEntity", {}).get("Comment") or ""
    return stripsignature(comment)


def comments2zubeids(comments):
    zuber = re.compile(r'ZUBE#(\d+)')
    found = []
    for comment in comments:
        found.extend(int(n) for n in zuber.findall(comment['BaseEntity']['Comment']))
    return sorted(set(found))


class GeminAPI(object):
    """
        https://docs.countersoft.com/rest-api/
    """

    def __init__(self, user, password, base_uri, prjid, wsid):
        self.prjid = prjid
        self.wsid = wsid
        self.base_uri = base_uri
        self.auth = HttpNtlmAuth(user, password)

    def _apiuri(self, *vargs):
        return "/".join([self.base_uri + '/api'] + [str(x) for x in vargs])

    def get(self, *subs):
        uri = self._apiuri(*subs)
        log.info("User %s getting %s", self.auth, uri)
        ret = requests.get(uri, auth=self.auth)
        log.debug("Resource %s returned %d", uri, ret.status_code)
        if not ret.status_code / 100 == 2:
            return
        return ret.json()

    def post(self, dictdata, *subs):
        uri = self._apiuri(*subs)
        log.info("User %s posting %s", self.auth, uri)
        ret = requests.post(uri, auth=self.auth, json=dictdata)
        log.debug("Resource %s returned %d", uri, ret.status_code)
        if not ret.status_code / 100 == 2:
            return
        return ret.json()        

    @property
    def authenticated(self):
        return bool(self.workspace)

    @cached_property
    def project(self):
        return self.get('projects', self.prjid)

    @cached_property
    def workspace(self):
        return self.get("navigationcards", self.wsid) or {}

    def search_items(self):
        return self.post(self.workspace.get('Filter'), 'items', 'filtered')

    @cached_property
    def badges(self):
        return self.workspace.get('CardData', {}).get('Badges', [])
        
    def get_item(self, itemid, clean=True):
        ite = self.get("items", itemid) or {}
        if clean and ite:
            ite = self.clean_item(ite)
        return ite

    @cached_property
    def project_page(self):
        return "/".join([self.base_uri, "project", str(self.prjid), "board"])

    @cached_property
    def workspace_page(self):
        return "/".join([self.base_uri, "workspace", str(self.wsid), "items"])

    def get_item_web_uri(self, itemid):
        return f"{self.base_uri}/workspace/{self.wsid}/item/{itemid}"

    def item_url(self, itemid):
        return "%s/workspace/%d/item/%d" % (self.base_uri, self.wsid, itemid)

    def item_get_zube_ref(self, itemid, zubeid):
        comments = self.get("items", str(itemid), "comments")
        return comments2zubeids(comments)

    def item_add_zube_ref(self, itemid, zubeid):
        created = self.post({"IssueId": itemid, "Comment": f"ZUBE#{zubeid}"}, 
                            "items", str(itemid), "comments")
        return created

    def clean_item(self, item):
        """Remove and reformat fields"""
        ticket = item.copy()
        for kme in ("Description", "Attachments"):
            try:
                del ticket[kme]
            except KeyError:
                pass
        ticket["last_commenter"] = last_commenter(ticket)
        ticket["last_comment"] = last_comment(ticket)
        ticket["item_url"] = self.item_url(ticket["Id"])
        ticket["description"] = stripsignature(ticket['BaseEntity']["Description"])
        ticket["zubeids"] = comments2zubeids(ticket['Comments'])
        ticket['risorse'] = ', '.join([t['Fullname'] for t in ticket.get('Resources', [])])
        cfields = {t["Name"]: t for t in ticket.pop("CustomFields")}
        ticket.update(cfields)
        return ticket
