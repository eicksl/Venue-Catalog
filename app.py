from flask import Flask, render_template, url_for, request, flash
from flask import jsonify, redirect
from sqlalchemy import create_engine, inspect, asc
from sqlalchemy.orm import sessionmaker
from db_setup import Base, Category, Venue
import json, requests, httplib2, os


app = Flask(__name__)
#app.jinja_env.add_extension('jinja2.ext.loopcontrols')
engine = create_engine('sqlite:///venue.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()

CLIENT_ID = 'X51LXWV4BDKANESBY1PCWEG2XDDG4FW0PTWFWOGXX0YTO5EL'
CLIENT_SECRET = 'Q4EWJUPCQM114AESG5VKYLVLGRVZLDFW1OA3KPERTMIP2R02'
LIMIT = 11


@app.context_processor
def override_url_for():
    '''Cache buster; see http://flask.pocoo.org/snippets/40'''
    return dict(url_for=dated_url_for)


def dated_url_for(endpoint, **values):
    '''Cache buster; see http://flask.pocoo.org/snippets/40'''
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(app.root_path,
                                     endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)


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
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET,
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

    if data['meta']['code'] != 200:
        flash('An error occurred while processing the request.')
        return None

    num_of_venues = len(data['response']['groups'][0]['items'])
    if num_of_venues == 0:
        flash('No results found. Please try modifying your search.')
        return None

    for index in range(num_of_venues):
        if index == LIMIT-1:
            results.append('LIMIT')
            break
        info = {}
        venue = data['response']['groups'][0]['items'][index]['venue']
        info['api_id'] = venue['id']
        info['category'] = venue['categories'][0]['pluralName']
        info['name'] = venue['name']
        try:
            info['phone'] = venue['contact']['formattedPhone']
        except KeyError:
            pass
        try:
            address = venue['location']['formattedAddress']
        except KeyError:
            pass
        info['address'] = '\n'.join(address)
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


@app.route('/add', methods=['POST'])
def add_venue():
    venue = json.loads(request.form['venue'])

    q = session.query(Category.name).filter_by(name=venue['category']).scalar()
    if q is None:
        new_category = Category(name=venue['category'])
        session.add(new_category)

    q = session.query(Category.key).filter_by(name=venue['category']).scalar()
    del venue['in_db'], venue['category']
    new_venue = Venue(category_key=q, **venue)
    session.add(new_venue)
    session.commit()

    flash('New venue {} added in category {}'.format(
          venue['name'], venue['category']))
    return redirect(url_for('show_catalog'))


@app.route('/new', methods=['GET','POST'])
def add_custom_venue():
    if request.method == 'GET':
        return render_template('new.html')

    if not request.form['category'] or not request.form['name']:
        flash('Category and Name fields are required.')
        return redirect(url_for('add_custom_venue'))

    category = ' '.join(request.form['category'].title().split())
    if session.query(Category.name).filter_by(name=category).scalar() is None:
        new_category = Category(name=category)
        session.add(new_category)

    name = ' '.join(request.form['name'].title().split())
    q = session.query(Category.key).filter_by(name=category).scalar()
    new_venue = Venue(category_key=q, name=name, phone=request.form['phone'],
                address=request.form['address'],
                description=request.form['description'])
    session.add(new_venue)
    session.commit()

    flash('New venue {} added in category {}'.format(new_venue.name, category))
    return redirect(url_for('show_catalog'))


@app.route('/category/<int:category_key>/venue/<int:venue_key>/edit',
            methods=['GET','POST'])
def edit_venue(category_key, venue_key):
    venue = session.query(Venue).filter_by(key=venue_key).one()
    old_category_str = session.query(Category).filter_by(
                       key=category_key).one().name

    if request.method == 'GET':
        return render_template('edit.html', venue=venue,
               category_name=old_category_str)

    if not request.form['category'] or not request.form['name']:
        flash('Category and Name fields are required.')
        return redirect(url_for('edit_venue'))

    new_category_str = ' '.join(request.form['category'].title().split())
    new_name_str = ' '.join(request.form['name'].title().split())

    # Delete and replace the category object if the category was edited AND
    # the venue we are editing is the only one in the category
    if (new_category_str != old_category_str
    and session.query(Venue).filter_by(category_key=category_key).count() == 1):
        old_category_obj = session.query(Category).filter_by(
                           key=category_key).one()
        session.delete(old_category_obj)
        new_category_obj = Category(name=new_category_str)
        session.add(new_category_obj)
        venue.category_key = new_category_obj.key

    venue.name = new_name_str
    venue.address = request.form['address']
    venue.phone = request.form['phone']
    venue.description = request.form['description']
    session.add(venue)
    session.commit()

    flash('Venue successfully edited')
    return redirect(url_for('show_catalog'))


@app.route('/category/<int:category_key>/venue/<int:venue_key>/delete',
            methods=['GET','POST'])
def delete_venue(category_key, venue_key):
    venue = session.query(Venue).filter_by(key=venue_key).one()

    if request.method == 'GET':
        return render_template('delete.html', venue=venue)

    if session.query(Venue).filter_by(category_key=category_key).count() == 1:
        old_category_obj = session.query(Category).filter_by(
                           key=category_key).one()
        session.delete(old_category_obj)

    session.delete(venue)
    session.commit()

    flash('Venue successfully deleted')
    return redirect(url_for('show_catalog'))


@app.route('/', methods=['GET','POST'])
def show_catalog():
    if request.method == 'POST':
        return redirect(url_for('search'), query=request.form['query'],
               location=request.form['location'])

    categories = session.query(Category).order_by(asc(Category.name))
    venues = session.query(Venue).order_by(asc(Venue.name))

    return render_template('catalog.html', categories=categories, venues=venues)


@app.route('/search')
def search():
    if request.args.get('offset') is None:
        offset = 0
    else:
        offset = request.args.get('offset')

    data = get_venues(request.args.get('query'), request.args.get('location'),
           offset)
    if data is None:
        return redirect(url_for('show_catalog'))

    return render_template('search.html', data=data, offset=offset, LIMIT=LIMIT,
        location=request.args.get('location'), query=request.args.get('query'))


@app.route('/category/<int:category_key>')
def show_venues(category_key):
    categories = session.query(Category).order_by(asc(Category.name))
    venues = session.query(Venue).filter_by(category_key=category_key).order_by(
             asc(Venue.name))
    return render_template('venues.html', categories=categories, venues=venues)


@app.route('/category/<int:category_key>/venue/<int:venue_key>')
def show_info(category_key, venue_key):
    venue = session.query(Venue).filter_by(key=venue_key).one()
    return render_template('info.html', venue=venue)


if __name__ == '__main__':
    app.secret_key = 'ROFLMAO'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
