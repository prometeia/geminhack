from os import environ
from flask import Flask, render_template
from .geminlib import GeminAPI, GeminHack, last_commenter

app = Flask(__name__)
api_auth = environ['GEMINI_API_AUTH'].split(':')
contextroot = environ.get('CONTEXT_ROOT') or ''
gapi = GeminAPI(*api_auth)


def route(subpath):
    return app.route('%s/%s' % (contextroot, subpath))


def render_ticktable(ghack, title, rows):
    return render_template(
        'ticktable.html', title=title, rows=rows, home=ghack.gapi.project_page, workspace=ghack.gapi.workspace_page)


@route("wip")
def tt_wip():
    ghack = GeminHack(gapi)
    return render_ticktable(ghack, "WiP", ghack.wip)


@route("all")
def tt_all():
    ghack = GeminHack(gapi)
    return render_ticktable(ghack, "All", ghack.tickets)


@route("active")
def tt_active():
    ghack = GeminHack(gapi)
    return render_ticktable(ghack, "Active", ghack.active)


if __name__ == '__main__':
    app.run(debug=True, use_debugger=False, use_reloader=False, passthrough_errors=True)
