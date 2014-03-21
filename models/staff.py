from google.appengine.ext import db
from webapp2_extras import security

from library import constants
from models.organization import Organization


class Staff(db.Model):
  """Represents a staff member of an organization.

  We give each staff member an auth_user_id to allow them to log in as staff
  members without requiring them to have a Blaze profile.
  Each Staff object must have an Organization as it's parent."""

  class Role:
    """Stores a staff member's role.

    Admins are the same as Managers, except they can only be modified by
    themselves.
    Managers are able to Create, Read, Update and Delete any
    `models.staff.Staff`, including other Managers.
    They are also able to view the Organization home page, and are able to do
    everything Staff can.
    Staff are only able to view the Staff home, and are able to verify and
    refund transactions.
    Since permissions are set up in a hierarchial manner, all members in a
    role are able to perform all tasks of roles below it."""

    Staff = 'staff'
    Manager = 'manager'
    Admin = 'admin'

  name = db.StringProperty()
  created = db.DateTimeProperty(auto_now_add=True)
  username = db.StringProperty()
  password_hash = db.StringProperty()
  pin = db.StringProperty()
  is_active = db.BooleanProperty(default=False)
  role = db.StringProperty(default=Role.Staff)

  jmd_tip_balance = db.IntegerProperty(default=0)
  usd_tip_balance = db.IntegerProperty(default=0)

  @classmethod
  def get_by_login(cls, login):
    username, organization_id = login.split('@', 2)
    organization = Organization.get_by_identifier(organization_id)

    if not organization:
      return None

    return cls.all().ancestor(
        organization).filter('username =', username).get()

  def get_organization(self):
    return self.parent()

  def get_short_name(self):
    if self.name:
      return self.name.split(' ', 2)[0]

  def get_tip_balance(self, currency):
    if currency == constants.JMD_CURRENCY:
      return self.jmd_tip_balance

    elif currency == constants.USD_CURRENCY:
      return self.usd_tip_balance

    else:
      raise ValueError('Expected valid currency, got "%s".' % currency)

  def is_activated(self):
    return self.pin is not None

  def is_editable_by(self, staff):
    if self.get_organization().key() != staff.get_organization().key():
      return False

    if self.role == self.Role.Admin:
      return self.key() == staff.key()

    return (staff.role in (self.Role.Manager, self.Role.Admin) or
            self.key() == staff.key())

  def increment_tip_balance(self, currency, amount, put=False):
    if currency == constants.JMD_CURRENCY:
      self.jmd_tip_balance += amount

    elif currency == constants.USD_CURRENCY:
      self.usd_tip_balance += amount

    else:
      raise ValueError('Expected valid currency, got "%s".' % currency)

    if put:
      self.put()

  def set_pin(self, raw_pin, put=False):
    if not isinstance(raw_pin, basestring):
      raise TypeError('Expected string, got %s.' % type(raw_pin))

    self.pin = security.generate_password_hash(raw_pin, length=12)

    if put:
      self.put()

  def check_pin(self, raw_pin):
    return security.check_password_hash(str(raw_pin), self.pin)

  def set_password(self, raw_password, put=False):
    if not isinstance(raw_password, basestring):
      raise TypeError('Expected string, got %s.' % type(raw_password))

    self.password_hash = security.generate_password_hash(
        raw_password, length=12)

    if put:
      self.put()

  def check_password(self, raw_password):
    return security.check_password_hash(str(raw_password), self.password_hash)

  def put(self, *args, **kwargs):
    if not self.get_organization():
      raise RuntimeError('Missing parent (Organization) object.')

    return super(Staff, self).put(*args, **kwargs)
