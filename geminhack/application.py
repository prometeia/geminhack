from os import environ
from logging import getLogger, basicConfig, INFO
from flask import Flask, render_template, request, Response, abort, send_from_directory
from .geminlib import GeminAPI, GeminHack
from .memoizer import memoize
from .zubelib import ZubeAPI, private_key_from_pem

PREFIXES = ('ESUP', 'UAT', 'RFF', 'DIR')

basicConfig(level=INFO)
log = getLogger(__name__)
app = Flask(__name__, instance_relative_config=True)
app.config.from_mapping(
    SECRET_KEY='dev',
    CONTEXT_ROOT='/',
    COOKIE_NAME='geminhack',
    GEMINI_URI="https://erm-swfactory.prometeia.com/Gemini",
    ESUP_PRJ_ID=46,
    ESUP_WS_ID=4236,
    UAT_PRJ_ID=37,
    UAT_WS_ID=4295,
    RFF_PRJ_ID=39,
    RFF_WS_ID=4281,
    DIR_PRJ_ID=40,
    DIR_WS_ID=4256,
    ZUBE_PEM="zube_api_key.pem",
    ZUBE_CLIENT_ID="951b3e3e-83bd-11ea-ab20-cbd5058a8766"
)


@memoize(lifespan=30, fresharg='FRESH')
def _create_ghack(username, password, confkey, FRESH=None):
    assert FRESH is None, "It should not come down"
    prjid = app.config['{}_PRJ_ID'.format(confkey)]
    wsid = app.config['{}_WS_ID'.format(confkey)]
    gapi = GeminAPI(username, password, base_uri=app.config['GEMINI_URI'], prjid=prjid, wsid=wsid)
    if not gapi.authenticated:
        abort(Response('Invalid LDAP auth', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'}))
    zapi = ZubeAPI(app.config['ZUBE_CLIENT_ID'], private_key_from_pem(app.config['ZUBE_PEM']))
    return GeminHack(gapi, zapi)


def get_hacker(confkey='ESUP'):
    auth = request.authorization
    if not auth:
        abort(Response('Required auth', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'}))
    kwargs = {
        'username': auth.username,
        'password': auth.password,
        'confkey': confkey,
        'FRESH': request.headers.get('Cache-Control', '') == 'max-age=0'
    }
    return _create_ghack(**kwargs)


def route(subpath, methods=None):
    return app.route('%s/%s' % (app.config['CONTEXT_ROOT'], subpath), methods=(methods or ['GET']))


def render_ticktable(ghack, title, rows):
    return render_template(
        'ticktable.html', home=app.config['CONTEXT_ROOT'], title=title, rows=rows, project_page=ghack.gapi.project_page,
        workspace=ghack.gapi.workspace_page)


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


@route("active/<key>")
def tt_active(key):
    ghack = get_hacker(key.upper())
    return render_ticktable(ghack, "{} Active".format(key.upper()), ghack.active)


@route("waiting/<key>")
def tt_waiting(key):
    ghack = get_hacker(key.upper())
    return render_ticktable(ghack, "{} Waiting".format(key.upper()), ghack.responded)
