#!/usr/bin/env python3

from flask import Blueprint, jsonify, request, make_response

from app import app, session
from app.models import Category, Venue, Activity
from app.search import get_coordinates, get_image, get_venues


api_blueprint = Blueprint('api', __name__)


@app.route('/activity')
@app.route('/activity/json')
def activity_json():
    '''Sends a JSON-formatted response containing data about the most recent
    user activity'''
    activity = session.query(Activity).all()
    return jsonify([i.serialize for i in activity])


@app.route('/json')
def show_catalog_json():
    '''Sends a JSON-formatted response containing data about all categories
    in the database'''
    categories = session.query(Category).all()
    return jsonify([i.serialize for i in categories])


@app.route('/search/json')
def search_json():
    '''Makes calls with user input to Google Geocode and Foursquare APIs to
    retrieve a list of data about user-requested venues, then sends the data
    as a JSON-formatted response'''
    if request.args.get('offset') is None:
        offset = 0
    else:
        offset = request.args.get('offset')

    data = get_venues(request.args.get('query'), request.args.get('location'),
                      offset)
    if data is None:
        error_msg = 'Either an error occurred while processing the request or \
                     there are no results to display for the given parameters.'
        return make_response(error_msg, 404)

    try:
        del data[app.config['LIMIT'] - 1]
    except IndexError:
        pass

    return jsonify(data)


@app.route('/category/<int:category_key>/json')
def show_venues_json(category_key):
    '''Sends a JSON-formatted response containing venue data for a particular
    category'''
    venues = session.query(Venue).filter_by(category_key=category_key).all()
    return jsonify([i.serialize for i in venues])


@app.route('/category/<int:category_key>/venue/<int:venue_key>/json')
def show_info_json(category_key, venue_key):
    '''Sends a JSON-formatted response with all available information about
    a particular venue in the database'''
    venue = session.query(Venue).filter_by(key=venue_key).one()
    return jsonify(venue.serialize)
