from os import makedirs
from flask import Flask

SETTINGS_VAR = "GEMINHACK_SETTINGS"


def create_app(test_config=None):
    # create and configure the app
    from .application import app
    
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_envvar(SETTINGS_VAR, silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        makedirs(app.instance_path)
    except OSError:
        pass

    return app