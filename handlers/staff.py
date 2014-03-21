import logging

from google.appengine.api import taskqueue
from google.appengine.ext import db
from webapp2_extras import security

from handlers import base
from forms import error_messages
from forms.refund import RefundForm
from forms.staff import StaffForm
from forms.staff_login import StaffLoginForm
from forms.transfer import TransferForm
from library import locking
from library.auth import login_not_required
from models.staff import Staff
from models.transaction import Transaction


class StaffHandler(base.BaseStaffHandler):

  def _get_homepage_uri(self, staff):
    """Returns the uri for the appropriate home page for a staff member.

    If the Organization is editable by the staff member, they are to be
    redirected to the Organization's home page, otherwise, they should be
    taken to the regular Staff home."""

    organization = staff.get_organization()
    if organization.is_editable_by(staff):
      return self.uri_for('organization.view', id=organization.key().id())

    return self.uri_for('staff.home')

  @login_not_required
  def login(self):
    error = False

    # If the staff member is already logged in, redirect them to their
    # appropriate view; Organization home if they are a manager or admin, and
    # Staff home otherwise.
    current_staff = self.get_current_staff()
    if current_staff:
      return self.redirect(self._get_homepage_uri(current_staff))

    if self.request.method == 'POST':
      form = StaffLoginForm(self.request.POST)

      if form.validate():
        login = form.data['username']
        password = form.data['password']
        staff = Staff.get_by_login(login)

        # Return None if the password doesn't match the datastore.
        if not (staff and
           security.check_password_hash(str(password), staff.password_hash)):
          return self.render_to_response(
              'staff_login.haml', {'error': True})

        self.session['staff_key'] = str(staff.key())
        redirect = self.request.get('redirect')

        # Prevent an attacker from using staff login to redirect to an external
        # website.
        if not redirect.startswith('/'):
          redirect = None

        return self.redirect(redirect or self._get_homepage_uri(staff))

      else:
        error = True

    return self.render_to_response('staff_login.haml', {'error': error})

  def home(self):
    # Make unactivated staff set a pin before continuing.
    staff = self.get_current_staff()
    if not staff.is_activated():
      self.session.add_flash(value='Please finish your registration with %s.' %
                             staff.get_organization().name, level='info')
      return self.redirect(self.uri_for('staff.update'))

    return self.render_to_response('staff_home.haml',
                                   {'Transaction': Transaction})

  def logout(self):
    self.session.pop('staff_key', None)
    self.session.add_flash(value='You have been successfully logged out!',
                           level='success')
    return self.redirect_to('home')

  def update(self):
    if self.request.method == 'POST':
      staff = self.get_current_staff()
      form = StaffForm(self.request.POST)
      if form.validate():
        staff.is_active = True
        staff.set_pin(str(form.data['pin']))
        staff.set_password(str(form.data['password']), put=True)
        Staff.get(staff.key())
        return self.redirect(self.uri_for('staff.home'))

      else:
        last_error = form.errors.values().pop()
        self.session.add_flash(last_error[0], level='error')

    return self.render_to_response('staff_update.haml')

  def verify(self):
    transaction = Transaction.get_by_uuid(
        self.request.POST.get('uuid', ''))
    if not transaction:
      return self.abort(404)

    current_staff = self.get_current_staff()

    # Ensure only purchases can be verified.
    if transaction.transaction_type != Transaction.Type.Purchase:
      error = error_messages.PURCHASES_ONLY_VERIFIABLE

    # Ensure unconcerned staff cannot verify a receipt.
    elif not transaction.recipient.is_viewable_by(current_staff):
      error = error_messages.UNAUTHORIZED_VERIFICATION

    # Ensure a transaction cannot be verified twice to prevent stealing of
    # tips.
    elif transaction.verifier:
      error = error_messages.ALREADY_VERIFIED

    else:
      error = None

    if error:
      self.session.add_flash(value=error, level='error')
      return self.redirect_to('transaction.verify', uuid=transaction.uuid)

    # TODO: This should be made to use the task queue, but due to deadlines,
    # will be run here.
    # Reload transaction to force the write to be fully consistent before
    # redirecting.
    try:
      transaction.verify(current_staff)

    except RuntimeError, e:
      self.session.add_flash(e.message)
      return self.redirect_to('transaction.verify', uuid=transaction.uuid)

    transaction = Transaction.get(transaction.key())
    self.session.add_flash(
        value='You have verified this receipt!', level='success')
    return self.redirect_to('transaction.verify', uuid=transaction.uuid)

  def refund(self):
    form = RefundForm(self.request.POST)

    if form.validate():
      transaction = form.data['transaction']
      organization = transaction.recipient

      # Ensure the transaction is refundable by the current staff member.
      if not transaction.is_refundable_by(self.get_current_staff()):
        error = error_messages.REFUND_UNAUTHORIZED

      # Ensure the Organization can afford to perform the refund.
      elif transaction.amount > organization.get_balance(transaction.currency):
        error = error_messages.ORGANIZATION_INADEQUATE_BALANCE

      else:
        error = None

      if error:
        self.session.add_flash(value=error, level='error')
        return self.redirect_to('home')

      # If a refund is possible, allow the purchase to be refunded.
      transaction.status = Transaction.Status.RefundPending
      transaction.put()
      self.session.add_flash('Processing refund.',
                             level='success')

      # Add the transaction to the queue for processing later.
      taskqueue.add(url=self.uri_for('transaction.process'),
                    queue_name='payment', target='transactions',
                    params={'transaction_key': str(transaction.key())})

      # Force the write to be fully applied before redirecting.
      transaction = Transaction.get(transaction.key())

      # Redirect the user to either the page they came from, or the transaction
      # private transaction receipt.
      redirect = (self.request.referrer or
                  self.uri_for('transaction.verify', uuid=transaction.uuid))

    else:
      last_error = form.errors.values().pop()
      self.session.add_flash(last_error[0], level='error')
      redirect = self.uri_for('home')

    return self.redirect(redirect)

  def deposit(self):
    if self.request.method == 'POST':
      form = TransferForm(self.request.POST)
      current_staff = self.get_current_staff()
      sender = current_staff.get_organization()

      if form.validate():
        recipient = form.data['recipient']
        amount = form.data['amount']
        currency = form.data['currency']

        if not current_staff.check_pin(form.data['pin']):
          error = error_messages.PIN_INVALID

        elif amount > sender.get_balance(currency):
          error = error_messages.INADEQUATE_ORG_BALANCE

        else:
          error = None

        if error:
          self.session.add_flash(value=error, level='error')
          return self.render_to_response('staff_deposit.haml')

        transaction = Transaction(amount=amount, sender=sender,
                                  recipient=recipient, currency=currency,
                                  transaction_type=Transaction.Type.Transfer,
                                  seller=current_staff)
        transaction.put()

        # Force the write to be fully applied before redirecting.
        transaction = Transaction.get(transaction.key())

        # Add the transaction to the queue for processing later.
        taskqueue.add(url=self.uri_for('transaction.process'),
                      queue_name='payment', target='transactions',
                      params={'transaction_key': str(transaction.key())})

        return self.redirect_to('transaction.verify',
                                uuid=transaction.uuid)

      else:
        # If validation failed, flash errors and repopulate the form.
        last_error = form.errors.values().pop()
        self.session.add_flash(last_error[0], level='error')

    return self.render_to_response('staff_deposit.haml')

  @login_not_required
  def process_verify(self):
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

      # Ensure transactions cannot be verified twice.
      if transaction.verifier:
        logging.error('Transaction {transaction_key} already verified.'
                      .format(transaction_key=transaction.key()))
        return

      # Ensure only purchases can be verified.
      elif transaction.transaction_type != Transaction.Type.Purchase:
        logging.error('Transaction {transaction_key} of type '
                      '{transaction.transaction_type} cannot be verified.'
                      .format(transaction_key=transaction.key(),
                              transaction=transaction))
        return

      # Only completed transactions can be verified.
      elif transaction.status != Transaction.Status.Completed:
        logging.error('Attempt to verify {transaction_key} when '
                      '{transaction.status}.'
                      .format(transaction_key=transaction.key(),
                              transaction=transaction))
        return

      # Get the verifier.
      verifier_key = self.request.POST.get('verifier_key')
      if not verifier_key:
        logging.error(Transaction.Errors.EmptyTransactionVerifier)
        return

      # Lock the verifier key to prevent race conditions when incrementing
      # their tip balance.
      with locking.lock(verifier_key, tries=1):
        try:
          verifier = Staff.get(verifier_key)

        except db.BadKeyError:
          verifier = None

        # If the verifier was not found, return.
        if not verifier:
          logging.error('Invalid verifier key "{verifier_key}" in '
                        '{transaction_key}.'
                        .format(verifier_key=verifier_key,
                                transaction_key=transaction.key()))
          return

        # Ensure the verifier is allowed to view the recipient.
        if not transaction.recipient.is_viewable_by(verifier):
          logging.error('Transaction {transaction_key} not viewable by '
                        '{verifier.username} ({verifier_key}).'
                        .format(transaction_key=transaction.key(),
                                verifier_key=verifier.key(),
                                verifier=verifier))

        # Since a verifier exists, and the transaction has not been verified,
        # attempt to verify the transaction.
        # We must swallow any exception raised here to prevent bad
        # verification attempts from causing the task to be reprocessed.
        try:
          transaction.verify(verifier)

        except:
          logging.exception('An error occurred when {verifier.username} '
                            '({verifier_key}) attempted to verify '
                            '{transaction_key}.'
                            .format(verifier_key=verifier.key(),
                                    verifier=verifier,
                                    transaction_key=transaction.key()))
          return

        # Force changes to transaction and staff to be fully applied before
        # completing.
        db.get([transaction.key(), verifier.key()])
