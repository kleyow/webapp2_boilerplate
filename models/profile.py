from datetime import datetime
import uuid

from google.appengine.ext import db
import pytz
from webapp2_extras import auth, security

from library import constants
from models.funding_source import FundingSource


class Profile(db.Model):
  """Stores a user's non-auth data.
  The Profile model represents a Blaze user.
  Their basic information (name, email address, timezone, etc.), and balance
  information (USD and JMD balances) are represented here.

  NOTE: To get the user's balance, use models.Profile.get_balance(currency)
  instead of accessing usd_balance and jmd_balance directly, and to set the
  user's balance, use models.Profile.increment_balance(currency, amount).
  To decrease a user's balance, pass a negative amount to increment_balance."""

  DEFAULT_TIMEZONE = 'America/Jamaica'

  # Tie back to webapp2 auth.
  auth_user_id = db.IntegerProperty()

  # Administrative details.
  created = db.DateProperty(auto_now_add=True)
  is_admin = db.BooleanProperty(default=False)
  beta_tester = db.BooleanProperty(default=False)

  # Basic details.
  name = db.StringProperty()
  email = db.EmailProperty()
  pin = db.StringProperty()
  timezone = db.StringProperty()
  activated = db.BooleanProperty(default=False)
  activation_key = db.StringProperty()

  # Book-keeping info.
  jmd_balance = db.IntegerProperty(default=0)
  usd_balance = db.IntegerProperty(default=0)

  @classmethod
  def get_by_email(cls, email):
    return cls.all().filter('email =', email).get()

  @classmethod
  def get_by_activation_key(cls, activation_key):
    return cls.all().filter('activation_key =', activation_key).get()

  @classmethod
  def get_by_auth_user_id(cls, id):
    return cls.all().filter('auth_user_id =', id).get()

  def set_pin(self, raw_pin, put=False):
    if not isinstance(raw_pin, basestring):
      raise TypeError('Expected string, got %s.' % type(raw_pin))

    self.pin = security.generate_password_hash(raw_pin, length=12)

    if put:
      self.put()

  def check_pin(self, raw_pin):
    return security.check_password_hash(str(raw_pin), self.pin)

  def get_auth_user(self):
    return auth.get_auth().store.user_model.get_by_id(self.auth_user_id)

  def get_timezone(self):
    return pytz.timezone(self.timezone or self.DEFAULT_TIMEZONE)

  def get_current_time(self):
    utc_now = pytz.utc.localize(datetime.utcnow())
    return utc_now.astimezone(self.get_timezone())

  def get_funding_sources(self, status=None):
    sources = FundingSource.all().ancestor(self)

    if status:
      sources = sources.filter('status =', status)

    return sources

  def get_organization(self):
    return self.organizations.get()

  def get_short_name(self):
    if self.name:
      return self.name.split(' ', 2)[0]

  def get_admin_deposits(self):
    """Returns all cash deposits originated from an admin user."""

    # Avoid circular imports.
    from models.transaction import Transaction

    if not self.is_admin:
      return None

    transactions = (Transaction.all()
                    .filter('transaction_type =', Transaction.Type.Deposit)
                    .filter('sender =', self))
    return transactions

  def is_editable_by(self, profile):
    return profile.is_admin or profile.key() == self.key()

  def put(self, *args, **kwargs):
    if not self.activation_key:
      self.activation_key = str(uuid.uuid4())

    return super(Profile, self).put(*args, **kwargs)

  def get_transactions_received(self, transaction_type=None):
    transactions = self.transactions_received
    if transaction_type:
      transactions.filter('transaction_type =', transaction_type)
    return transactions

  def get_transactions_sent(self, transaction_type=None):
    transactions = self.transactions_sent
    if transaction_type:
      transactions.filter('transaction_type =', transaction_type)
    return transactions

  def get_balance(self, currency):
    if currency == constants.JMD_CURRENCY:
      return self.jmd_balance

    elif currency == constants.USD_CURRENCY:
      return self.usd_balance

    else:
      raise ValueError('Expected valid currency, got "%s".' % currency)

  def increment_balance(self, currency, amount, put=False):
    if currency == constants.JMD_CURRENCY:
      self.jmd_balance += amount

    elif currency == constants.USD_CURRENCY:
      self.usd_balance += amount

    else:
      raise ValueError('Expected valid currency, got "%s".' % currency)

    if put:
      self.put()
