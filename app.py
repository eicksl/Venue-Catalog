from flask import Flask, render_template, url_for, request, flash
from flask import jsonify, redirect
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db_setup import Base, City, Venue
import json, requests, httplib2


app = Flask(__name__)
engine = create_engine('sqlite:///venue.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

CLIENT_ID = 'X51LXWV4BDKANESBY1PCWEG2XDDG4FW0PTWFWOGXX0YTO5EL'
CLIENT_SECRET = 'Q4EWJUPCQM114AESG5VKYLVLGRVZLDFW1OA3KPERTMIP2R02'


def get_coordinates(location):
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
        return None


def get_image(venue_api_id):
    photo_url = ('https://api.foursquare.com/v2/'
                 'venues/{}/photos').format(venue_api_id)
    photo_params = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'v': '20170801'
    }
    p_resp = requests.get(photo_url, photo_params)
    p_data = json.loads(p_resp.text)
    if p_data['response']['photos']['items']:
        prefix = p_data['response']['photos']['items'][0]['prefix']
        suffix = p_data['response']['photos']['items'][0]['suffix']
        image_url = prefix + '300x300' + suffix
        return image_url
    else:
        return None


def get_venues(query, location, offset=0):
    # RESULTS NEEDED: Name, Address, Phone, Description, Photo
    LIMIT = 11
    results = []
    coordinates = get_coordinates(location)
    if not coordinates:
        return None
    url = 'https://api.foursquare.com/v2/venues/explore'
    params = {
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
        'v': '20170801',
        'll': coordinates,
        'query': query,
        'limit': LIMIT,
        'offset': offset
    }
    resp = requests.get(url, params)
    data = json.loads(resp.text)

    num_of_venues = len(data['response']['groups'][0]['items'])
    if num_of_venues == 0:
        return None

    for index in range(num_of_venues):
        if index == LIMIT-1:
            results.append('LIMIT')
            break
        info = {}
        venue = data['response']['groups'][0]['items'][index]['venue']
        info['name'] = venue['name']
        info['phone'] = venue['contact']['formattedPhone']
        address = venue['location']['formattedAddress']
        info['address'] = '\n'.join(address)
        try:
            info['description'] = (data['response']['groups'][0]
                                        ['items'][index]['tips'][0]['text'])
        except (KeyError, IndexError):
            pass
        info['image'] = get_image(venue['id'])

        results.append(info)

    return results


@app.route('/', methods=['GET','POST'])
def catalog():
    if request.method == 'POST':
        return redirect(url_for('search'), data=data,
            query=request.form['query'], location=request.form['location'])
    else:
        return render_template('main.html')


@app.route('/search')
def search():
    data = get_venues(request.args.get('query'), request.args.get('location'))
    if data is None:
        flash('No results found. Please try modifying your search.')
        return redirect(url_for('catalog'))

    return render_template('search.html', data=data,
        location=request.args.get('location'), query=request.args.get('query'))


if __name__ == '__main__':
    app.secret_key = 'ROFLMAO'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
