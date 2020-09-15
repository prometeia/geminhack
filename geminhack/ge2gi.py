import argparse
from yaml import dump
from types import SimpleNamespace
from re import match
from pymongo import MongoClient
from github import GithubException
from .githublib import GitHubBoarder
from .geminlib import GeminAPI

GEMINI_URI = "https://erm-swfactory.prometeia.com/Gemini"


def _dumpme(*items):
    for i in items:
        print(dump(i))


def text2gitem(text):
    gitem = match(r'((?:ESUP|UAT)-\d+): ', text)
    if gitem:
        return gitem.group(0)


def args2conf():    
    parser = argparse.ArgumentParser()
    parser.add_argument("mongouri")
    parser.add_argument("-t", "--token")
    parser.add_argument("-o", "--organization")
    parser.add_argument("-u", "--username")
    parser.add_argument("-p", "--password")
    parser.add_argument("-b", "--board", default="!Bug, Supporto e Processi")
    parser.add_argument('-w','--workspaces', nargs='+', help='List of project:workspaces on Gemini')    
    args = parser.parse_args()    
    # Connecting to mongodb
    db = MongoClient(args.mongouri).get_default_database()
    ref = {"_id":'MAIN'}
    mainconf = dict(db.conf.find_one(ref) or ref)
    for key, val in vars(args).items():
        if val is not None:
            mainconf[key] = val
    db.conf.replace_one(ref, mainconf, upsert=True)
    conf = SimpleNamespace(**mainconf)
    conf.db = db
    return conf


if __name__ == '__main__':
    conf = args2conf()
    # Listing Gemini items
    icoll = conf.db.items
    for wp in conf.workspaces:
        pid, wid = wp.split(':', 1)
        pid = int(pid)
        wid = int(wid)
        gapi = GeminAPI(conf.username, conf.password, GEMINI_URI, prjid=pid, wsid=wid)
        assert gapi.authenticated
        for n, item in enumerate(gapi.search_items()):
            be = item['BaseEntity']            
            id = item['IssueKey']
            icoll.update_one(
                {'_id': item['IssueKey']}, 
                {'$set': dict(                
                    title=be['Title'].strip(),
                    status=item['Status'],
                    creator=item['Creator'],
                    uri=item['item_url']
                )},
                upsert=True
            )
    # Adding missing cards
    gb = GitHubBoarder(conf.token, conf.organization)
    geboard = gb.get_board(conf.board)    
    assert geboard, f"Missing project board '{conf.board}'"
    backlog = geboard.get_columns()[0]
    for item in icoll.find(dict(status={'$nin': ['Closed']}, added=None)).sort('_id'):
        c = backlog.create_card(
            note=f"{item['_id']}: {item['title']}\n\ncfr. [{item['_id']}]({item['uri']})")
        print(f"{item['_id']}: {item['title']} -> {c}")
        icoll.update_one({'_id': item['_id']}, {"$set": {"added": c.id}})
