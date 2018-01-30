#!/usr/bin/env python3

from flask import flash, request
from app import app


def valid_image(image):
    '''Checks if image exists and has an allowed extension. Returns True
    if no image exists.'''
    if not image:
        return True
    else:
        return '.' in image.filename and \
            image.filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXT']


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
    path_from_main = app.config['UPLOAD_DIR'] + filename
    #path_from_static = 'img/uploads/' + filename
    path_from_static = app.config['UPLOAD_DIR'].replace('app/static/', '', 1) + filename
    image.save(path_from_main)
    image.close()

    return path_from_static
