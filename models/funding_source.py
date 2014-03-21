import datetime

from google.appengine.ext import db


class FundingSource(db.Model):
  """Represents a method of payment for adding credit to a profile.
  Currently, Stripe is used to process credit card payments.
  A funding source can be in one of three states:

    Accepted: The funding source has been verified by the payment processor
              (Stripe), and can be used to add credit to the system, provided
              the card is still in a usable state. (Not maxed out, etc)

    Pending:  The funding source has been added, but has not yet been verified
              by the payment processor, and therefore cannot be used to
              top up an account.

    Rejected: The funding source has been declined by the payment processor,
              and must not be allowed to be used as payment for credit.
              """
  class Status:
    Accepted = 'accepted'
    Pending = 'pending'
    Rejected = 'rejected'

  # Keep track of the date we added the source (for auditing purposes).
  created = db.DateProperty(auto_now_add=True)
  is_verified = db.BooleanProperty(default=False)
  status = db.StringProperty(default=Status.Pending)

  # NOTE: For now, just focusing on credit cards.

  # Stripe-specific data.
  card_token = db.StringProperty()
  customer_id = db.StringProperty()

  # Local data to be displayed to the user.
  nickname = db.StringProperty()
  last_four_digits = db.StringProperty()
  exp_month = db.StringProperty()
  exp_year = db.StringProperty()

  # Derived fields.
  is_expired = db.BooleanProperty(default=False)

  @classmethod
  def get_by_customer_id(cls, customer_id):
    return cls.all().filter('customer_id =', customer_id).get()

  def get_profile(self):
    return self.parent()

  def get_expiration_date(self):
    """Return a datetime object for the expiration date.

    Computes the 1st of the following month, then subtracts one day to safely
    get the last day of the month.
    """
    if self.exp_month and self.exp_year:
      date = datetime.date(year=int(self.exp_year),
                           month=int(self.exp_month) + 1,
                           day=1)
      return date - datetime.timedelta(days=1)

  def is_editable_by(self, profile):
    return profile and (profile.is_admin or
                        profile.key() == self.get_profile().key())

  def compute_derived_fields(self, put=False):
    self.is_expired = (self.get_expiration_date() < datetime.date.today())

    if put:
      self.put()

    return self

  def put(self, *args, **kwargs):
    if not self.get_profile():
      raise RuntimeError('Missing parent Profile object.')

    return super(FundingSource, self).put(*args, **kwargs)
