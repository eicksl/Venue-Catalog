#!/usr/bin/env python3

import requests
import httplib2
import os
import json

from flask import Blueprint, render_template, url_for, redirect, request
from flask import make_response, flash
from flask import session as login_session
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
from functools import wraps

from app import app, session
from app.models import User


oauth_blueprint = Blueprint('oauth', __name__)


def login_required(login):
    '''Takes a function as a parameter and returns it if the user is logged in;
    otherwise redirects to the login page'''
    @wraps(login)
    def check_login_status(*args, **kwargs):
        if 'user_key' in login_session:
            return login(*args, **kwargs)
        else:
            return redirect('/login')
    return check_login_status


@app.template_filter('authorized')
def authorized(venue_user_key):
    '''Returns True if the user key in the flask session matches the venue's
    user key, else returns False'''
    if 'user_key' in login_session and login_session['user_key'] == venue_user_key:
        return True
    else:
        return False


@oauth_blueprint.route('/fbconnect', methods=['POST'])
def fbconnect():
    '''Exchanges short term token for long term one, then logs in the user'''
    short_term_token = request.form['token']
    app_id = json.loads(open(
        'fb_client_secrets.json', 'r').read())['web']['app_id']
    app_secret = json.loads(open(
        'fb_client_secrets.json', 'r').read())['web']['app_secret']
    #app_id = json.loads(open(
    #    '/var/www/Venue-Catalog/fb_client_secrets.json', 'r').read())['web']['app_id']
    #app_secret = json.loads(open(
    #    '/var/www/Venue-Catalog/fb_client_secrets.json', 'r').read())['web']['app_secret']
    auth_url = ('https://graph.facebook.com/oauth/access_token?grant_type='
                'fb_exchange_token&client_id={}&client_secret={}'
                '&fb_exchange_token={}').format(app_id, app_secret,
                                                short_term_token)

    http = httplib2.Http()
    resp = http.request(auth_url, 'GET')
    if resp[0]['status'] != '200':
        error_msg = 'Login was aborted due to an invalid token'
        flash(error_msg)
        return make_response(error_msg, 401)

    long_term_token = json.loads(resp[1].decode())['access_token']

    info_url = 'https://graph.facebook.com/v2.8/me'
    params = {
        'access_token': long_term_token,
        'fields': 'name,id,email'
    }
    resp = requests.get(info_url, params)
    info = resp.json()

    login_session['token'] = long_term_token
    login_session['provider'] = 'facebook'
    login_session.permanent = True

    fb_id = request.form['fb_id']  # Unique facebook account identifier
    email = info['email']
    fb_id_in_db = session.query(User.fb_id).filter_by(fb_id=fb_id).scalar()
    email_in_db = session.query(User.email).filter_by(email=email).scalar()

    existing = None
    if not fb_id_in_db and email_in_db:
        existing = session.query(User).filter_by(email=email).one()
        existing.fb_id = fb_id
    elif fb_id_in_db:
        existing = session.query(User).filter_by(fb_id=fb_id).one()

    if existing:
        flash('Welcome back, {}!'.format(existing.name))
        login_session['user_key'] = existing.key
        login_session['user_name'] = existing.name
        return make_response('Login successful', 200)

    name = ' '.join(info['name'].split(' ')[:-1])
    new_user = User(name=name, email=email, fb_id=fb_id)
    session.add(new_user)
    session.commit()
    flash('Thanks for joining, {}!'.format(new_user.name))
    login_session['user_key'] = new_user.key
    login_session['user_name'] = new_user.name
    return make_response('Registration successful', 200)


@oauth_blueprint.route('/gconnect', methods=['POST'])
def gconnect():
    '''Uses oauth2client library to exchange the authorization code for an
    access token, then logs in the user'''
    try:
        auth_code = request.form['code']
        #flow = flow_from_clientsecrets('/var/www/Venue-Catalog/g_client_secrets.json', scope='')
        flow = flow_from_clientsecrets('g_client_secrets.json', scope='')
        flow.redirect_uri = 'postmessage'
        credentials = flow.step2_exchange(auth_code)
    except FlowExchangeError:
        error_msg = 'Could not obtain and exchange the authorization code'
        flash(error_msg)
        return make_response(error_msg, 401)

    token = credentials.access_token
    auth_url = ('https://www.googleapis.com/oauth2/v3/tokeninfo?'
                'access_token={}').format(token)
    http = httplib2.Http()
    resp = http.request(auth_url, 'GET')
    if resp[0]['status'] != '200':
        error_msg = 'Login was aborted due to an invalid token'
        flash(error_msg)
        return make_response(error_msg, 401)

    data = json.loads(resp[1].decode())
    if data['aud'] != app.config['G_OAUTH_ID']:
        error_msg = 'Login was aborted due to an invalid client ID'
        flash(error_msg)
        return make_response(error_msg, 401)

    info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
    params = {'access_token': token, 'alt': 'json'}
    resp = requests.get(info_url, params=params)
    info = resp.json()

    login_session['token'] = token
    login_session['provider'] = 'google'
    login_session.permanent = True

    sub = data['sub']  # Unique facebook account identifier
    email = info['email']
    sub_in_db = session.query(User.sub).filter_by(sub=sub).scalar()
    email_in_db = session.query(User.email).filter_by(email=email).scalar()

    existing = None
    if not sub_in_db and email_in_db:
        existing = session.query(User).filter_by(email=email).one()
        existing.sub = sub
    elif sub_in_db:
        existing = session.query(User).filter_by(sub=sub).one()

    if existing:
        flash('Welcome back, {}!'.format(existing.name))
        login_session['user_key'] = existing.key
        login_session['user_name'] = existing.name
        return make_response('Login successful', 200)

    new_user = User(name=info['given_name'], email=email, sub=sub)
    session.add(new_user)
    session.commit()
    flash('Thanks for joining, {}!'.format(new_user.name))
    login_session['user_key'] = new_user.key
    login_session['user_name'] = new_user.name
    return make_response('Registration successful', 200)


@oauth_blueprint.route('/disconnect')
def disconnect():
    '''Deletes session data for the user, revoking permissions in effect'''
    try:
        del login_session['user_key']
        del login_session['user_name']
        del login_session['token']
        del login_session['provider']
        return make_response('Logout successful', 200)
    except KeyError:
        return make_response('User not connected', 500)
