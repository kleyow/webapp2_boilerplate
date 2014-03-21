import json
import logging
import time

from google.appengine.api import taskqueue
from google.appengine.ext import db, deferred
import keen
import stripe

from forms import error_messages
from forms.add_credit import AddCreditForm
from forms.purchase import PurchaseForm
from forms.transfer import TransferForm
from handlers import base
from library import constants, locking
from library.constants import email
from library.auth import login_not_required
from models.organization import Organization
from models.transaction import Transaction
from models.transaction_receipt import TransactionReceipt


class TransactionHandler(base.BaseHandler):

  # Maximum value for each transaction.
  # For now, limited at $60.00 USD or $6,000.00 JMD.
  TRANSACTION_MAX = {
      constants.USD_CURRENCY: 6000, constants.JMD_CURRENCY: 600000}

  def add_credit(self):
    if self.request.method == 'POST':
      form = AddCreditForm(self.request.POST)

      if form.validate():
        # Create and populate the Transaction object.
        transaction = Transaction()
        transaction.amount = int(form.data['amount'] * 100)
        transaction.funding_source = form.data['funding_source']
        transaction_max = self.TRANSACTION_MAX[constants.USD_CURRENCY]

        if transaction.amount > transaction_max:
          error = ('For now, you can\'t add more than $%.2f %s.' %
                   (transaction_max / 100.0), constants.USD_CURRENCY.upper())
        elif (transaction.funding_source.get_profile().key() !=
              self.get_current_profile().key()):
          error = error_messages.UNAUTHORIZED_FUNDING_SOURCE
        else:
          error = None

        if error:
          # If there were errors let the user try again.
          self.session.add_flash(value=error, level='error')
          return self.render_to_response('transaction_add_credit.haml')

        # Save the transaction.
        transaction.transaction_type = Transaction.Type.Deposit

        # Allow a user's topups to be retrieved with
        # Profile.transactions_received.
        transaction.recipient = self.get_current_profile()
        transaction.put()

        # Kick off a task to process the transaction.
        taskqueue.add(url=self.uri_for('transaction.process'),
                      queue_name='payment', target='transactions',
                      params={'transaction_key': transaction.key()})

        # Redirect home.
        return self.redirect_to('home')

      else:
        # Unpack form errors and flash the first one.
        last_error = form.errors.values().pop()
        self.session.add_flash(value=last_error[0], level='error')

    return self.render_to_response('transaction_add_credit.haml')

  def purchase_list(self):
    return self.render_to_response(
        'transaction_purchase_list.haml',
        {'organizations': Organization.all()})

  def purchase(self, id):
    organization = Organization.get_by_id(int(id))
    if not organization:
      return self.abort(404)

    if self.request.method == 'POST':
      form = PurchaseForm(self.request.POST)
      current_profile = self.get_current_profile()

      if form.validate():
        # Create and populate the transaction object.
        transaction = Transaction()
        form.populate_obj(transaction)
        transaction.sender = current_profile
        transaction.recipient = organization
        user_total = transaction.amount + transaction.tip_amount

        # Ensure the user can afford to make the purchase.
        if (user_total >
                current_profile.get_balance(transaction.currency)):
          error = error_messages.INADEQUATE_BALANCE
        # Stop users from sending themselves money.
        elif current_profile.key() == transaction.recipient.key():
          error = error_messages.SENDER_IS_RECIPIENT

        # Cap individual transactions to mitigate financial damage from bugs.
        elif transaction.amount > self.TRANSACTION_MAX[transaction.currency]:
          error = ('You cannot spend more than $%.2f %s per transaction.' %
                   (self.TRANSACTION_MAX[transaction.currency] / 100.0,
                    transaction.currency.upper()))

        elif not current_profile.check_pin(form.data['pin']):
          error = error_messages.PIN_INVALID

        else:
          error = None

        if error:
          self.session.add_flash(error, level='error')
          return self.render_to_response(
              'transaction_purchase.haml',
              {'organization': transaction.recipient})

        # Save the transaction and add the transfer job to the queue.
        transaction.transaction_type = Transaction.Type.Purchase
        transaction.put()

        # Force the write to be fully applied before redirecting.
        transaction = Transaction.get(transaction.key())

        taskqueue.add(url=self.uri_for('transaction.process'),
                      queue_name='payment', target='transactions',
                      params={'transaction_key': transaction.key()})

        self.session.add_flash('We are processing your purchase.')
        return self.redirect_to('transaction.view',
                                id=transaction.key().id())

      # Flash errors to the user.
      else:
        last_error = form.errors.values().pop()
        self.session.add_flash(value=last_error[0], level='error')
        return self.render_to_response(
            'transaction_purchase.haml',
            {'organization': organization})

    return self.render_to_response('transaction_purchase.haml',
                                   {'organization': organization})

  @login_not_required
  def verify(self):
    # Get a transaction by uuid, and render the receipt. This handler is
    # viewable by anyone.
    uuid = self.request.get('uuid', '').strip()
    transaction = Transaction.get_by_uuid(uuid)

    return self.display_receipt(transaction)

  def view(self, id):
    # Get a transaction by ID and render the receipt if the transaction is
    # viewable by the currently logged in user.
    transaction = Transaction.get_by_id(int(id))
    current_profile = self.get_current_profile()
    if not transaction:
      return self.abort(404)

    elif not transaction.is_viewable_by(current_profile):
      self.session.add_flash(value=error_messages.ACCESS_DENIED,
                             level='error')
      return self.redirect_to('home')

    return self.display_receipt(transaction)

  @login_not_required
  def display_receipt(self, transaction, qr_code_url=None,
                      verify_transaction=False):
    if not transaction:
      return self.abort(404)

    return self.render_to_response(
        'transaction_view.haml',
        {'transaction': transaction, 'qr_code_url': qr_code_url})

  def transfer(self):
    if self.request.method == 'POST':
      form = TransferForm(self.request.POST)
      current_profile = self.get_current_profile()

      if form.validate():
        if not current_profile.check_pin(form.data['pin']):
          self.session.add_flash(error_messages.PIN_INVALID, level='error')
          return self.redirect_to('transaction.transfer')

        recipient = form.data['recipient']
        amount = form.data['amount']
        currency = form.data['currency']

        if amount > current_profile.get_balance(currency):
          error = error_messages.INADEQUATE_BALANCE
        elif current_profile.key() == recipient.key():
          error = error_messages.SENDER_IS_RECIPIENT

        # Cap individual transactions to mitigate financial damage from bugs.
        elif amount > self.TRANSACTION_MAX[currency]:
          error = ('You cannot transfer more than $%.2f %s per transaction.' %
                  (self.TRANSACTION_MAX[currency] / 100.0, currency.upper()))

        else:
          error = None

        if error:
          self.session.add_flash(value=error, level='error')
          return self.render_to_response('transaction_transfer.haml')

        transaction = Transaction(amount=amount, sender=current_profile,
                                  recipient=recipient, currency=currency,
                                  transaction_type=Transaction.Type.Transfer)
        transaction.put()

        # Force the write to be fully applied before redirecting.
        transaction = Transaction.get(transaction.key())

        # Add the transaction to the queue for processing later.
        taskqueue.add(url=self.uri_for('transaction.process'),
                      queue_name='payment', target='transactions',
                      params={'transaction_key': str(transaction.key())})

        return self.redirect_to('transaction.view', id=transaction.key().id())

      else:
        # If validation failed, flash errors and repopulate the form.
        last_error = form.errors.values().pop()
        self.session.add_flash(last_error[0], level='error')

    return self.render_to_response('transaction_transfer.haml')

  @login_not_required
  def refresh(self):
    uuid = self.request.get('uuid', '')
    transaction = Transaction.get_by_uuid(uuid)

    if not transaction:
      return self.abort(404)

    transaction_json = json.dumps({'transaction_status': transaction.status})
    self.response.content_type = 'application/json'
    return self.response.write(transaction_json)

  @login_not_required
  def process(self):
    if not self.is_taskqueue_request():
      logging.error(Transaction.Errors.UnauthorizedRequest)
      return

    transaction_key = self.request.POST.get('transaction_key')

    if not transaction_key:
      logging.error(Transaction.Errors.EmptyTransactionKey)
      return

    # Try once. This will raise an exception if we can't get the lock on the
    # transaction, and cause the task to retry.
    with locking.lock(transaction_key, tries=1):
      logging.debug('Processing transaction key "{transaction_key}".'
                    .format(transaction_key=transaction_key))

      try:
        transaction = Transaction.get(transaction_key)
      except db.BadKeyError:
        transaction = None

      # Exit. Nothing more we can do without a valid transaction key.
      if not transaction:
        logging.error('Invalid transaction key "{transaction_key}".'
                      .format(transaction_key=transaction_key))
        return

      # Ensure that completed and cancelled transactions cannot be processed.
      if transaction.status not in (Transaction.Status.Pending,
                                    Transaction.Status.RefundPending):
        logging.error('Transaction {transaction_key} cannot be processed '
                      'when marked as {transaction.status}.'
                      .format(transaction=transaction,
                              transaction_key=transaction.key()))
        return

      # Mark the transaction as processing.
      if transaction.status == Transaction.Status.Pending:
        transaction.status = Transaction.Status.Processing

      elif transaction.status == Transaction.Status.RefundPending:
        transaction.status = Transaction.Status.Refunding

      transaction.put()

      transfer_types = (Transaction.Type.Purchase, Transaction.Type.Transfer)
      sender_is_admin = getattr(transaction.sender, 'is_admin', False)
      is_cash_deposit = (
          transaction.transaction_type == Transaction.Type.Deposit and
          not transaction.funding_source and sender_is_admin)

      # Ensure cash deposits cannot originate from a non-admin Profile.
      if (transaction.transaction_type == Transaction.Type.Deposit and
         transaction.sender and
         hasattr(transaction.sender, 'is_admin') and
         not transaction.sender.is_admin):
        logging.error('Cash deposit from non-admin {sender.email} '
                      '({sender_key}) detected in {transaction_key}'
                      .format(sender=transaction.sender,
                              sender_key=transaction.sender.key(),
                              transaction_key=transaction.key()))
        transaction.cancel()
        return

      # For credit card deposits, charge the account using Stripe.
      if (transaction.transaction_type == Transaction.Type.Deposit and
         transaction.funding_source):
        stripe.api_key = self.get_stripe_api_key()

        try:
          charge = stripe.Charge.create(
              amount=transaction.amount, currency='usd',
              customer=transaction.funding_source.customer_id)
          transaction.stripe_charge_id = charge.id
          transaction.put()

        except Exception, e:
          # If there was an error, log it, update the transaction as Cancelled,
          # and then die.
          logging.exception(e.message)
          transaction.cancel()
          return

        # We've made the charge, now we *must* update balances. This should
        # retry *forever* until the profile's balance in incremented the
        # proper amount.
        profile = transaction.funding_source.get_profile()
        with locking.lock(str(profile.key()), tries=None):
          fresh_profile = profile.get(profile.key())
          fresh_profile.usd_balance += transaction.amount
          fresh_profile.put()

        # Mark the transaction as completed.
        transaction.status = Transaction.Status.Completed
        transaction.put()
        subject = email.DEPOSIT_SUBJECT
        email_message = email.DEPOSIT_MESSAGE
        self.send_mail(profile=profile, subject=subject,
                       template='emails/transaction.haml',
                       context={'transaction': transaction,
                                'email_message': email_message,
                                'email_title': email.DEPOSIT_TITLE,
                                'email_recipient': transaction.recipient.name})
        logging.debug('{profile.email} ({profile_key}) successfully topped '
                      'up with {transaction.amount}. Their new balance is '
                      '{profile.usd_balance}.'
                      .format(profile=profile, transaction=transaction,
                              profile_key=profile.key()))

        # Store audit log of successful top up.
        transaction_receipt = TransactionReceipt(parent=profile)
        transaction_receipt.load_transaction_data(transaction, put=True)

      # If we're processing a transfer purchase, we need to
      # move credit from one entity to another.
      # In the case of a cash deposit (admin Profile to user Profile, we simply
      # create new credit to be added to the user's account.
      elif (transaction.transaction_type in transfer_types or
            is_cash_deposit):
        # If we're processing a refund, flip the sender and recipient so
        # logging and transaction checks still work.
        # NOTE: This will not affect the actual transaction.
        if transaction.status == Transaction.Status.Refunding:
          sender = transaction.recipient
          recipient = transaction.sender

        else:
          sender = transaction.sender
          recipient = transaction.recipient

        # Organization objects don't have an 'email' attribute, so in order to
        # avoid having to check for it on the recipient and sender each time we
        # log, simply use getattr to place the email (if any) into a dict.
        params = {
            'recipient_email': getattr(recipient, 'email', ''),
            'sender_email': getattr(sender, 'email', '')}

        # Ensure accounts cannot send money to themselves.
        if sender.key() == recipient.key():
          logging.error('Sender {sender_email} ({sender_key}) attempted to '
                        'transfer funds to themselves in transaction '
                        '{transaction_key}.'
                        .format(sender_key=transaction.sender.key(),
                                transaction=transaction,
                                transaction_key=transaction.key(),
                                **params))
          transaction.cancel()
          return

        sender_balance = sender.get_balance(transaction.currency)
        recipient_balance = recipient.get_balance(
            transaction.currency)
        logging.debug('Transferring {transaction.amount} '
                      '{transaction.currency} from {sender_email} '
                      '({sender_key}) to {recipient_email} '
                      '({recipient_key}) in  {transaction_key}.\n'
                      'Sender balance: {sender_balance}, Recipient '
                      'balance: {recipient_balance}.'
                      .format(sender_balance=sender_balance,
                              sender_key=transaction.sender.key(),
                              recipient_balance=recipient_balance,
                              recipient_key=transaction.recipient.key(),
                              transaction=transaction,
                              transaction_key=transaction.key(),
                              **params))

        # Stop senders from sending negative and zero value transactions.
        if transaction.amount <= 0:
          logging.error('Transaction {transaction_key} detected with invalid '
                        'transfer of {transaction.amount} '
                        '{transaction.currency}.'
                        .format(transaction=transaction,
                                transacton_key=transaction.key()))
          transaction.cancel()
          return

        # Lock sender to avoid race condition bugs when checking their balance.
        with locking.lock(str(sender.key()), tries=2):
          logging.debug('Locking sender {sender_email} ({sender_key}) in '
                        'transaction {transaction_key}.'
                        .format(sender_key=sender.key(),
                                transaction_key=transaction.key(),
                                transaction=transaction,
                                **params))

          # Reload sender and ensure they have adequate funds to carry
          # out the transaction.
          sender = db.get(sender.key())
          sender_balance = sender.get_balance(transaction.currency)

          # If the transaction is a cash deposit from an administrator, we
          # don't need to check if they have an adequate balance.
          if not is_cash_deposit:
            if sender_balance < transaction.amount:
              logging.error('Transaction {transaction_key} failed due to '
                            'sender {sender_email} ({sender_key}) not having '
                            'adequate funds.'
                            .format(sender_key=sender.key(),
                                    transaction=transaction,
                                    transaction_key=transaction.key(),
                                    **params))
              transaction.cancel()
              return

          # Since the sender has adequate funds, lock the recipient to
          # perform the transfer. We *need* to retry until the balances update,
          # or an error occurs, as the balance must be updated since the
          # transaction already began processing.
          with locking.lock(str(recipient.key()), tries=1):
            logging.debug('Locking recipient {recipient_email} '
                          '({recipient_key}) in transaction '
                          '{transaction_key}.'
                          .format(recipient_key=recipient.key(),
                                  transaction_key=transaction.key(),
                                  **params))
            try:
              # Refresh recipient and transfer money.
              recipient = db.get(recipient.key())
              recipient_balance = recipient.get_balance(transaction.currency)
              transaction.transfer_funds()

            except:
              # If an error occurs, log it and cancel the transaction.
              logging.exception('An error occured when transferring '
                                '{transaction.amount} {transaction.currency} '
                                'from {sender_email} ({sender_key}) to '
                                '{recipient_email} ({recipient_key}) in '
                                'transaction {transaction_key}.\n'
                                'Sender balance: {sender_balance}, '
                                'Recipient balance: {recipient_balance}.'
                                .format(sender_balance=sender_balance,
                                        sender_key=sender.key(),
                                        recipient_balance=recipient_balance,
                                        recipient_key=recipient.key(),
                                        transaction=transaction,
                                        transaction_key=transaction.key(),
                                        **params))
              transaction.cancel()
              return

          # Store audit log of transfer for sender and recipient.
          sender_receipt = TransactionReceipt(parent=sender)
          recipient_receipt = TransactionReceipt(parent=recipient)
          sender_receipt.load_transaction_data(transaction)
          recipient_receipt.load_transaction_data(transaction)
          db.put([sender_receipt, recipient_receipt])

          # Log successful transfer.
          logging.debug('Successfully transferred {transaction.amount} '
                        '{transaction.currency} from {sender_email} '
                        '({sender_key}) to {recipient_email} '
                        '({recipient_key}) in transaction '
                        '{transaction_key}.\n'
                        'Sender balance: {sender_balance}, '
                        'Recipient balance: {recipient_balance}.'
                        .format(sender_key=sender.key(),
                                sender_balance=sender_balance,
                                recipient_balance=recipient_balance,
                                recipient_key=recipient.key(),
                                transaction=transaction,
                                transaction_key=transaction.key(),
                                **params))

          if (transaction.transaction_type == Transaction.Type.Transfer or
             is_cash_deposit):
            subject = email.TRANSFER_SUBJECT
            email_message = email.TRANSFER_MESSAGE
            email_title = email.TRANSFER_TITLE
            profile = transaction.recipient
            email_recipient = transaction.recipient.name

          elif transaction.transaction_type == Transaction.Type.Purchase:

            if transaction.status == Transaction.Status.Completed:
              subject = email.PURCHASE_SUBJECT
              email_message = email.PURCHASE_MESSAGE
              email_title = email.PURCHASE_TITLE

            elif transaction.status == Transaction.Status.Refunded:
              subject = email.REFUND_SUBJECT
              email_message = email.REFUND_MESSAGE
              email_title = email.REFUND_TITLE
            profile = transaction.sender
            email_recipient = transaction.sender.name

          self.send_mail(profile=profile, subject=subject,
                         template='emails/transaction.haml',
                         context={'transaction': transaction,
                                  'email_message': email_message,
                                  'email_title': email_title,
                                  'email_recipient': email_recipient})

          # Only send data to keen.io in production.
          if not self.is_devappserver_request():
            # Send transaction to keen.io with a deferred task.
            deferred.defer(
                record_transaction, transaction.key(), _name=transaction_key)


def record_transaction(transaction_key):
  """Sends transaction data to keen.io for further analysis.

  Currently, it is being used to send transaction data
  (amount, sender, recipient, etc.) to keen.
  No user data (real names, email addresses, etc.) or the transaction key
  should be sent to keen.io."""

  transaction = Transaction.get(transaction_key)

  if not transaction:
    logging.error('Invalid transaction key "{transaction_key}" passed.'
                  .format(transaction_key=transaction_key))

  logging.debug('Sending transaction "{transaction_key}" to keen.io.'
                .format(transaction_key=transaction_key))

  transaction_event = {
      'uuid': transaction.uuid,
      'sender': str(transaction.sender.key()),
      'recipient': str(transaction.recipient.key()),
      'total_amount': transaction.total_amount,
      'amount': transaction.amount,
      'tip_amount': transaction.tip_amount,
      'currency': transaction.currency,
      'fees': transaction.fees,
      'created': int(time.mktime(transaction.created.timetuple())),
      'status': transaction.status,
  }

  keen.add_event(transaction.transaction_type, transaction_event)

  logging.debug('Transaction "{transaction_key}" was sent to keen.io.'
                .format(transaction_key=transaction_key))
