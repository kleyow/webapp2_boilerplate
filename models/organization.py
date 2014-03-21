import decimal

from google.appengine.ext import db

from library import constants
from models.profile import Profile


class Organization(db.Model):
  """Stores a record of each organization.
  The fee_percentage field should *never* be accessed directly, but must be
  accessed via the get_fee_percentage method, as it is stored in the datastore
  as a string.
  It is possible to set a custom fee percentage, but the default value is
  library.constants.DEFAULT_FEE_PERCENTAGE"""

  # Administrative details.
  created = db.DateTimeProperty(auto_now_add=True)
  is_verified = db.BooleanProperty(default=False)
  fee_percentage = db.StringProperty(default=constants.DEFAULT_FEE_PERCENTAGE)

  # Staff details.
  owner = db.ReferenceProperty(Profile, collection_name='organizations')

  # Basic details.
  address = db.PostalAddressProperty()
  name = db.StringProperty()
  identifier = db.StringProperty()
  logo_url = db.StringProperty()

  # Accounting details.
  jmd_balance = db.IntegerProperty(default=0)
  usd_balance = db.IntegerProperty(default=0)
  jmd_fees = db.IntegerProperty(default=0)
  usd_fees = db.IntegerProperty(default=0)

  @classmethod
  def get_by_identifier(cls, identifier):
    return cls.all().filter('identifier = ', identifier).get()

  def is_editable_by(self, editor):
    """Organizations are editable by its Admins and Managers."""

    # NOTE: This is here for backward compatability while we roll out
    # Organization admins.
    if isinstance(editor, Profile):
      return editor.key() == self.owner.key()

    return (self.is_viewable_by(editor) and
            editor.role in (editor.Role.Manager, editor.Role.Admin))

  def is_viewable_by(self, viewer):
    """Organizations are only viewable by staff and owners."""

    organization = viewer.get_organization()

    return organization and viewer.get_organization().key() == self.key()

  def get_fee_percentage(self):
    return decimal.Decimal(self.fee_percentage)

  def get_balance(self, currency):
    if currency == constants.JMD_CURRENCY:
      return self.jmd_balance

    elif currency == constants.USD_CURRENCY:
      return self.usd_balance

    else:
      raise ValueError('Expected valid currency, got "%s".' % currency)

  def get_staff(self):
    # Prevent circular imports.
    from models.staff import Staff
    return Staff.all().ancestor(self)

  def get_fees(self, currency):
    if currency == constants.JMD_CURRENCY:
      return self.jmd_fees

    elif currency == constants.USD_CURRENCY:
      return self.usd_fees

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

  def increment_fees(self, currency, amount, put=False):
    if currency == constants.JMD_CURRENCY:
      self.jmd_fees += amount

    elif currency == constants.USD_CURRENCY:
      self.usd_fees += amount

    else:
      raise ValueError('Expected valid currency, got "%s".' % currency)

    if put:
      self.put()
