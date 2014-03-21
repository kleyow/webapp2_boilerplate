from google.appengine.ext import db

from models.transaction import Transaction


class Ticket(db.Model):
  """Represents a ticket for an event.

  Each Ticket must be a child of a models.event.Event instance,
  and must contain a reference to the models.transaction.Transaction
  created by the purchase of the Ticket."""

  transaction = db.ReferenceProperty(Transaction)

  def get_event(self):
    return self.parent()

  def put(self, *args, **kwargs):
    if not self.get_event():
      raise RuntimeError('Missing parent (Event) object.')

    return super(Ticket, self).put(*args, **kwargs)
