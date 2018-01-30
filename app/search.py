#!/usr/bin/env python3

import requests, json
from flask import flash
from app import app, session
from app.models import Venue


def get_coordinates(location):
    '''Takes in a location string and uses the Google Geocode API to return
    a string of coordinates for the location'''
    GOOGLE_API_KEY = 'AIzaSyAQCG4wcNxQHbYQ9WYstLWVb03HC_lDKeI'
    url = 'https://maps.googleapis.com/maps/api/geocode/json'
    params = {'key': GOOGLE_API_KEY, 'address': location}
    resp = requests.get(url, params)
    data = json.loads(resp.text)
    try:
        latitude = data['results'][0]['geometry']['location']['lat']
        longitude = data['results'][0]['geometry']['location']['lng']
        return str(latitude) + ',' + str(longitude)
    except (KeyError, IndexError):
        flash('No results found. Please try modifying your search.')
        return None


def get_image(venue_api_id):
    '''Uses the Foursquare API to retrieve an image of a venue based on the
    venue's ID as defined in the API'''
    photo_url = ('https://api.foursquare.com/v2/'
                 'venues/{}/photos').format(venue_api_id)
    photo_params = {
        'client_id': app.config['CLIENT_ID'],
        'client_secret': app.config['CLIENT_SECRET'],
        'v': '20170801'
    }
    p_resp = requests.get(photo_url, photo_params)
    p_data = json.loads(p_resp.text)
    try:
        prefix = p_data['response']['photos']['items'][0]['prefix']
        suffix = p_data['response']['photos']['items'][0]['suffix']
        image_url = prefix + '300x300' + suffix
        return image_url
    except (KeyError, IndexError):
        return None


def get_venues(query, location, offset=0):
    '''Uses the Foursquare API to retrieve data about nearby venues based
    on a query and location. Returns a list of dictionaries.'''
    results = []
    coordinates = get_coordinates(location)

    if not coordinates:
        return None

    url = 'https://api.foursquare.com/v2/venues/explore'
    params = {
        'client_id': app.config['CLIENT_ID'],
        'client_secret': app.config['CLIENT_SECRET'],
        'v': '20170801',
        'll': coordinates,
        'query': query,
        'limit': app.config['LIMIT'],
        'offset': offset
    }
    resp = requests.get(url, params)
    data = json.loads(resp.text)

    if data['meta']['code'] != 200:
        flash('An error occurred while processing the request.')
        return None

    num_of_venues = len(data['response']['groups'][0]['items'])
    if num_of_venues == 0:
        flash('No results found. Please try modifying your search.')
        return None

    for index in range(num_of_venues):
        if index == app.config['LIMIT'] - 1:
            results.append('LIMIT')   # Template displays URL to more results
            break                     # when this index exists
        info = {}
        venue = data['response']['groups'][0]['items'][index]['venue']
        info['api_id'] = venue['id']
        info['name'] = venue['name']
        try:
            info['category'] = venue['categories'][0]['pluralName']
        except (KeyError, IndexError):
            info['category'] = 'Unknown'
        try:
            info['phone'] = venue['contact']['formattedPhone']
        except (KeyError):
            pass
        try:
            address = venue['location']['formattedAddress']
            info['address'] = '\n'.join(address)
        except (KeyError):
            pass
        try:
            info['description'] = (data['response']['groups'][0]
                                   ['items'][index]['tips'][0]['text'])
        except (KeyError, IndexError):
            pass
        info['image'] = get_image(venue['id'])

        q = session.query(Venue.api_id).filter_by(
            api_id=info['api_id']).scalar()
        if q is None:
            info['in_db'] = False
        else:
            info['in_db'] = True

        results.append(info)

    return results
