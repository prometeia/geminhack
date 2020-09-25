import argparse
import logging
import re
from yaml import dump
from types import SimpleNamespace
from re import match
from pymongo import MongoClient
from github import GithubException, Requester
from .githublib import GitHubBoarder
from .geminlib import GeminAPI


log = logging.getLogger(__name__)


def _dumpme(*items, **kvitems):
    print(dump(items))
    print(dump(kvitems))


def text2gitem(text):
    gitem = match(r'((?:ESUP|UAT)-\d+): ', text)
    if gitem:
        return gitem.group(0)


class Gegi(object):
    GEMINI_URI = "https://erm-swfactory.prometeia.com/Gemini"

    def __init__(self):
        parser = argparse.ArgumentParser()
        parser.add_argument("mongouri")
        parser.add_argument("confkey", default="MAIN", help="Unique configuration KEY")
        parser.add_argument("-t", "--token")
        parser.add_argument("-o", "--organization")
        parser.add_argument("-u", "--username")
        parser.add_argument("-p", "--password")
        parser.add_argument("-b", "--board")
        parser.add_argument("--quoteboard", default=GitHubBoarder.SPRINT_BOARD_NAME, help="Board to quote")
        parser.add_argument("--quotefile", help="Output csv file of quoting")
        parser.add_argument('-w','--workspaces', nargs='+', help='List of project:workspaces on Gemini')
        args = parser.parse_args()
        # Connecting to mongodb
        self.db = MongoClient(args.mongouri).get_default_database()
        ref = {"_id": args.confkey}
        log.info("Working with configuration %s", ref['_id'])
        mainconf = dict(self.db.conf.find_one(ref) or ref)
        for key, val in vars(args).items():
            if val is not None and key not in ('mongouri', 'quoteboard', 'quotefile'):
                mainconf[key] = val
        self.db.conf.replace_one(ref, mainconf, upsert=True)
        self.conf = SimpleNamespace(**mainconf)
        self.quoteboard = args.quoteboard
        self.quotefile = args.quotefile
        self.icoll = self.db.items

    def workspaces_pull(self):
        # Listing Gemini items
        if not self.conf.workspaces:
            log.warning("No workspaces specified, skipping pull")
        for wp in self.conf.workspaces:
            pid, wid = wp.split(':', 1)
            pid = int(pid)
            wid = int(wid)
            gapi = GeminAPI(self.conf.username, self.conf.password, self.GEMINI_URI, prjid=pid, wsid=wid)
            assert gapi.authenticated
            for item in gapi.search_items():
                be = item['BaseEntity']
                self.icoll.update_one(
                    {'_id': item['IssueKey']},
                    {'$set': dict(
                        title=be['Title'].strip(),
                        status=item['Status'],
                        creator=item['Creator'],
                        uri=item['item_url']
                    )},
                    upsert=True
                )

    def board_push(self):
        gb = GitHubBoarder(self.conf.token, self.conf.organization)
        if not self.conf.board:
            log.warning("No board specified, skipping push")
            return
        geboard = gb.get_board(self.conf.board)
        assert geboard, f"Missing project board '{self.conf.board}'"
        backlog = geboard.get_columns()[0]
        for item in self.icoll.find(dict(status={'$nin': ['Closed']}, added=None)).sort('_id'):
            c = backlog.create_card(
                note=f"{item['_id']}: {item['title']}\n\ncfr. [{item['_id']}]({item['uri']})")
            print(f"{item['_id']}: {item['title']} -> {c}")
            self.icoll.update_one({'_id': item['_id']}, {"$set": {"added": c.id}})

    def boards_report(self):
        gb = GitHubBoarder(self.conf.token, self.conf.organization)
        qboard = gb.get_board(self.quoteboard)
        cards = []
        _dumpme(name=qboard.name, html=qboard.html_url)
        for col in qboard.get_columns():
            log.info("Analyzing column %s: %s", col.name, f'{qboard.html_url}/columns/{col.id}/cards')
            for card in col.get_cards(archived_state="false"):
                title = card.note
                if title is None and card.content_url is not None:
                    log.info("Reading %s: %s", card.content_url, card.url)
                    try:
                        data = card.get_content()
                        if data is None:
                            continue
                        title = data.title
                    except GithubException as ghe:
                        log.error("Failed content get: %s", str(ghe))
                        continue
                if title:
                    head = title.splitlines()[0].strip()
                    dur = re.search(r'\[s([01235])\]', head)
                    if dur:
                        size = int(dur.group(1))
                    else:
                        size = ""
                    cards.append((col.name, head, size))
        for bor, car, size in cards:
            log.info(f"{bor:20} {size:4}: {car}")
        if self.quotefile:
            log.info("Creating %s quote file", self.quotefile)
            with open(self.quotefile, 'wt') as qf:
                qf.write("status;size;title\n")
                for status, title, size in cards:
                    qf.write(f'"{status}";{size};"{title}"\n')


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    gegi = Gegi()    
    gegi.workspaces_pull()
    gegi.board_push()
    gegi.boards_report()
