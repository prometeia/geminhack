from os import environ
from logging import getLogger, basicConfig, DEBUG
from flask import Flask, render_template, request, Response, abort, send_from_directory, redirect
from .memoizer import memoize
from .geminlib import GeminAPI
from .zubelib import ZubeAPI, private_key_from_pem
from .geminhack import GeminHack

PREFIXES = ('ESUP', 'UAT', 'ERMRFF', 'ERMDIR', 'ERM')
ALLOFUS = ["Luigi Curzi", "Denis Brandolini", "Glauco Uri", "Loredana Ribatto",
           "Matteo Gnudi", "Alessio Durinzi", "Mattia Gianessi"]


basicConfig(level=DEBUG)
log = getLogger(__name__)
app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY='dev',
    CONTEXT_ROOT='/',
    COOKIE_NAME='geminhack',
    GEMINI_URI="https://erm-swfactory.prometeia.com/Gemini",
    ESUP_PRJ_ID=46,
    ESUP_WS_ID=4236,
    ESUP_ZUBE_LABEL_ID=181120,
    UAT_PRJ_ID=37,
    UAT_WS_ID=4295,
    UAT_ZUBE_LABEL_ID=243959,
    ERMRFF_PRJ_ID=39,
    ERMRFF_WS_ID=4281,
    ERMRFF_ZUBE_LABEL_ID=224740,
    ERMDIR_PRJ_ID=40,
    ERMDIR_WS_ID=4256,
    ZUBE_PEM="zube_api_key.pem",
    ZUBE_CLIENT_ID="951b3e3e-83bd-11ea-ab20-cbd5058a8766",
    ZUBE_PRJ_ID=15973,
    ZUBE_PRJ_URI="https://zube.io/prometeia/pytho-suite",
    ERM_PRJ_ID=36,
    ERM_WS_ID=4524,
    ERM_ZUBE_LABEL_ID=248440,
    LOG_LEVEL_NUM=20
)
log.setLevel(int(app.config['LOG_LEVEL_NUM']))


def _create_ghack(username, password, confkey, FRESH=None):
    prjid = app.config['{}_PRJ_ID'.format(confkey)]
    wsid = app.config['{}_WS_ID'.format(confkey)]
    gapi = GeminAPI(username, password, base_uri=app.config['GEMINI_URI'], prjid=prjid, wsid=wsid)
    if not gapi.authenticated:
        log.warning("Failed GeminAPI bootstrap for %s", username)
        abort(Response('Invalid LDAP auth for', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'}))
    zapi = ZubeAPI(
        app.config['ZUBE_CLIENT_ID'],
        private_key_from_pem(app.config['ZUBE_PEM']),
        app.config['ZUBE_PRJ_ID'],
        app.config['ZUBE_PRJ_URI'])
    return GeminHack(gapi, zapi, ALLOFUS)


def get_hacker(confkey='ESUP') -> GeminHack:
    auth = request.authorization
    if not auth:
        abort(Response('Required auth', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'}))
    kwargs = {
        'username': auth.username,
        'password': auth.password,
        'confkey': confkey
    }
    return _create_ghack(**kwargs)


def route(subpath, methods=None):
    return app.route('%s/%s' % (app.config['CONTEXT_ROOT'], subpath), methods=(methods or ['GET']))


def render_ticktable(ghack, title, rows):
    return render_template(
        'ticktable.html', home=app.config['CONTEXT_ROOT'], title=title, rows=rows, project_page=ghack.gapi.project_page,
        workspace=ghack.gapi.workspace_page, zubeprojecturi=ghack.zapi.project_uri, zubesearcher=ghack.zapi.search_cards)


@route("/")
def home():
    return render_template('home.html', prefixes=PREFIXES,
                           home=app.config['CONTEXT_ROOT'],
                           gemini=app.config['GEMINI_URI'])


@route('statics/<path:path>')
def send_statics(path):
    return send_from_directory('statics', path)


@route("wip/<key>")
def tt_wip(key):
    ghack = get_hacker(key.upper())
    return render_ticktable(ghack, "{} WiP".format(key.upper()), ghack.wip)


@route("all/<key>")
def tt_all(key):
    ghack = get_hacker(key.upper())
    return render_ticktable(ghack, "{} All".format(key.upper()), ghack.tickets)


@route("workspace/<key>")
def tt_workspace(key):
    ghack = get_hacker(key.upper())
    return render_ticktable(ghack, "{} All".format(key.upper()), ghack.entire_workspace) 


@route("active/<key>")
def tt_active(key):
    ghack = get_hacker(key.upper())
    return render_ticktable(ghack, "{} Active".format(key.upper()), ghack.active)


@route("waiting/<key>")
def tt_waiting(key):
    ghack = get_hacker(key.upper())
    return render_ticktable(ghack, "{} Waiting".format(key.upper()), ghack.responded)


@route("items/<key>/<itemid>", ['GET', 'POST'])
def get_zube_refs(key, itemid):
    itemid = int(itemid)
    key = key.upper()
    ghack = get_hacker(key)
    item = ghack.gapi.get_item(itemid)
    if not item:
        abort(404)
    if request.method == 'GET':
        return {cardid:ghack.zapi.get_card(cardid) for cardid in item['zubeids']}
    if request.method != 'POST':
        abort(405)
    if item['zubeids']:
        return {}, 200
    title = f"{key}-{itemid}: {item['Title']}"
    itemuri = ghack.gapi.get_item_web_uri(itemid)
    body = item['description'] + f"\n\n---\n\n[{key}-{itemid}]({itemuri})"
    label = app.config.get(f'{key}_ZUBE_LABEL_ID')
    zubecard = ghack.zapi.create_card(title, body, label)
    if not zubecard:
        abort(500)
    data = ghack.gapi.item_add_zube_ref(itemid, zubecard['number'])
    if request.referrer:
        return redirect(request.referrer, code=302)
    else:
        return data, 201

@route("items/<key>/<itemid>/<zubeid>", ['POST'])
def add_zube_ref(key, itemid, zubeid):
    itemid = int(itemid)
    zubeid = int(zubeid)
    ghack = get_hacker(key.upper())
    item = ghack.gapi.get_item(itemid)
    if not item:
        abort(404)
    if zubeid in item['zubeids']:
        return {}, 200
    zubecard = ghack.zapi.get_card(zubeid)
    if not zubecard:
        abort(404)
    data = ghack.gapi.item_add_zube_ref(itemid, zubeid)
    if request.referrer:
        return redirect(request.referrer, code=302)
    else:
        return data
