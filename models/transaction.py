import datetime
import uuid

import pytz
from google.appengine.ext import db

from library import constants
from models.funding_source import FundingSource
from models.organization import Organization
from models.profile import Profile
from models.transaction_receipt import TransactionReceipt


class Transaction(db.Model):
  """Stores a record of each transaction.
  When a deposit is processed, the stripe_charge_id and funding_source fields
  will be populated with the relevant details, and the sender and recipient
  fields will be None.

  If a transfer is processed, however, the funding_source and stripe_charge_id
  fields will be None, and sender and recipient will contain a reference to
  the relevant entities.

  Purchases and cash deposits can be refunded. Only a completed transaction
  can be refunded.

  Deposits represent purchases of Blaze credit via cash or credit card.
  Cash deposits are processed like any other transaction, but doesn't require
  interaction with Stripe.

  Cash deposits can ONLY be originated from admins.
  If a user purchases credit from an Organization, it will be recorded as a
  transfer, and the models.staff.Staff instance responsible for the sale will
  be stored in the seller field.
  Note that in cash deposits from admins, the admin's balance is not
  decremented.
  """

  class Status:
    Pending = 'pending'
    Processing = 'processing'
    Completed = 'completed'
    Cancelled = 'cancelled'
    RefundPending = 'refund pending'
    Refunding = 'refunding'
    Refunded = 'refunded'

  class Type:
    Deposit = 'deposit'
    Transfer = 'transfer'
    Purchase = 'purchase'

  class Errors:
    EmptyTransactionKey = 'Transaction cannot have an empty key.'
    UnauthorizedRequest = ('Attempted to process transaction outside '
                           'of task queue.')
    EmptyTransactionVerifier = 'Transaction cannot have an empty verifier.'

  # Book-keeping.
  created = db.DateTimeProperty(auto_now_add=True)
  verified_time = db.DateTimeProperty()
  modified = db.DateTimeProperty(auto_now=True)
  stripe_charge_id = db.StringProperty()
  uuid = db.StringProperty()

  # Basic details about the transaction.
  funding_source = db.ReferenceProperty(FundingSource, required=False)

  # For now currency defaults to USD as to not break everything while JMD
  # is implemented into the system.
  currency = db.StringProperty(default=constants.USD_CURRENCY)
  amount = db.IntegerProperty()
  status = db.StringProperty(default=Status.Pending)
  transaction_type = db.StringProperty()
  fees = db.IntegerProperty(default=0)
  total_amount = db.IntegerProperty(default=0)
  tip_amount = db.IntegerProperty(default=0)

  # Sender, seller, verifier and receipient information for transfers.
  sender = db.ReferenceProperty(collection_name='transactions_sent')
  recipient = db.ReferenceProperty(collection_name='transactions_received')
  verifier = db.ReferenceProperty(collection_name='transactions_verified')
  seller = db.ReferenceProperty(collection_name='credit_sales')

  @classmethod
  def get_by_uuid(cls, uuid):
    return cls.all().filter('uuid =', uuid).get()

  def get_sender_time(self):
    return self.get_localized_time(self.sender.get_timezone())

  def get_recipient_time(self):
    return self.get_localized_time(self.recipient.get_timezone())

  def get_localized_time(self, timezone):
    localized_time = pytz.utc.localize(
        self.created).astimezone(timezone)
    return localized_time

  def get_transaction_amount(self):
    if self.currency == constants.USD_CURRENCY:
      return 'US$ %.2f' % ((self.amount + self.tip_amount) / 100)
    elif self.currency == constants.JMD_CURRENCY:
      return 'J$ %.2f' % ((self.amount + self.tip_amount) / 100)

  def is_viewable_by(self, viewer):
    # If an Organization is the recipient, check that the profile is either the
    # sender, or an authorized viewer of the organization.
    if isinstance(self.recipient, Organization):
      return (self.sender.key() == viewer.key() or
              self.recipient.is_viewable_by(viewer))

    # Otherwise, if a Profile is the recipient, check that the viewer is either
    # the sender or the recipient.
    elif isinstance(self.recipient, Profile):
      return (self.sender.key() == viewer.key() or
              self.recipient.key() == viewer.key())

    # If the recipient is of another type, the transaction is not viewable
    # so return False.
    else:
      return False

  def is_refundable_by(self, viewer):
    """Only completed purchases can be verified, and only profiles that are
    authorized to view the transaction can verify them."""

    organization = self.recipient
    return (self.transaction_type == Transaction.Type.Purchase and
            self.status == Transaction.Status.Completed and
            organization.is_viewable_by(viewer))

  def cancel(self):
    if self.status not in (Transaction.Status.Pending,
                           Transaction.Status.Processing,
                           Transaction.Status.Refunding):
      raise RuntimeError(
          'Cannot cancel a transaction unless it is in progress.')
    self.status = Transaction.Status.Cancelled

    transfer_types = (Transaction.Type.Transfer, Transaction.Type.Purchase)
    is_cash_deposit = (self.transaction_type == Transaction.Type.Deposit and
                       not self.funding_source)

    # If the transaction is a deposit, store a receipt for the account being
    # topped up.
    if (self.transaction_type == Transaction.Type.Deposit and
       self.funding_source):
      transaction_receipt = TransactionReceipt(parent=self.recipient)
      transaction_receipt.load_transaction_data(self, put=True)
      db.put([self, transaction_receipt])
      return

    # If the transaction is a transfer, purchase or cash deposit,
    # store receipts for the sender and recipient.
    elif self.transaction_type in transfer_types or is_cash_deposit:
      sender_receipt = TransactionReceipt(parent=self.sender)
      recipient_receipt = TransactionReceipt(parent=self.recipient)
      sender_receipt.load_transaction_data(self)
      recipient_receipt.load_transaction_data(self)
      db.put([self, sender_receipt, recipient_receipt])
      return

    # Something is horribly wrong. Just bail out.
    else:
      raise ValueError('Invalid transaction type %s.' %
                       self.transaction_type)

  @db.transactional(xg=True)
  def verify(self, staff):
    """Allows a staff member to verify a purchase and collect tips.

    Accepts an instance of models.staff.Staff and sets it as the verifier if
    the transaction is a purchase has not already been verified.
    If the transaction is not a completed purchase, is not viewable by that
    staff instance, or has already been verified, verify will raise a
    RuntimeError.
    If the transaction has not been verified, the models.staff.Staff instance
    passed to it will become the verifier, and verification time will be
    recorded.
    The staff balance will then be incremented by the tip_amount.

    NOTE: All entities involved in this transaction *must* by locked, to avoid
    race conditions when incrementing the balance."""

    if self.verifier:
      raise RuntimeError('Transaction cannot be verified more than once.')

    elif self.transaction_type != Transaction.Type.Purchase:
      raise RuntimeError('Only purchases can be verified.')

    elif self.status != Transaction.Status.Completed:
      raise RuntimeError('Only completed transactions can be verified.')

    elif not self.is_viewable_by(staff):
      raise RuntimeError('Only staff authorized to view the transaction can '
                         'verify it.')

    # Set the staff as verifier, set the verified time, and increment the
    # correct tip balance.
    self.verifier = staff
    self.verified_time = datetime.datetime.now()
    staff.increment_tip_balance(self.currency, self.tip_amount)
    db.put([self, staff])

  @db.transactional(xg=True)
  def transfer_funds(self):
    """Executes a transaction between a sender and a recipient using
    cross-group transactions to ensure that all operations are atomic.
    *All* of the entities modified in this transaction *must* be locked.

    `amount` is the bill amount
    `fees` is the percentage that should be deducted
           from the amount as our charge based on `amount`
    `total_amount` is the amount the user paid minus our fee
    `tip_amount` is user inputted load_transaction_data

    We should deduct from the sender `amount+tip_amount`
    We should credit to the recipient `total_amount+tip_amount`
    We are left with `fees` charged on `amount` only."""

    if self.amount < 0:
      raise ValueError('Transaction amount cannot be negative.')
    if self.status not in (Transaction.Status.Processing,
                           Transaction.Status.Refunding):
      raise ValueError('Funds cannot be transferred unless a transaction is '
                       'marked as processing.')

    sender_is_admin = getattr(self.sender, 'is_admin', False)
    is_cash_deposit = (self.transaction_type == Transaction.Type.Deposit and
                       not self.funding_source and sender_is_admin)

    # If the transaction is a purchase, Blaze takes a fee, so we'll deduct that
    # here to avoid inadvertently robbing merchants when transactions fail.
    if (self.transaction_type == Transaction.Type.Purchase and
            self.status == Transaction.Status.Processing):
      self.fees = int((self.amount + self.tip_amount) *
                      self.recipient.get_fee_percentage())
      self.total_amount = self.amount - self.fees
      self.recipient.increment_fees(self.currency, self.fees)

    if self.status == Transaction.Status.Refunding:
      # If we're refunding a cash deposit from an admin, we only need to
      # decrement the recipient's balance.
      if is_cash_deposit:
        self.recipient.increment_balance(self.currency, -(self.amount))

      # If we're refunding any other kind of transaction, we need to send the
      # money from recipient to sender.
      else:
        # If we're refunding a purchase, we need to return the fees to the
        # recipient and reduce the verifier's tip balance.
        if self.transaction_type == Transaction.Type.Purchase:
          self.recipient.increment_fees(self.currency, -self.fees)

          # If the transaction has a verifier, we need to decrement their tip
          # balance to reflect the refund.
          if self.verifier:
            self.verifier.increment_tip_balance(
                self.currency, -self.tip_amount, put=True)

        self.sender.increment_balance(self.currency, (self.amount +
                                                      self.tip_amount))
        self.recipient.increment_balance(self.currency, -(self.amount +
                                                          self.tip_amount))

      # Mark the purchase as refunded.
      self.status = Transaction.Status.Refunded

    elif is_cash_deposit:
      # If an administrator is topping up an account, increment the recipient's
      # balance and leave the sender's balance untouched.
      self.recipient.increment_balance(self.currency, self.amount)
      self.status = Transaction.Status.Completed

    # Otherwise, the money should flow in the normal manner (sender to
    # recipient).
    else:
      self.sender.increment_balance(self.currency, -(self.amount +
                                                     self.tip_amount))
      self.recipient.increment_balance(self.currency, (self.amount +
                                                       self.tip_amount))

      # Mark transaction as completed.
      self.status = Transaction.Status.Completed

    db.put([self.sender, self.recipient, self])

  def put(self, *args, **kwargs):
    if not self.uuid:
      self.uuid = str(uuid.uuid4())

    super(Transaction, self).put(*args, **kwargs)
