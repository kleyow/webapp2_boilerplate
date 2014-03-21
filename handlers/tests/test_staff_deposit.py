from babel.dates import format_datetime
from google.appengine.ext import deferred
from pyquery import PyQuery
import unittest2

from forms import error_messages
from library import constants, testing
from library.constants import email
from models.organization import Organization
from models.profile import Profile
from models.transaction import Transaction


class TestStaffDeposit(testing.TestCase, unittest2.TestCase):

  def test_get_staff_deposit_not_logged_in(self):
    response = self.app.get(self.uri_for('staff.deposit'))
    staff_login_url = self.uri_for(
        'staff.login', redirect=self.uri_for('staff.deposit'))
    self.assertRedirects(response, staff_login_url)
    self.assertNotStaffLoggedIn()

  @testing.logged_in
  def test_get_staff_deposit_logged_in_as_profile(self):
    response = self.app.get(self.uri_for('staff.deposit'))
    staff_login_url = self.uri_for(
        'staff.login', redirect=self.uri_for('staff.deposit'))
    self.assertRedirects(response, staff_login_url)
    self.assertNotStaffLoggedIn()

  @testing.staff_logged_in
  def test_get_staff_deposit_logged_in_as_staff(self):
    response = self.app.get(self.uri_for('staff.deposit'))
    self.assertOk(response)
    self.assertTemplateUsed('staff_deposit.haml')
    self.assertLength(1, response.pyquery('form#deposit-form'))
    form = response.pyquery('form#deposit-form')
    self.assertEqual(self.uri_for('staff.deposit'), form.attr('action'))

  def test_post_staff_deposit_not_logged_in(self):
    params = {'amount': '50.00', 'recipient': 'test@example',
              'currency': constants.JMD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('staff.deposit'), params)
    staff_login_url = self.uri_for(
        'staff.login', redirect=self.uri_for('staff.deposit'))
    self.assertRedirects(response, staff_login_url)
    self.assertNotStaffLoggedIn()

  @testing.logged_in
  def test_post_staff_deposit_logged_in_as_profile(self):
    params = {'amount': '50.00', 'recipient': 'test@example',
              'currency': constants.JMD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('staff.deposit'), params)
    staff_login_url = self.uri_for(
        'staff.login', redirect=self.uri_for('staff.deposit'))
    self.assertRedirects(response, staff_login_url)
    self.assertNotStaffLoggedIn()

  @testing.staff_logged_in
  def test_post_staff_deposit_logged_in_as_staff(self):
    current_staff = self.get_current_staff()
    sender = current_staff.get_organization()
    sender.jmd_balance = 6000
    sender.jmd_fees = 50
    sender.put()
    recipient = self.create_profile()

    response = self.app.get(self.uri_for('staff.deposit'))
    form = response.forms['deposit-form']
    params = {'amount': '50.00', 'recipient': recipient.email,
              'currency': constants.JMD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    form['amount'] = '50.00'
    form['recipient'] = recipient.email
    form['currency'] = constants.JMD_CURRENCY
    form['pin'] = self.DEFAULT_UNHASHED_PIN
    response = form.submit()

    self.assertLength(1, Transaction.all())
    transaction = Transaction.all().get()
    self.assertRedirects(
        response, self.uri_for('transaction.verify', uuid=transaction.uuid))

    # Ensure the transaction has the correct details.
    self.assertEqual(recipient.key(), transaction.recipient.key())
    self.assertEqual(sender.key(), transaction.sender.key())
    self.assertEqual(5000, transaction.amount)
    self.assertEqual(constants.JMD_CURRENCY, transaction.currency)
    self.assertEqual(current_staff.key(), transaction.seller.key())

    # Ensure a task has been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(1, tasks)

    # Ensure the task has the correct parameters.
    task, = tasks
    params = task.extract_params()
    self.assertEqual(str(transaction.key()), params['transaction_key'])

    # Process the task and ensure it completes correctly.
    response = self.app.post(task.url, params, headers=self.TASKQUEUE_HEADERS)
    self.assertOk(response)

    # Reload all entities involved.
    sender = Organization.get(sender.key())
    recipient = Profile.get(recipient.key())
    transaction = Transaction.get(transaction.key())

    # Ensure the transaction has been sucessfully processed.
    self.assertEqual(1000, sender.jmd_balance)
    self.assertEqual(0, sender.usd_balance)
    self.assertEqual(50, sender.jmd_fees)
    self.assertEqual(0, sender.usd_fees)
    self.assertEqual(5000, recipient.jmd_balance)
    self.assertEqual(0, recipient.usd_balance)
    self.assertEqual(0, transaction.fees)

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
    self.assertEqual('"%s" <%s>' % (recipient.name, recipient.email),
                     message.to)
    self.assertEqual(email.TRANSFER_SUBJECT, message.subject)
    self.assertEqual(constants.FULL_NO_REPLY_EMAIL, message.sender)
    self.assertEqual(constants.FULL_SUPPORT_EMAIL, message.reply_to)
    self.assertTemplateUsed('emails/transaction.haml')

    email_greeting = PyQuery(message.html.decode())('h3.email_greeting')
    self.assertEqual('Hi %s,' % recipient.name, email_greeting.text())

    email_message = PyQuery(message.html.decode())('p.email_message')
    self.assertEqual(email.TRANSFER_MESSAGE, email_message.text())

    email_table = PyQuery(message.html.decode())('tbody td')
    self.assertEqual(sender.name, email_table.filter('.email_name').text())
    self.assertEqual(format_datetime(transaction.get_recipient_time()),
                     email_table.filter('.email_time').text())
    self.assertEqual(transaction.get_transaction_amount(),
                     email_table.filter('.email_amount').text())
    self.assertEqual(Transaction.Status.Completed,
                     email_table.filter('.email_status').text())

  @testing.staff_logged_in
  def test_post_staff_deposit_invalid_pin(self):
    current_staff = self.get_current_staff()
    sender = current_staff.get_organization()
    sender.jmd_balance = 6000
    sender.put()
    recipient = self.create_profile()

    params = {'amount': '50.00', 'recipient': recipient.email,
              'currency': constants.JMD_CURRENCY, 'tip_amount': '0',
              'pin': '4444'}
    response = self.app.post(self.uri_for('staff.deposit'), params)
    self.assertOk(response)
    self.assertFlashMessage(level='error', message=error_messages.PIN_INVALID,
                            response=response)

    # Ensure no transactions have been created, and no tasks are in the queue.
    self.assertLength(0, Transaction.all())
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(0, tasks)

  @testing.staff_logged_in
  def test_post_staff_deposit_insufficient_balance(self):
    recipient = self.create_profile()

    params = {'amount': '50.00', 'recipient': recipient.email,
              'currency': constants.JMD_CURRENCY, 'tip_amount': '0',
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('staff.deposit'), params)
    self.assertOk(response)
    self.assertFlashMessage(level='error',
                            message=error_messages.INADEQUATE_ORG_BALANCE,
                            response=response)

    # Ensure no transactions have been created, and no tasks are in the queue.
    self.assertLength(0, Transaction.all())
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(0, tasks)
