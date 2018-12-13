import requests
import json

PYTHO_WORKSPACE_ID = 3116
ESUP_PROJECT_ID = 46


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


class GeminAPI(object):
    base_uri = "https://erm-swfactory.prometeia.com/Gemini"

    def __init__(self, user, password, prjid=ESUP_PROJECT_ID, wsid=PYTHO_WORKSPACE_ID):
        self.prjid = prjid
        self.wsid = wsid
        self.auth = user, password

    def _apiuri(self, *vargs):
        return "/".join([self.base_uri + '/api'] + [str(x) for x in vargs])

    def get(self, *subs):
        uri = self._apiuri(*subs)
        ret = requests.get(uri, auth=self.auth)
        assert ret.status_code / 100 == 2
        return ret.json()

    @property
    def workspace(self):
        return self.get("navigationcards", self.wsid) or {}

    @property
    def badges(self):
        return self.workspace.get('CardData', {}).get('Badges', [])

    def item(self, itemid):
        return self.get("items", itemid) or {}

    @property
    def home(self):
        return self.get("projects", self.prjid).get("HomePageUrl", "")

    def item_url(self, itemid):
        return "%s/workspace/%d/item/%d" % (self.base_uri, self.wsid, itemid)


class GeminHack(object):

    def __init__(self, geminapi):
        self.gapi = geminapi
        self.tickets = {bid: self.gapi.item(bid) for bid in self.gapi.badges}
        # TODO: Discover from gapi
        self.allofus = ["Luigi Curzi", "Denis Brandolini", "Glauco Uri", "Loredana Ribatto",
                        "Matteo Gnudi", "Marco Montanari"]

    @property
    def statuses(self):
        return set(t['Status'] for t in self.tickets.values())

    def _instatus(self, *statuses):
        return [t for t in self.tickets.values() if t['Status'] in statuses]
    
    @property
    def wip_real(self):
        return self._instatus("In Charge", "Open")

    @property
    def wip_virtual(self):
        return [t for t in self.responded if not self.we_lastcommented(t)]

    @property
    def wip(self):
        return sorted(self.wip_real + self.wip_virtual, key=lambda x: x.get("Revised"))

    @property
    def responded(self):
        return self._instatus("Initial Response", "Responded")

    @property
    def ids(self):
        return sorted(self.tickets)

    def we_lastcommented(self, tick):
        return last_commenter(tick) in self.allofus


if __name__ == '__main__':
    import os
    import glob
    import sys
    gapi = GeminAPI(*sys.argv[1:3])
    ge = GeminHack(gapi)
    dwhere = "export"
    try:
        os.mkdir(dwhere)
    except FileExistsError:
        for ajson in glob.glob("%s/*.json" % dwhere):
            os.remove(ajson)
    for ti in ge.wip:
        for killme in ("Description", "Attachments"):
            del ti[killme]
        print('- Issue [%s](%s) has status *%s* and last commenter "%s": *%s*.' % (
            ti["IssueKey"], gapi.item_url(ti["Id"]), ti["Status"], last_commenter(ti), ti["Title"]
        ))
        jdump(ti, "%s/%s.json" % (dwhere, ti["IssueKey"]))
