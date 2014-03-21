import logging
import os
import types

from google.appengine.api import mail
from google.appengine.api import memcache
from google.appengine.ext import db, deferred
import webapp2
from webapp2_extras import auth
from webapp2_extras import i18n
from webapp2_extras import jinja2
from webapp2_extras import sessions

import config
from library import analytics
from library import constants
from library import csrf
from library.auth import (admin_required, login_not_required, login_required,
                          staff_required)
from models.profile import Profile
from models.staff import Staff


class BaseHandlerMeta(type):
  """Meta class for all request handlers.

  This automatically wraps all handler methods with the login_required
  decorator. If something should be exposed publicly, it should be wrapped
  with the login_not_required decorator.
  """

  def __new__(cls, name, bases, local):
    if name != 'BaseHandler':
      for func_name, func in local.iteritems():
        if isinstance(func, types.FunctionType):
          local[func_name] = login_required(func)

    return type.__new__(cls, name, bases, local)


class BaseAdminHandlerMeta(BaseHandlerMeta):
  """Metaclass for AdminHandler to ensure that each handler method is wrapped
  with the admin_required decorator."""

  def __new__(cls, name, bases, local):
    if name != 'BaseHandler':
      for func_name, func in local.iteritems():
        if isinstance(func, types.FunctionType):
          local[func_name] = admin_required(func)

    return type.__new__(cls, name, bases, local)


class BaseStaffHandlerMeta(BaseHandlerMeta):
  """Metaclass for StaffHandler to ensure that each handler method is wrapped
  with the staff_required decorator."""

  def __new__(cls, name, bases, local):
    if name != 'BaseHandler':
      for func_name, func in local.iteritems():
        if isinstance(func, types.FunctionType):
          local[func_name] = staff_required(func)

    return type.__new__(cls, name, bases, local)


class BaseHandler(webapp2.RequestHandler):
  """Base class for all RequestHandlers.

  Provides several helper methods for templating, authentication, and
  data access.
  """

  __metaclass__ = BaseHandlerMeta

  @webapp2.cached_property
  def i18n(self):
    return i18n.get_i18n()

  @webapp2.cached_property
  def jinja2(self):
    # Configure i18n whenever we are using jinja2 to render a template.
    if self.get_current_profile():
      self.i18n.set_timezone(str(self.get_current_profile().get_timezone()))
    return jinja2.get_jinja2(app=self.app)

  @webapp2.cached_property
  def analytics(self):
    return analytics.Analytics(self)

  @webapp2.cached_property
  def auth(self):
    return auth.get_auth()

  @webapp2.cached_property
  def csrf(self):
    return csrf.CSRF(self)

  @webapp2.cached_property
  def session(self):
    return self.session_store.get_session()

  def dispatch(self):
    """Override dispatch to initialize and persist session data."""
    self.session_store = sessions.get_store(request=self.request)

    self.csrf.initialize_token()

    if self.csrf.token_required():
      if not self.csrf.token_is_valid():
        logging.warn('A CSRF token was required for this request, but it was '
                     'invalid or missing!')

      self.csrf.expire_token()

    try:
      super(BaseHandler, self).dispatch()
    finally:
      self.session_store.save_sessions(self.response)

  def redirect_back(self, default=None):
    if not default:
      default = self.uri_for('home')

    redirect = self.request.referrer or default
    return self.redirect(redirect)

  def render_template(self, template, context=None):
    """Renders the template with the provided context (optional)."""
    context = context or {}

    extra_context = {
        'analytics': self.analytics,
        'constants': constants,
        'csrf': self.csrf,
        'current_profile': self.get_current_profile(),
        'current_staff': self.get_current_staff(),
        'request': self.request,
        'session': self.session,
        'uri_for': self.uri_for}

    # Only override extra context stuff if it's not set by the template:
    for key, value in extra_context.items():
      if key not in context:
        context[key] = value

    return self.jinja2.render_template(template, **context)

  def render_to_response(self, template, context=None, use_cache=False):
    """Renders the template and writes the result to the response."""

    if use_cache:
      # Use the request's path to store the contents.

      # WARNING: This could cause scary problems if you render
      # user-specific pages.
      # DO NOT use current_profile in a template rendered with use_cache=True.
      cache_key = self.request.path
      contents = memcache.get(cache_key)

      if not contents or 'flushcache' in self.request.arguments():
        contents = self.render_template(template, context)

        # If add() returns False, it means another request is already trying
        # to cache the page. No need to do anything here.
        if memcache.add('lock.%s' % cache_key, True):
          memcache.set(cache_key, contents)
          memcache.delete('lock.%s' % cache_key)

    else:
      contents = self.render_template(template, context)

    self.response.write(contents)

  def get_current_profile(self):
    user = self.auth.get_user_by_session()
    if user:
      return Profile.get_by_auth_user_id(user['user_id'])

  def get_current_staff(self):
    """Retrieves the current staff member from the session.

    Since we're not using webapp2's auth to handle staff authentication, we
    can use this to ensure that a staff member is logged in."""

    if 'staff_key' in self.session:
      try:
        staff = Staff.get(self.session['staff_key'])
      except db.BadKeyError:
        staff = None

      return staff

  @login_not_required
  def get_stripe_api_key(self):
    if self.is_devappserver_request():
      logging.info('Using Stripe TEST key: %s' % config.STRIPE_TEST_KEY)
      return config.STRIPE_TEST_KEY
    else:
      logging.info('Using Stripe PROD key: %s' % config.STRIPE_PROD_KEY)
      return config.STRIPE_PROD_KEY

  def is_cron_request(self):
    return self.request.headers.get('X-Appengine-Cron') == 'true'

  def is_taskqueue_request(self):
    return 'X-AppEngine-QueueName' in self.request.headers

  def is_devappserver_request(self):
    return os.environ.get('APPLICATION_ID', '').startswith('dev~')

  def is_inbound_mail_request(self):
    return self.request.path.startswith('/_ah/mail/')

  def send_mail(self, profile, subject, template, context=None, sender=None,
                reply_to=None, defer=True):
    """Send an e-mail message to a profile with the appropriate template.

    Args:
      profile: models.profile.Profile object of the recipient.
      subject: string subject for the e-mail
      template: string HTML template to render as the e-mail.
      context: (optional) dict of context to apply to the template.
    """
    context = context or {}

    # Provide the current_profile and current_account context by default.
    base_context = {'current_profile': profile}

    # Only add base context values if they don't conflict with the context
    # provided.
    for key, value in base_context.items():
      if key not in context:
        context[key] = value

    # TODO: Use splitext for this piece.
    if template.endswith('haml'):
      html_template = template
      body_template = html_template[:-4] + 'txt'
    elif template.endswith('txt'):
      body_template = template
      html_template = template[:-3] + 'haml'
    else:
      raise ValueError('Invalid template: %s' % template)

    if not sender:
      sender = constants.FULL_NO_REPLY_EMAIL

    if not reply_to:
      reply_to = constants.FULL_SUPPORT_EMAIL

    mail_kwargs = {'body': self.render_template(body_template, context),
                   'html': self.render_template(html_template, context),
                   'to': '"%s" <%s>' % (profile.name, profile.email),
                   'bcc': constants.FULL_LOGS_EMAIL,
                   'sender': sender, 'reply_to': reply_to, 'subject': subject}

    logging.info('Sending e-mail to: %(to)s with subject: %(subject)s' %
                 mail_kwargs)

    if defer:
      deferred.defer(mail.send_mail, _queue='mail', _target='mail',
                     **mail_kwargs)
    else:
      mail.send_mail(**mail_kwargs)


class BaseAdminHandler(BaseHandler):

  __metaclass__ = BaseAdminHandlerMeta


class BaseStaffHandler(BaseHandler):

  __metaclass__ = BaseStaffHandlerMeta
