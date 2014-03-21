import json

from google.appengine.ext import db

from library import json_encoder


class TransactionReceipt(db.Model):
  """Holds a receipt (belonging to a particular user) for a transaction."""

  owner = db.ReferenceProperty(required=False)

  # Stored as JSON (since it is read-only).
  transaction_data = db.TextProperty()

  def load_transaction_data(self, transaction, put=False):
    self.transaction_data = json.dumps(
        db.to_dict(transaction), default=json_encoder.serialize_model)

    if put:
      self.put()

  def get_owner(self):
    return self.parent()

  def put(self, *args, **kwargs):
    if not self.get_owner():
      raise RuntimeError('Missing parent (owner) object.')

    super(TransactionReceipt, self).put(*args, **kwargs)
