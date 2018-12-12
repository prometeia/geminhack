from os import environ
from flask import Flask, render_template
from .geminlib import GeminAPI, GeminHack, last_commenter

app = Flask(__name__)
api_auth = environ['GEMINI_API_AUTH'].split(':')
ghack = GeminHack(GeminAPI(*api_auth))


@app.route("/wip")
def wip():
    wiptt = ghack.wip
    for ticket in wiptt:
        for killme in ("Description", "Attachments"):
            try:
                del ticket[killme]
            except KeyError:
                pass
        ticket["last_commenter"] = last_commenter(ticket)
        ticket["item_url"] = ghack.gapi.item_url(ticket['Id'])
    return render_template('wip.html', wip=wiptt, home=ghack.gapi.home)


if __name__ == '__main__':
    app.run(debug=True, use_debugger=False, use_reloader=False, passthrough_errors=True)
