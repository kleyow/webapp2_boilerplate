import uuid


class CSRF(object):
  CSRF_TOKEN_KEY = '_csrf_token'

  def __init__(self, request_handler):
    self.request_handler = request_handler

  @property
  def request(self):
    return self.request_handler.request

  @property
  def session(self):
    return self.request_handler.session

  def initialize_token(self):
    csrf_token = self.get_current_token()
    if not csrf_token:
      self.set_current_token(self.generate_token())

  def expire_token(self):
    if self.CSRF_TOKEN_KEY in self.session:
      del self.session[self.CSRF_TOKEN_KEY]

  def generate_token(self):
    return str(uuid.uuid4())

  def set_current_token(self, token):
    self.session[self.CSRF_TOKEN_KEY] = token

  def get_current_token(self):
    return self.session.get(self.CSRF_TOKEN_KEY)

  def get_provided_token(self):
    return self.request.get(self.CSRF_TOKEN_KEY)

  def token_required(self):
    if self.request_handler.is_taskqueue_request():
      return False
    elif self.request_handler.is_cron_request():
      return False
    elif self.request_handler.is_inbound_mail_request():
      return False
    else:
      return self.request.method == 'POST'

  def token_is_valid(self):
    return self.get_provided_token() == self.get_current_token()
