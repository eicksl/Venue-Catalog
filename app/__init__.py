#!/usr/bin/env python3

import random, string, os

from flask import Flask, request, abort, url_for
from flask import session as login_session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from functools import wraps

from app.models import Base


app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py')

engine = create_engine(app.config['DATABASE_URI'])
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


def get_random_string():
    '''Generates a random 32-character string comprised of uppercase ASCII
    characters and digits'''
    return ''.join(random.choice(string.ascii_uppercase + string.digits)
                   for x in range(32))


@app.context_processor
def override_url_for():
    '''Cache buster by Eric Buckley; see http://flask.pocoo.org/snippets/40'''
    return dict(url_for=dated_url_for)


def dated_url_for(endpoint, **values):
    '''Cache buster by Eric Buckley; see http://flask.pocoo.org/snippets/40'''
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                     endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)


@app.before_request
def csrf_protect():
    '''Checks that the CSRF token from the form matches the one in the Flask
    session.'''
    if request.method == 'POST':
        if 'csrf_token' in login_session:
            token = login_session['csrf_token']
        else:
            token = None
        if token is None or token != request.form.get('csrf_token'):
            abort(400)


def get_csrf_token():
    '''Returns the CSRF token in the Flask session. If one is not yet in the
    session then it is first generated and then returned.'''
    if 'csrf_token' not in login_session:
        login_session['csrf_token'] = get_random_string()
    return login_session['csrf_token']


from app.oauth.oauth import oauth_blueprint
from app.views.views import views_blueprint
from app.api.api import api_blueprint


app.register_blueprint(oauth_blueprint)
app.register_blueprint(views_blueprint)
app.register_blueprint(api_blueprint)

app.jinja_env.globals['get_csrf_token'] = get_csrf_token
app.secret_key = get_random_string()
