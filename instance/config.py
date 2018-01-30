#!/usr/bin/env python3

DATABASE_URI = 'postgresql://cataloguser:password@localhost/catalogdb'
#DATABASE_URI = 'sqlite:///venue.db'
G_OAUTH_ID = ('441640703458-8gb39d0jqjk9s0khrhdfhj8kutnnekpg.apps'
              '.googleusercontent.com')
UPLOAD_DIR = '/var/www/Venue-Catalog/app/static/img/uploads/'
#UPLOAD_DIR = 'app/static/img/uploads/'
ALLOWED_EXT = set(['png', 'jpg', 'jpeg', 'gif', 'apng', 'bmp', 'svg'])
CLIENT_ID = 'X51LXWV4BDKANESBY1PCWEG2XDDG4FW0PTWFWOGXX0YTO5EL'
CLIENT_SECRET = 'Q4EWJUPCQM114AESG5VKYLVLGRVZLDFW1OA3KPERTMIP2R02'
RECENTS = 10  # A limit set on the number of rows in the Activity model, which
# is also the number of entries shown on the main page for recent activity.
LIMIT = 11   # LIMIT-1 results are shown on the search page. An extra item
# is used to indicate whether there are more results to display.
