from babel.dates import format_datetime
from google.appengine.ext import deferred
from pyquery import PyQuery
import unittest2

from forms import error_messages
from library import constants, testing
from library.constants import email
from models.profile import Profile
from models.organization import Organization
from models.transaction import Transaction


class TestStaffRefund(testing.TestCase, unittest2.TestCase):

  AMOUNT = 2000

  def test_post_transaction_refund_not_logged_in(self):
    sender = self.create_profile()
    recipient = self.create_organization(owner=self.create_profile(),
                                         jmd_balance=3000)
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=self.AMOUNT,
        status=Transaction.Status.Completed, currency=constants.JMD_CURRENCY,
        transaction_type=Transaction.Type.Purchase)

    params = {'transaction': transaction.uuid}
    response = self.app.post(self.uri_for('staff.refund'), params)
    staff_login_url = self.uri_for(
        'staff.login', redirect=self.uri_for('staff.refund'))
    self.assertRedirects(response, staff_login_url)

    # Ensure no tasks have been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(0, tasks)

  def test_post_transaction_refund_logged_in(self):
    sender = self.create_profile()
    recipient = self.create_organization(jmd_balance=3000)

    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=self.AMOUNT,
        status=Transaction.Status.Completed, currency=constants.JMD_CURRENCY,
        transaction_type=Transaction.Type.Purchase)

    # Log in as staff of the recipient.
    staff = self.create_staff(organization=recipient)
    login = '%s@%s' % (staff.username, recipient.identifier)
    self.staff_login(login)
    self.assertStaffLoggedIn()

    params = {'transaction': transaction.uuid}
    response = self.app.post(self.uri_for('staff.refund'), params)
    self.assertRedirects(
        response, self.uri_for('transaction.verify', uuid=transaction.uuid))

    # Ensure a task has been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(1, tasks)

    # Ensure that the correct transaction is queued for processing.
    task, = tasks
    params = task.extract_params()
    self.assertEqual(str(transaction.key()), params['transaction_key'])

    # Process the refund.
    with self.datastore_consistency_policy(testing.HR_HIGH_CONSISTENCY_POLICY):
      response = self.app.post(
          task.url, params, headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)

    # Reload the sender, recipient and transaction and ensure that the money
    # has moved successfully.
    sender = Profile.get(sender.key())
    recipient = Organization.get(recipient.key())
    transaction = Transaction.get(transaction.key())

    self.assertEqual(self.AMOUNT, sender.jmd_balance)
    self.assertEqual(1000, recipient.jmd_balance)
    self.assertEqual(Transaction.Status.Refunded, transaction.status)

    # Ensure USD balances have not changed.
    self.assertEqual(0, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)

    # Check that a mail-sending task is in the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(1, tasks)

    # Run the task (it should be a deferred call) and check that an e-mail
    # is sent.
    task, = tasks
    deferred.run(task.payload)
    messages = self.mail_stub.get_sent_messages()
    self.assertLength(1, messages)

    # Verify that the e-mail sent has the right information.
    message, = messages
    self.assertEqual('"%s" <%s>' % (sender.name, sender.email),
                     message.to)
    self.assertEqual(email.REFUND_SUBJECT, message.subject)
    self.assertEqual(constants.FULL_NO_REPLY_EMAIL, message.sender)
    self.assertEqual(constants.FULL_SUPPORT_EMAIL, message.reply_to)
    self.assertTemplateUsed('emails/transaction.haml')

    email_greeting = PyQuery(message.html.decode())('h3.email_greeting')
    self.assertEqual('Hi %s,' % sender.name, email_greeting.text())

    email_message = PyQuery(message.html.decode())('p.email_message')
    self.assertEqual(email.REFUND_MESSAGE, email_message.text())

    email_table = PyQuery(message.html.decode())('tbody td')
    self.assertEqual(recipient.name, email_table.filter('.email_name').text())
    self.assertEqual(format_datetime(transaction.get_sender_time()),
                     email_table.filter('.email_time').text())
    self.assertEqual(transaction.get_transaction_amount(),
                     email_table.filter('.email_amount').text())
    self.assertEqual(Transaction.Status.Refunded,
                     email_table.filter('.email_status').text())

  def test_transaction_refund_flow(self):
    sender = self.create_profile()
    recipient = self.create_organization(jmd_balance=3000)
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=self.AMOUNT,
        status=Transaction.Status.Completed, currency=constants.JMD_CURRENCY,
        transaction_type=Transaction.Type.Purchase)

    # Log in as staff of the recipient.
    staff = self.create_staff(organization=recipient)
    login = '%s@%s' % (staff.username, recipient.identifier)
    self.staff_login(login)
    self.assertStaffLoggedIn()

    # View the receipt.
    response = self.app.get(self.uri_for('transaction.verify',
                            uuid=transaction.uuid))
    self.assertOk(response)

    # Attempt to request a refund.
    form = response.forms['refund-form']
    response = form.submit()

    # Ensure a task has been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(1, tasks)

    # Ensure that the correct transaction is queued for processing.
    task, = tasks
    params = task.extract_params()
    self.assertEqual(str(transaction.key()), params['transaction_key'])

    # Process the refund.
    with self.datastore_consistency_policy(testing.HR_HIGH_CONSISTENCY_POLICY):
      response = self.app.post(
          task.url, params, headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)

    # Reload the sender, recipient and transaction and ensure that the money
    # has moved successfully.
    sender = Profile.get(sender.key())
    recipient = Organization.get(recipient.key())
    transaction = Transaction.get(transaction.key())

    self.assertEqual(self.AMOUNT, sender.jmd_balance)
    self.assertEqual(1000, recipient.jmd_balance)
    self.assertEqual(Transaction.Status.Refunded, transaction.status)

    # Ensure USD balances have not changed.
    self.assertEqual(0, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)

  @testing.staff_logged_in
  def test_transaction_refund_empty_transaction_uuid(self):
    params = {'transaction': ''}
    response = self.app.post(self.uri_for('staff.refund'), params)
    self.assertRedirects(response, self.uri_for('home'))
    self.assertFlashMessage(
        message=error_messages.TRANSACTION_REQUIRED, level='error')

    # Ensure no tasks have been queued.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(0, tasks)

  @testing.staff_logged_in
  def test_transaction_refund_invalid_transaction_uuid(self):
    params = {'transaction': 'INVALID'}
    response = self.app.post(self.uri_for('staff.refund'), params)
    self.assertRedirects(response, self.uri_for('home'))
    self.assertFlashMessage(
        message=error_messages.TRANSACTION_NOT_FOUND, level='error')

    # Ensure no tasks have been queued.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(0, tasks)

  @testing.staff_logged_in
  def test_transaction_refund_transfer(self):
    sender = self.create_profile()
    recipient = self.create_profile(jmd_balance=3000)
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=self.AMOUNT,
        status=Transaction.Status.Completed, currency=constants.JMD_CURRENCY,
        transaction_type=Transaction.Type.Transfer)

    params = {'transaction': transaction.uuid}
    response = self.app.post(self.uri_for('staff.refund'), params)
    self.assertRedirects(response, self.uri_for('home'))

    # Ensure no tasks have been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(0, tasks)

  def test_transaction_refund_inadequate_organization_balance(self):
    sender = self.create_profile()
    recipient = self.create_organization(jmd_balance=1000)
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=self.AMOUNT,
        status=Transaction.Status.Completed, currency=constants.JMD_CURRENCY,
        transaction_type=Transaction.Type.Purchase)

    # Log in as staff of the recipient.
    staff = self.create_staff(organization=recipient)
    login = '%s@%s' % (staff.username, recipient.identifier)
    self.staff_login(login)
    self.assertStaffLoggedIn()

    params = {'transaction': transaction.uuid}
    response = self.app.post(self.uri_for('staff.refund'), params)
    self.assertRedirects(response, self.uri_for('home'))
    self.assertFlashMessage(
        message=error_messages.ORGANIZATION_INADEQUATE_BALANCE, level='error')

    # Ensure no tasks have been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(0, tasks)

  @testing.staff_logged_in
  def test_transaction_refund_deposit(self):
    sender = self.create_profile()
    recipient = self.create_organization(
        owner=self.create_profile(), jmd_balance=3000)
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=self.AMOUNT,
        status=Transaction.Status.Completed, currency=constants.JMD_CURRENCY,
        transaction_type=Transaction.Type.Deposit)

    params = {'transaction': transaction.uuid}
    response = self.app.post(self.uri_for('staff.refund'), params)
    self.assertRedirects(response, self.uri_for('home'))

    # Ensure no tasks have been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(0, tasks)

  @testing.staff_logged_in
  def test_transaction_refund_processing_transaction(self):
    sender = self.create_profile()
    recipient = self.create_organization(jmd_balance=3000)
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=self.AMOUNT,
        status=Transaction.Status.Processing, currency=constants.JMD_CURRENCY,
        transaction_type=Transaction.Type.Purchase)

    # Log in as staff of the recipient.
    staff = self.create_staff(organization=recipient)
    login = '%s@%s' % (staff.username, recipient.identifier)
    self.staff_login(login)
    self.assertStaffLoggedIn()

    params = {'transaction': transaction.uuid}
    response = self.app.post(self.uri_for('staff.refund'), params)
    self.assertRedirects(response, self.uri_for('home'))

    # Ensure no tasks have been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(0, tasks)

  @testing.staff_logged_in
  def test_transaction_refund_pending_transaction(self):
    sender = self.create_profile()
    recipient = self.create_organization(
        owner=self.create_profile(), jmd_balance=3000)
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=self.AMOUNT,
        status=Transaction.Status.Pending, currency=constants.JMD_CURRENCY,
        transaction_type=Transaction.Type.Purchase)

    params = {'transaction': transaction.uuid}
    response = self.app.post(self.uri_for('staff.refund'), params)
    self.assertRedirects(response, self.uri_for('home'))

    # Ensure no tasks have been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_post_transaction_refund_as_sender(self):
    sender = self.get_current_profile()
    recipient = self.create_organization(owner=self.create_profile(),
                                         jmd_balance=3000)
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=self.AMOUNT,
        status=Transaction.Status.Completed, currency=constants.JMD_CURRENCY,
        transaction_type=Transaction.Type.Purchase)

    params = {'transaction': transaction.uuid}
    response = self.app.post(self.uri_for('staff.refund'), params)
    staff_login_url = (self.uri_for('staff.login',
                                    redirect=self.uri_for('staff.refund')))
    self.assertRedirects(response, staff_login_url)

    # Ensure no tasks have been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_post_transaction_refund_as_unconcerned_user(self):
    sender = self.create_profile()
    recipient = self.create_organization(owner=self.create_profile(),
                                         jmd_balance=3000)
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=self.AMOUNT,
        status=Transaction.Status.Completed, currency=constants.JMD_CURRENCY,
        transaction_type=Transaction.Type.Purchase)

    params = {'transaction': transaction.uuid}
    response = self.app.post(self.uri_for('staff.refund'), params)
    staff_login_url = (self.uri_for('staff.login',
                                    redirect=self.uri_for('staff.refund')))
    self.assertRedirects(response, staff_login_url)

    # Ensure no tasks have been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(0, tasks)

  def test_transaction_is_added_immediately(self):
    sender = self.create_profile()
    recipient = self.create_organization(jmd_balance=3000)
    transaction = self.create_transaction(
        sender=sender, recipient=recipient, amount=self.AMOUNT,
        status=Transaction.Status.Completed, currency=constants.JMD_CURRENCY,
        transaction_type=Transaction.Type.Purchase)

    # Log in as staff of the recipient.
    staff = self.create_staff(organization=recipient)
    login = '%s@%s' % (staff.username, recipient.identifier)
    self.staff_login(login)
    self.assertStaffLoggedIn()

    # Emulate the High Replication Datastore.
    with self.datastore_consistency_policy(testing.HR_HIGH_CONSISTENCY_POLICY):
      params = {'transaction': transaction.uuid}
      response = self.app.post(self.uri_for('staff.refund'), params)
      receipt_url = self.uri_for('transaction.verify', uuid=transaction.uuid)
      self.assertRedirects(response, receipt_url)

      # Ensure that the refund button is not on the receipt.
      response = self.app.get(response.location)
      self.assertOk(response)
      self.assertLength(0, response.pyquery('#refund-button'))
