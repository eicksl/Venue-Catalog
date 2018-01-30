from flask import Flask, render_template, url_for, flash, abort
from flask import request, make_response, redirect, jsonify
from flask import session as login_session
from sqlalchemy import create_engine, inspect, asc, desc
from sqlalchemy.orm import sessionmaker
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
from datetime import datetime
from functools import wraps
from models import Base, User, Category, Venue, Activity
from exceptions import UserKeyNotFound
import json
import requests
import os
import random
import string
import httplib2


G_OAUTH_ID = ('441640703458-8gb39d0jqjk9s0khrhdfhj8kutnnekpg.apps'
              '.googleusercontent.com')
UPLOAD_DIR = '/var/www/Venue-Catalog/static/img/uploads/'
ALLOWED_EXT = set(['png', 'jpg', 'jpeg', 'gif', 'apng', 'bmp', 'svg'])
CLIENT_ID = 'X51LXWV4BDKANESBY1PCWEG2XDDG4FW0PTWFWOGXX0YTO5EL'
CLIENT_SECRET = 'Q4EWJUPCQM114AESG5VKYLVLGRVZLDFW1OA3KPERTMIP2R02'
RECENTS = 10  # A limit set on the number of rows in the Activity model, which
# is also the number of entries shown on the main page for recent activity.
LIMIT = 11   # LIMIT-1 results are shown on the search page. An extra item
# is used to indicate whether there are more results to display.

app = Flask(__name__)
app.config['UPLOAD_DIR'] = UPLOAD_DIR
engine = create_engine('postgresql://cataloguser:password@localhost/catalogdb')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


def login_required(login):
    @wraps(login)
    def check_login_status(*args, **kwargs):
        if 'user_key' in login_session:
            return login(*args, **kwargs)
        else:
            return redirect('/login')
    return check_login_status


def get_random_string():
    '''Generates a random 32-character string comprised of uppercase ASCII
    characters and digits'''
    return ''.join(random.choice(string.ascii_uppercase + string.digits)
                   for x in range(32))


@app.route('/fbconnect', methods=['POST'])
def fbconnect():
    '''Exchanges short term token for long term one, then logs in the user'''
    short_term_token = request.form['token']
    app_id = json.loads(open(
        '/var/www/Venue-Catalog/fb_client_secrets.json', 'r').read())['web']['app_id']
    app_secret = json.loads(open(
        '/var/www/Venue-Catalog/fb_client_secrets.json', 'r').read())['web']['app_secret']
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


@app.route('/gconnect', methods=['POST'])
def gconnect():
    '''Uses oauth2client library to exchange the authorization code for an
    access token, then logs in the user'''
    try:
        auth_code = request.form['code']
        flow = flow_from_clientsecrets('/var/www/Venue-Catalog/g_client_secrets.json', scope='')
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
    if data['aud'] != G_OAUTH_ID:
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


@app.route('/disconnect')
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
        if index == LIMIT - 1:
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


def valid_image(image):
    '''Checks if image exists and has an allowed extension. Returns True
    if no image exists.'''
    if not image:
        return True
    else:
        return '.' in image.filename and \
               image.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT


def validate_form():
    '''If the form fields are valid, it will return None. Otherwise it will
    return a dictionary of the form values. This is to save the user from
    having to re-input values in an incorrectly submitted form.'''
    image = request.files.get('image', None)
    image_is_valid = valid_image(image)

    if (not request.form['category'] or not request.form['name']
            or not image_is_valid):
        if not request.form['category'] or not request.form['name']:
            flash('Category and Name fields are required.')
        if not image_is_valid:
            flash('Unsupported file extension.')
        venue = {}
        info = ['category', 'name', 'address', 'phone', 'description']
        for index in info:
            if request.form[index]:
                venue[index] = request.form[index]
        if not venue:
            return True  # All fields are empty. Redirect to the form's URI.
        return venue
    else:
        return None


def handle_image_upload(image, venue_key):
    '''If the image exists, it saves it to the server and returns the path
    from the static directory. Otherwise returns None.'''
    if not image:
        return None

    ext = image.filename.rsplit('.', 1)[1].lower()
    filename = str(venue_key) + '.' + ext
    path_from_main = UPLOAD_DIR + filename
    #path_from_static = UPLOAD_DIR.replace('static/', '', 1) + filename
    path_from_static = 'img/uploads/' + filename
    image.save(path_from_main)
    image.close()

    return path_from_static


def new_activity(venue, action):
    '''Takes in a venue object and a string for the action performed and
    instantiates a new activity object. Deletes the oldest row if the count
    is greater than or equal to RECENTS.'''
    if not venue.user_key:
        raise UserKeyNotFound()

    if session.query(Activity).count() >= RECENTS:
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
        if entry in previous:
            entry.venue_key = None

    session.add(activity)
    session.commit()


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


@app.template_filter('authorized')
def authorized(venue_user_key):
    '''Returns True if the user key in the flask session matches the venue's
    user key, else returns False'''
    if 'user_key' in login_session and login_session['user_key'] == venue_user_key:
        return True
    else:
        return False


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
            os.remove('static/' + venue.image)
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
        os.remove('static/' + venue.image)

    session.delete(venue)
    session.commit()

    flash('Venue successfully deleted')
    return redirect(url_for('show_catalog'))


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
        del data[LIMIT - 1]
    except IndexError:
        pass

    return jsonify(data)


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
                           LIMIT=LIMIT, location=request.args.get('location'),
                           query=request.args.get('query'))


@app.route('/category/<int:category_key>/json')
def show_venues_json(category_key):
    '''Sends a JSON-formatted response containing venue data for a particular
    category'''
    venues = session.query(Venue).filter_by(category_key=category_key).all()
    return jsonify([i.serialize for i in venues])


@app.route('/category/<int:category_key>')
def show_venues(category_key):
    '''Renders the venues.html template which displays the list of venues
    in the database for a particular category'''
    categories = session.query(Category).order_by(asc(Category.name))
    venues = session.query(Venue).filter_by(
             category_key=category_key).order_by(asc(Venue.name))
    return render_template('venues.html', categories=categories, venues=venues,
                           category_key=category_key)


@app.route('/category/<int:category_key>/venue/<int:venue_key>/json')
def show_info_json(category_key, venue_key):
    '''Sends a JSON-formatted response with all available information about
    a particular venue in the database'''
    venue = session.query(Venue).filter_by(key=venue_key).one()
    return jsonify(venue.serialize)


@app.route('/category/<int:category_key>/venue/<int:venue_key>')
def show_info(category_key, venue_key):
    '''Renders the info.html template which displays all available information
    about a particular venue in the database'''
    venue = session.query(Venue).filter_by(key=venue_key).one()
    return render_template('info.html', venue=venue)


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


app.jinja_env.globals['get_csrf_token'] = get_csrf_token
app.secret_key = get_random_string()

if __name__ == '__main__':
    app.jinja_env.globals['get_csrf_token'] = get_csrf_token
    app.secret_key = get_random_string()
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
