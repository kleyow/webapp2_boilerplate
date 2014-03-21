from google.appengine.ext import db

from library import constants


class Event(db.Model):
  """Represents an event for which tickets can be sold."""

  # Event data.
  name = db.StringProperty()
  date = db.DateTimeProperty()
  location = db.StringProperty()
  usd_price = db.IntegerProperty(default=0)
  jmd_price = db.IntegerProperty(default=0)
  max_tickets = db.IntegerProperty(default=None)

  # Administrative data.
  created = db.DateTimeProperty(auto_now_add=True)

  def get_price(self, currency):
    if currency == constants.JMD_CURRENCY:
      return self.jmd_price

    elif currency == constants.USD_CURRENCY:
      return self.usd_price

    else:
      raise ValueError('Expected valid currency, got "%s".' % currency)

  def get_organization(self):
    return self.parent()

  def put(self, *args, **kwargs):
    if not self.get_organization():
      raise RuntimeError('Missing parent (Organization) object.')

    return super(Event, self).put(*args, **kwargs)
