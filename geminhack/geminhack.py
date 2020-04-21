import requests
import json
import re
import threading
from requests_ntlm import HttpNtlmAuth
from logging import getLogger
from .geminlib import last_commenter, GeminAPI
from .zubelib import ZubeAPI

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


class GeminHack(object):
    _tt_cache_lock = threading.Lock()

    def __init__(self, geminapi: GeminAPI, zubeapi: ZubeAPI):
        self.gapi: GeminAPI = geminapi
        self.zapi: ZubeAPI = zubeapi
        self._tt_cache = None
        # TODO: Discover from gapi
        self.allofus = ["Luigi Curzi", "Denis Brandolini", "Glauco Uri", "Loredana Ribatto",
                        "Matteo Gnudi", "Alessio Durinzi"]

    @property
    def _tickets(self):
        with self._tt_cache_lock:
            if self._tt_cache is None:
                self._tt_cache = {bid: self.gapi.get_item(bid) for bid in self.gapi.badges}
            return self._tt_cache

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
    gapi = GeminAPI(args.username, args.password, "https://erm-swfactory.prometeia.com/Gemini", 
                    args.prjid, args.wsid)
    ge = GeminHack(gapi, None)
    dwhere = tempfile.mkdtemp("export", "geminhack")
    print("Exporting issue in %s" % dwhere)
    for ti in ge.wip:
        print('- Issue [%s](%s) has status *%s* and last commenter "%s": *%s*.' % (
            ti["IssueKey"], gapi.item_url(ti["Id"]), ti["Status"], last_commenter(ti), ti["Title"]
        ))
        jdump(ti, os.path.join(dwhere, ti["IssueKey"] + ".json"))
