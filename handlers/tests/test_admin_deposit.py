from babel.dates import format_datetime
from google.appengine.ext import deferred
from pyquery import PyQuery
import unittest2

from forms import error_messages
from library import constants, testing
from library.constants import email
from models.profile import Profile
from models.transaction import Transaction


class TestAdminDeposit(testing.TestCase, unittest2.TestCase):

  def test_get_deposit_account_not_logged_in(self):
    response = self.app.get(self.uri_for('admin.deposit'))
    login_url = self.uri_for(
        'login', redirect=self.uri_for('admin.deposit'))
    self.assertRedirects(response, login_url)

  @testing.logged_in
  def test_get_deposit_account_not_admin(self):
    response = self.app.get(self.uri_for('admin.deposit'))
    self.assertRedirects(response, self.uri_for('home'))

  @testing.login_as(is_admin=True)
  def test_deposit_form_fields_have_correct_attributes(self):
    response = self.app.get(self.uri_for('admin.deposit'))
    self.assertOk(response)
    self.assertTemplateUsed('admin/deposit.haml')

    self.assertEqual('email', response.pyquery('input#recipient').attr('type'))
    self.assertEqual('recipient',
                     response.pyquery('input#recipient').attr('name'))

    self.assertEqual('number', response.pyquery('input#amount').attr('type'))
    self.assertEqual('0.01', response.pyquery('input#amount').attr('step'))
    self.assertEqual('off',
                     response.pyquery('input#amount').attr('autocomplete'))
    self.assertEqual('$0.00',
                     response.pyquery('input#amount').attr('placeholder'))

    self.assertEqual('currency',
                     response.pyquery('select#currency').attr('name'))

    self.assertEqual('password',
                     response.pyquery('input#pin').attr('type'))
    self.assertEqual('pin',
                     response.pyquery('input#pin').attr('name'))
    self.assertEqual('4', response.pyquery('input#pin').attr('maxlength'))
    self.assertEqual('off', response.pyquery('input#pin').attr('autocomplete'))

  @testing.login_as(is_admin=True)
  def test_get_deposit_account_admin(self):
    response = self.app.get(self.uri_for('admin.deposit'))
    self.assertOk(response)
    self.assertTemplateUsed('admin/deposit.haml')
    self.assertLength(1, response.pyquery('form.transfer'))

  def test_post_deposit_account_not_logged_in(self):
    recipient = self.create_profile()
    params = {'recipient': recipient.email, 'amount': '20.00',
              'currency': constants.JMD_CURRENCY, 'pin': '1234'}
    response = self.app.post(self.uri_for('admin.deposit'), params)
    login_url = self.uri_for(
        'login', redirect=self.uri_for('admin.deposit'))
    self.assertRedirects(response, login_url)

    self.assertLength(0, Transaction.all())
    self.assertEqual(0, recipient.jmd_balance)
    self.assertEqual(0, recipient.usd_balance)

  @testing.logged_in
  def test_post_deposit_account_not_admin(self):
    recipient = self.create_profile()
    params = {'recipient': recipient.email, 'amount': '20.00',
              'currency': constants.JMD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('admin.deposit'), params)
    self.assertRedirects(response, self.uri_for('home'))

    self.assertLength(0, Transaction.all())
    self.assertEqual(0, recipient.jmd_balance)
    self.assertEqual(0, recipient.usd_balance)

  @testing.login_as(is_admin=True)
  def test_post_jmd_deposit_account_admin(self):
    recipient = self.create_profile()
    sender = self.get_current_profile()

    params = {'recipient': recipient.email, 'amount': '20.00',
              'currency': constants.JMD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('admin.deposit'), params)
    self.assertRedirects(response, self.uri_for('admin.deposit'))
    self.assertFlashMessage(level='success')

    # Ensure a transaction has been created with the correct details.
    self.assertLength(1, Transaction.all())
    transaction = Transaction.all().get()

    self.assertEqual(recipient.key(), transaction.recipient.key())
    self.assertEqual(sender.key(), transaction.sender.key())
    self.assertEqual(2000, transaction.amount)
    self.assertEqual(Transaction.Type.Deposit, transaction.transaction_type)
    self.assertEqual(constants.JMD_CURRENCY, transaction.currency)

    # Ensure the transaction has been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(1, tasks)
    task, = tasks
    params = task.extract_params()
    self.assertEqual(params['transaction_key'], str(transaction.key()))

    # Process the transaction and ensure it completed successfully.
    with self.datastore_consistency_policy(testing.HR_LOW_CONSISTENCY_POLICY):
      response = self.app.post(task.url, params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)

    # Reload the sender, recipient and transaction and ensure the balances have
    # updated appropriately.
    recipient = Profile.get(recipient.key())
    sender = Profile.get(sender.key())
    transaction = Transaction.get(transaction.key())

    self.assertEqual(Transaction.Status.Completed, transaction.status)
    self.assertEqual(2000, recipient.jmd_balance)
    self.assertEqual(0, recipient.usd_balance)
    self.assertEqual(0, sender.jmd_balance)
    self.assertEqual(0, sender.usd_balance)

  @testing.login_as(is_admin=True)
  def test_post_usd_deposit_account_admin(self):
    recipient = self.create_profile()
    sender = self.get_current_profile()

    params = {'recipient': recipient.email, 'amount': '20.00',
              'currency': constants.USD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('admin.deposit'), params)
    self.assertRedirects(response, self.uri_for('admin.deposit'))
    self.assertFlashMessage(level='success')

    # Ensure a transaction has been created with the correct details.
    self.assertLength(1, Transaction.all())
    transaction = Transaction.all().get()

    self.assertEqual(recipient.key(), transaction.recipient.key())
    self.assertEqual(sender.key(), transaction.sender.key())
    self.assertEqual(2000, transaction.amount)
    self.assertEqual(Transaction.Type.Deposit, transaction.transaction_type)
    self.assertEqual(constants.USD_CURRENCY, transaction.currency)

    # Ensure the transaction has been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(1, tasks)
    task, = tasks
    params = task.extract_params()
    self.assertEqual(params['transaction_key'], str(transaction.key()))

    # Process the transaction and ensure it completed successfully.
    with self.datastore_consistency_policy(testing.HR_LOW_CONSISTENCY_POLICY):
      response = self.app.post(task.url, params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)

    # Reload the sender, recipient and transaction and ensure the balances have
    # updated appropriately.
    recipient = Profile.get(recipient.key())
    sender = Profile.get(sender.key())
    transaction = Transaction.get(transaction.key())

    self.assertEqual(Transaction.Status.Completed, transaction.status)
    self.assertEqual(0, recipient.jmd_balance)
    self.assertEqual(2000, recipient.usd_balance)
    self.assertEqual(0, sender.jmd_balance)
    self.assertEqual(0, sender.usd_balance)

  @testing.login_as(is_admin=True)
  def test_admin_cannot_deposit_themselves(self):
    current_profile = self.get_current_profile()

    params = {'recipient': current_profile.email, 'amount': '20.00',
              'currency': constants.USD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('admin.deposit'), params)
    self.assertRedirects(response, self.uri_for('admin.deposit'))
    self.assertFlashMessage(message=error_messages.SENDER_IS_RECIPIENT,
                            level='error')

  @testing.login_as(is_admin=True)
  def test_email_is_sent_after_successful_cash_deposit(self):
    recipient = self.create_profile()
    sender = self.get_current_profile()

    params = {'recipient': recipient.email, 'amount': '20.00',
              'currency': constants.USD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('admin.deposit'), params)
    self.assertRedirects(response, self.uri_for('admin.deposit'))
    self.assertFlashMessage(level='success')

    # Ensure a transaction has been created with the correct details.
    self.assertLength(1, Transaction.all())
    transaction = Transaction.all().get()

    self.assertEqual(recipient.key(), transaction.recipient.key())
    self.assertEqual(sender.key(), transaction.sender.key())
    self.assertEqual(2000, transaction.amount)
    self.assertEqual(Transaction.Type.Deposit, transaction.transaction_type)
    self.assertIsNone(transaction.funding_source)
    self.assertEqual(constants.USD_CURRENCY, transaction.currency)

    # Ensure the transaction has been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(1, tasks)
    task, = tasks
    params = task.extract_params()
    self.assertEqual(params['transaction_key'], str(transaction.key()))

    # Process the transaction and ensure it completed successfully.
    with self.datastore_consistency_policy(testing.HR_LOW_CONSISTENCY_POLICY):
      response = self.app.post(task.url, params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)

    # Reload the sender, recipient and transaction and ensure the balances have
    # updated appropriately.
    recipient = Profile.get(recipient.key())
    sender = Profile.get(sender.key())
    transaction = Transaction.get(transaction.key())

    self.assertEqual(Transaction.Status.Completed, transaction.status)
    self.assertEqual(0, recipient.jmd_balance)
    self.assertEqual(2000, recipient.usd_balance)
    self.assertEqual(0, sender.jmd_balance)
    self.assertEqual(0, sender.usd_balance)

    # Check that a mail-sending task is in the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(1, tasks)

    # Run the task (it should be a deferred call) and check that an e-mail
    # is sent.
    task, = tasks
    deferred.run(task.payload)
    messages = self.mail_stub.get_sent_messages()
    self.assertLength(1, messages)
    sender = self.get_current_profile()
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
    self.assertEqual(recipient.name, email_table.filter('.email_name').text())
    self.assertEqual(format_datetime(transaction.get_recipient_time()),
                     email_table.filter('.email_time').text())
    self.assertEqual(transaction.get_transaction_amount(),
                     email_table.filter('.email_amount').text())
    self.assertEqual(Transaction.Status.Completed,
                     email_table.filter('.email_status').text())
