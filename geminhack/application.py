from os import environ
from logging import getLogger, basicConfig, INFO
from flask import Flask, render_template, request, Response, abort
from .geminlib import GeminAPI, GeminHack
from .memoizer import memoize

COOKIENAME = 'geminhack'


basicConfig(level=INFO)
log = getLogger(__name__)
app = Flask(__name__)
contextroot = environ.get('CONTEXT_ROOT') or ''

FRESHARG = 'FRESH'


@memoize(lifespan=60, fresharg='FRESH')
def _create_ghack(username, password):
    gapi = GeminAPI(username, password)
    if not gapi.authenticated:
        abort(Response('Invalid LDAP auth', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'}))
    return GeminHack(gapi)


def authenticate():
    auth = request.authorization
    if not auth:
        abort(Response('Required auth', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'}))
    kwargs = {
        'username': auth.username,
        'password': auth.password,
        FRESHARG: request.headers.get('Cache-Control', '') == 'max-age=0'
    }
    return _create_ghack(**kwargs)


def route(subpath, methods=None):
    return app.route('%s/%s' % (contextroot, subpath), methods=(methods or ['GET']))


def render_ticktable(ghack, title, rows):
    return render_template(
        'ticktable.html', home=contextroot, title=title, rows=rows, project_page=ghack.gapi.project_page,
        workspace=ghack.gapi.workspace_page)


@route("/")
def home():
    return render_template('home.html')


@route("wip")
def tt_wip():
    ghack = authenticate()
    return render_ticktable(ghack, "WiP", ghack.wip)


@route("all")
def tt_all():
    ghack = authenticate()
    return render_ticktable(ghack, "All", ghack.tickets)


@route("active")
def tt_active():
    ghack = authenticate()
    return render_ticktable(ghack, "Active", ghack.active)


@route("waiting")
def tt_waiting():
    ghack = authenticate()
    return render_ticktable(ghack, "Waiting", ghack.responded)


if __name__ == '__main__':
    app.run(debug=True, use_debugger=False, use_reloader=False, passthrough_errors=True)
