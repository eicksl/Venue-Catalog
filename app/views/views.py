#!/usr/bin/env python3

import json
import os

from flask import Blueprint, render_template, url_for, redirect, request
from flask import make_response, flash
from flask import session as login_session
from sqlalchemy import asc, desc
from datetime import datetime

from app import app, session
from app.models import User, Category, Venue, Activity
from app.validate import valid_image, validate_form, handle_image_upload
from app.search import get_coordinates, get_image, get_venues
from app.exceptions import UserKeyNotFound
from app.oauth.oauth import login_required, authorized


views_blueprint = Blueprint('views', __name__)


@app.route('/')
def show_catalog():
    '''Renders main page'''
    categories = session.query(Category).order_by(asc(Category.name))
    activity = session.query(Activity).order_by(desc(Activity.key))
    if activity.count() == 0:
        activity = None
    f_datetime = []
    if activity:
        for action in activity:
            dt_str = action.datetime.strftime('%m-%d-%y, %X')[:-3] + ' UTC'
            f_datetime.append(dt_str)

    return render_template('catalog.html', categories=categories,
                           activity=activity, f_datetime=f_datetime)


@app.route('/search')
def search():
    '''Makes calls with user input to Google Geocode and Foursquare APIs to
    retrieve a list of data about user-requested venues, then renders the
    search results template'''
    if request.args.get('offset') is None:
        offset = 0
    else:
        offset = request.args.get('offset')

    data = get_venues(request.args.get('query'), request.args.get('location'),
                      offset)
    if data is None:
        return redirect(url_for('show_catalog'))

    return render_template('search.html', data=data, offset=offset,
                           LIMIT=app.config['LIMIT'], location=request.args.get('location'),
                           query=request.args.get('query'))


@app.route('/login')
def show_login():
    '''Renders login page view'''
    return render_template('login.html')


@app.route('/add', methods=['POST'])
@login_required
def add_venue():
    '''Adds a new venue from the search results to the database'''
    venue = json.loads(request.form['venue'])

    q = session.query(Category.name).filter_by(name=venue['category']).scalar()
    if q is None:
        new_category = Category(name=venue['category'])
        session.add(new_category)

    q = session.query(Category.key).filter_by(name=venue['category']).scalar()
    category = venue['category']
    del venue['in_db'], venue['category']
    user_key = login_session['user_key']
    new_venue = Venue(user_key=user_key, category_key=q, **venue)
    session.add(new_venue)
    session.commit()
    new_activity(new_venue, 'added')

    flash('New venue {} added in category {}'.format(
          venue['name'], category))
    return redirect(url_for('show_catalog'))


@app.route('/new', methods=['GET', 'POST'])
@login_required
def add_custom_venue():
    '''Adds a new user-defined venue to the database'''
    if request.method == 'GET':
        return render_template('new.html')

    form_values = validate_form()
    if form_values:
        return render_template('new.html', venue=form_values)

    category = ' '.join(request.form['category'].title().split())
    if session.query(Category.name).filter_by(name=category).scalar() is None:
        new_category = Category(name=category)
        session.add(new_category)

    name = ' '.join(request.form['name'].title().split())
    q = session.query(Category.key).filter_by(name=category).scalar()
    user_key = login_session['user_key']
    new_venue = Venue(category_key=q, name=name, phone=request.form['phone'],
                      address=request.form['address'], user_key=user_key,
                      description=request.form['description'])
    session.add(new_venue)
    session.commit()

    if 'image' in request.files:
        new_venue.image = handle_image_upload(
            request.files['image'], new_venue.key)
        session.add(new_venue)
        session.commit()

    new_activity(new_venue, 'added')

    flash('New venue {} added in category {}'.format(new_venue.name, category))
    return redirect(url_for('show_catalog'))


@app.route('/category/<int:category_key>/venue/<int:venue_key>/edit',
           methods=['GET', 'POST'])
@login_required
def edit_venue(category_key, venue_key):
    '''Edits an existing venue in the database based on user input'''
    venue = session.query(Venue).filter_by(key=venue_key).one()
    if not authorized(venue.user_key):
        return make_response('Unauthorized User', 401)

    old_category_str = session.query(Category).filter_by(
        key=category_key).one().name

    if request.method == 'GET':
        return render_template('edit.html', venue=venue,
                               category_name=old_category_str)

    form_values = validate_form()
    if form_values:
        return render_template('edit.html', venue=form_values)

    new_category_str = ' '.join(request.form['category'].title().split())
    new_name_str = ' '.join(request.form['name'].title().split())

    # Delete and replace the category object if the category was edited AND
    # the venue we are editing is the only one in the category
    if (new_category_str != old_category_str
            and session.query(Venue).filter_by(
            category_key=category_key).count() == 1):
        old_category_obj = session.query(Category).filter_by(
            key=category_key).one()
        session.delete(old_category_obj)
        new_category_obj = Category(name=new_category_str)
        session.add(new_category_obj)
        venue.category_key = new_category_obj.key

    if 'image' in request.files:
        if venue.image and venue.image[:8] != 'https://':
            os.remove(app.config['UPLOAD_DIR'] + venue.image.replace('img/uploads/', '', 1))
        venue.image = handle_image_upload(request.files['image'], venue.key)

    venue.name = new_name_str
    venue.address = request.form['address']
    venue.phone = request.form['phone']
    venue.description = request.form['description']
    session.add(venue)
    session.commit()
    new_activity(venue, 'edited')

    flash('Venue successfully edited')
    return redirect(url_for('show_catalog'))


@app.route('/category/<int:category_key>/venue/<int:venue_key>/delete',
           methods=['GET', 'POST'])
@login_required
def delete_venue(category_key, venue_key):
    '''Deletes a venue from the database'''
    venue = session.query(Venue).filter_by(key=venue_key).one()
    if not authorized(venue.user_key):
        return make_response('Unauthorized User', 401)

    if request.method == 'GET':
        return render_template('delete.html', venue=venue)

    new_activity(venue, 'deleted')

    if session.query(Venue).filter_by(category_key=category_key).count() == 1:
        old_category_obj = session.query(Category).filter_by(
            key=category_key).one()
        session.delete(old_category_obj)

    if venue.image and venue.image[:8] != 'https://':
        os.remove(app.config['UPLOAD_DIR'] + venue.image.replace('img/uploads/', '', 1))

    session.delete(venue)
    session.commit()

    flash('Venue successfully deleted')
    return redirect(url_for('show_catalog'))


@app.route('/category/<int:category_key>')
def show_venues(category_key):
    '''Renders the venues.html template which displays the list of venues
    in the database for a particular category'''
    categories = session.query(Category).order_by(asc(Category.name))
    venues = session.query(Venue).filter_by(
             category_key=category_key).order_by(asc(Venue.name))
    return render_template('venues.html', categories=categories, venues=venues,
                           category_key=category_key)


@app.route('/category/<int:category_key>/venue/<int:venue_key>')
def show_info(category_key, venue_key):
    '''Renders the info.html template which displays all available information
    about a particular venue in the database'''
    venue = session.query(Venue).filter_by(key=venue_key).one()
    return render_template('info.html', venue=venue)


def new_activity(venue, action):
    '''Takes in a venue object and a string for the action performed and
    instantiates a new activity object. Deletes the oldest row if the count
    is greater than or equal to RECENTS.'''
    if not venue.user_key:
        raise UserKeyNotFound()

    if session.query(Activity).count() >= app.config['RECENTS']:
        oldest = session.query(Activity).order_by(
            asc(Activity.datetime)).first()
        session.delete(oldest)
        session.commit()

    user_name = session.query(User.name).filter_by(key=venue.user_key).scalar()
    dt = datetime.utcnow()

    activity = Activity(
        user_name=user_name,
        action=action,
        venue_name=venue.name,
        datetime=dt
    )
    if action != 'deleted':
        activity.category_key = venue.category_key
        activity.venue_key = venue.key
    else:
        previous = session.query(Activity).filter_by(venue_key=venue.key).all()
        for entry in previous:
            entry.venue_key = None

    session.add(activity)
    session.commit()
