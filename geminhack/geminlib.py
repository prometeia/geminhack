import requests
import json
import re
from requests_ntlm import HttpNtlmAuth
from logging import getLogger

log = getLogger(__name__)


def jdump(data, where=None):
    todump = json.dumps(data, sort_keys=True, indent=2)
    if where and isinstance(where, str):
        with open(where, "wt") as tg:
            tg.write(todump)
    elif where:
        where.write(todump)
    else:
        print(todump)


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
        log.info("User %s requesting %s", self.auth, uri)
        ret = requests.get(uri, auth=self.auth)
        log.debug("Resource %s returned %d", uri, ret.status_code)
        if not ret.status_code / 100 == 2:
            return
        return ret.json()

    @property
    def authenticated(self):
        return bool(self.project)

    @property
    def project(self):
        return self.get('projects', self.prjid)

    @property
    def workspace(self):
        return self.get("navigationcards", self.wsid) or {}

    @property
    def badges(self):
        return self.workspace.get('CardData', {}).get('Badges', [])
        
    def item(self, itemid, clean=True):
        ite = self.get("items", itemid) or {}
        if clean:
            ite = self.clean_item(ite)
        return ite

    @property
    def project_page(self):
        return "/".join([self.base_uri, "project", str(self.prjid), "board"])

    @property
    def workspace_page(self):
        return "/".join([self.base_uri, "workspace", str(self.wsid), "items"])

    def item_url(self, itemid):
        return "%s/workspace/%d/item/%d" % (self.base_uri, self.wsid, itemid)

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
        cfields = {t["Name"]: t for t in ticket.pop("CustomFields")}
        ticket.update(cfields)
        return ticket


class GeminHack(object):

    def __init__(self, geminapi):
        self.gapi = geminapi
        self._tickets = {bid: self.gapi.item(bid) for bid in self.gapi.badges}
        # TODO: Discover from gapi
        self.allofus = ["Luigi Curzi", "Denis Brandolini", "Glauco Uri", "Loredana Ribatto",
                        "Matteo Gnudi", "Alessio Durinzi"]

    @property
    def statuses(self):
        return set(t['Status'] for t in self._tickets.values())

    def _instatus(self, *statuses):
        return [t for t in self.tickets if t['Status'].lower() in [s.lower() for s in statuses]]

    def _notinstatus(self, *statuses):
        return [t for t in self.tickets if t['Status'].lower() not in [s.lower() for s in statuses]]
    
    @property
    def wip_real(self):
        return self._instatus("In charge", "Open", "Initial Response")

    @property
    def wip_virtual(self):
        return [t for t in self.responded if not self.we_lastcommented(t)]

    @property
    def tickets(self):
        return sorted(self._tickets.values(), key=lambda x: x.get("Revised"), reverse=True)

    @property
    def active(self):
        return self._notinstatus('closed')

    @property
    def wip(self):
        return sorted(self.wip_real + self.wip_virtual, key=lambda x: x.get("Revised"), reverse=True)

    @property
    def responded(self):
        return self._instatus("Responded")

    @property
    def ids(self):
        return sorted(self._tickets)

    def we_lastcommented(self, tick):
        return last_commenter(tick) in self.allofus


if __name__ == '__main__':
    import os
    import sys
    import tempfile
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("username")
    parser.add_argument("password")
    parser.add_argument("prjid", type=int)
    parser.add_argument("wsid", type=int)
    args = parser.parse_args()
    gapi = GeminAPI(args.username, args.password, args.prjid, args.wsid)
    ge = GeminHack(gapi)
    dwhere = tempfile.mkdtemp("export", "geminhack")
    print("Exporting issue in %s" % dwhere)
    for ti in ge.wip:
        print('- Issue [%s](%s) has status *%s* and last commenter "%s": *%s*.' % (
            ti["IssueKey"], gapi.item_url(ti["Id"]), ti["Status"], last_commenter(ti), ti["Title"]
        ))
        jdump(ti, os.path.join(dwhere, ti["IssueKey"] + ".json"))
