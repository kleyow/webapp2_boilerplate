import sys


ZIP_LIBRARIES = ['library/babel.zip', 'library/keen.zip',
                 'library/pyhaml_jinja.zip', 'library/pytz.zip',
                 'library/requests.zip', 'library/stripe.zip',
                 'library/webapp2.zip', 'library/wtforms.zip', 'library/']


# Zipimport configuration:
def configure_libraries():
  sys.path.extend(ZIP_LIBRARIES)

  # Ensure no duplicates in the PYTHONPATH.
  sys.path = list(set(sys.path))

configure_libraries()

import logging
import os

from google.appengine.api import datastore_errors
from google.appengine.ext import db

from babel import localedata
from library import template_filters
from library.silent_undefined import SilentUndefined

STRIPE_PROD_KEY = 'sk_live_sfDg7fTDvU6s6y8ysZeUxZ4H'
STRIPE_TEST_KEY = 'sk_test_gkcZGfpbsGmPIqiSpvuBYN6B'

# Hack warning:
# Due to babel being zipped, we need to move locale data into
# a separate directory. This directory only has en_US locale.
localedata._dirname = os.path.join(os.path.dirname(__file__),
                                   'library', 'localedata')


# Hack warning:
# Due to App Engine's ReferenceProperty and possible integrity errors,
# we are going to blast out db.ReferenceProperty's __get__ method so that
# instead of errors, we get None and an error is LOGGED.
def safe_get(self, model_instance, model_class, *args, **kwargs):
  try:
    return self.unsafe_get(model_instance, model_class, *args, **kwargs)
  except datastore_errors.ReferencePropertyResolveError:
    logging.exception('Property "%s" for %s failed to be resolved' % (
                      self.name, model_instance.key().to_path()))
    return None

# Make sure that we only blast this method out once (otherwise we'll recurse
# infinitely.
safe_get.injected = True
if not hasattr(db.ReferenceProperty.__get__, 'injected'):
  db.ReferenceProperty.unsafe_get = db.ReferenceProperty.__get__
  db.ReferenceProperty.__get__ = safe_get


webapp2_config = {
    'webapp2_extras.sessions': {
        'secret_key': 'b256a592-5ebe-46a0-85d5-de92ef5023a2',
    },
    'webapp2_extras.jinja2': {
        'environment_args': {
            'undefined': SilentUndefined,
            'autoescape': True,
            'extensions': [
                'jinja2.ext.i18n',
                'pyhaml_jinja.HamlExtension',
            ],
        },
    },
}

# Automatically pull in all the filters defined in template_filters.__all__.
filters = {}
for func in template_filters.__all__:
  filters[func] = getattr(template_filters, func)
webapp2_config['webapp2_extras.jinja2']['filters'] = filters
