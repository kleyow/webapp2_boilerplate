from babel.dates import format_datetime
from google.appengine.ext import deferred
from pyquery import PyQuery
import unittest2

from forms import error_messages
from library import constants, testing
from library.constants import email
from models.profile import Profile
from models.transaction import Transaction


class TestTransactionTransfer(testing.TestCase, unittest2.TestCase):

  def test_get_transfer_not_logged_in(self):
    response = self.app.get(self.uri_for('transaction.transfer'))
    login_url = self.uri_for(
        'login', redirect=self.uri_for('transaction.transfer'))
    self.assertRedirects(response, login_url)

  @testing.logged_in
  def test_get_transfer_logged_in(self):
    response = self.app.get(self.uri_for('transaction.transfer'))
    self.assertOk(response)
    self.assertTemplateUsed('transaction_transfer.haml')
    self.assertLength(1, response.pyquery('form.transfer'))

  def test_post_transfer_not_logged_in(self):
    params = {'amount': '50.00', 'recipient': 'test@example.com',
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('transaction.transfer'), params)
    login_url = self.uri_for(
        'login', redirect=self.uri_for('transaction.transfer'))
    self.assertRedirects(response, login_url)
    self.assertLength(0, Transaction.all())

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_post_transfer_logged_in_usd(self):
    sender = self.get_current_profile()
    sender.usd_balance = 5000
    sender.put()
    recipient = self.create_profile()

    params = {'amount': '30.00', 'recipient': recipient.email,
              'currency': constants.USD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('transaction.transfer'), params)

    # Ensure a transaction has been created.
    self.assertLength(1, Transaction.all())

    # Ensure the correct sender and recipient are set, and that the transaction
    # has been marked as a transfer.
    transaction = Transaction.all().get()
    self.assertEqual(sender.key(), transaction.sender.key())
    self.assertEqual(recipient.key(), transaction.recipient.key())
    self.assertEqual(Transaction.Type.Transfer, transaction.transaction_type)
    self.assertRedirects(
        response, self.uri_for('transaction.view', id=transaction.key().id()))

    # Ensure a task has been placed in the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(1, tasks)

    # Ensure the correct transaction is in the queue.
    task, = tasks
    params = task.extract_params()
    self.assertEqual(str(transaction.key()), params['transaction_key'])
    response = self.app.post(self.uri_for('transaction.process'), params,
                             headers=self.TASKQUEUE_HEADERS)
    self.assertOk(response)

    # Ensure the balances have updated and the transaction has been marked as
    # completed.
    sender = Profile.get(sender.key())
    recipient = Profile.get(recipient.key())
    transaction = Transaction.get(transaction.key())
    self.assertEqual(2000, sender.usd_balance)
    self.assertEqual(3000, recipient.usd_balance)
    self.assertEqual(Transaction.Status.Completed, transaction.status)

    # Ensure JMD balances have not changed.
    self.assertEqual(0, sender.jmd_balance)
    self.assertEqual(0, recipient.jmd_balance)

  @testing.logged_in
  def test_sender_cannot_overdraw_account(self):
    sender = self.get_current_profile()
    sender.usd_balance = 5000
    sender.put()
    recipient = self.create_profile()

    params = {'amount': '80.00', 'recipient': recipient.email,
              'currency': constants.USD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('transaction.transfer'), params)
    self.assertFlashMessage(message=error_messages.INADEQUATE_BALANCE,
                            level='error', response=response)

    # Ensure the balances have not been changed and no transaction has been
    # created.
    sender = Profile.get(sender.key())
    recipient = Profile.get(recipient.key())
    self.assertEqual(5000, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)
    self.assertLength(0, Transaction.all())

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_sender_cannot_send_money_to_themselves(self):
    sender = self.get_current_profile()
    sender.usd_balance = 5000
    sender.put()

    params = {'amount': '30.00', 'recipient': sender.email,
              'currency': constants.USD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('transaction.transfer'), params)
    self.assertFlashMessage(message=error_messages.SENDER_IS_RECIPIENT,
                            level='error', response=response)

    # Ensure the balance has not been changed, and no transaction has been
    # created.
    sender = Profile.get(sender.key())
    self.assertEqual(5000, sender.usd_balance)
    self.assertLength(0, Transaction.all())

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_sender_cannot_send_negative_amount(self):
    sender = self.get_current_profile()
    sender.usd_balance = 5000
    sender.put()
    recipient = self.create_profile()

    params = {'amount': '-80.00', 'recipient': recipient.email,
              'currency': constants.USD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('transaction.transfer'), params)
    self.assertFlashMessage(message=error_messages.POSITIVE_AMOUNT_REQUIRED,
                            level='error', response=response)

    # Ensure the balances have not been changed and no transaction has been
    # created.
    sender = Profile.get(sender.key())
    recipient = Profile.get(recipient.key())
    self.assertEqual(5000, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)
    self.assertLength(0, Transaction.all())

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_invalid_recipient_fails(self):
    sender = self.get_current_profile()
    sender.usd_balance = 5000
    sender.put()

    params = {'amount': '30.00', 'recipient': 'fake@email.com',
              'currency': constants.USD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('transaction.transfer'), params)
    self.assertFlashMessage(message=error_messages.RECIPIENT_NOT_FOUND,
                            level='error', response=response)

    # Ensure the balance has not been changed, and no transaction has been
    # created.
    sender = Profile.get(sender.key())
    self.assertEqual(5000, sender.usd_balance)
    self.assertLength(0, Transaction.all())

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_unactivated_recipient_fails(self):
    sender = self.get_current_profile()
    sender.usd_balance = 5000
    sender.put()
    recipient = self.create_profile(activated=False)

    params = {'amount': '30.00', 'recipient': recipient.email,
              'currency': constants.USD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('transaction.transfer'), params)
    self.assertFlashMessage(message=error_messages.RECIPIENT_NOT_ACTIVATED,
                            level='error', response=response)

    # Ensure the balances have not been changed and no transaction has been
    # created.
    sender = Profile.get(sender.key())
    recipient = Profile.get(recipient.key())
    self.assertEqual(5000, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)
    self.assertLength(0, Transaction.all())

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_non_beta_tester_recipient_fails(self):
    sender = self.get_current_profile()
    sender.usd_balance = 5000
    sender.put()
    recipient = self.create_profile(beta_tester=False)

    params = {'amount': '30.00', 'recipient': recipient.email,
              'currency': constants.USD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('transaction.transfer'), params)
    self.assertFlashMessage(message=error_messages.RECIPIENT_NOT_BETA_TESTER,
                            level='error', response=response)

    # Ensure the balances have not been changed and no transaction has been
    # created.
    sender = Profile.get(sender.key())
    recipient = Profile.get(recipient.key())
    self.assertEqual(5000, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)
    self.assertLength(0, Transaction.all())

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_no_pin_provided_fails(self):
    sender = self.get_current_profile()
    sender.usd_balance = 5000
    sender.put()
    recipient = self.create_profile(beta_tester=True)

    params = {'amount': '30.00', 'recipient': recipient.email,
              'currency': constants.USD_CURRENCY}
    response = self.app.post(self.uri_for('transaction.transfer'), params)
    self.assertFlashMessage(message=error_messages.PIN_REQUIRED,
                            level='error', response=response)

    # Ensure the balances have not been changed and no transaction has been
    # created.
    sender = Profile.get(sender.key())
    recipient = Profile.get(recipient.key())
    self.assertEqual(5000, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)
    self.assertLength(0, Transaction.all())

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_wrong_pin_provided_fails(self):
    sender = self.get_current_profile()
    sender.usd_balance = 5000
    sender.put()
    recipient = self.create_profile(beta_tester=True)

    params = {'amount': '30.00', 'recipient': recipient.email,
              'currency': constants.USD_CURRENCY, 'pin': 'gaza'}
    response = self.app.post(self.uri_for('transaction.transfer'), params)
    self.assertFlashMessage(message=error_messages.PIN_INVALID,
                            level='error', response=response)

    # Ensure the balances have not been changed and no transaction has been
    # created.
    sender = Profile.get(sender.key())
    recipient = Profile.get(recipient.key())
    self.assertEqual(5000, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)
    self.assertLength(0, Transaction.all())

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_invalid_pin_provided_fails(self):
    sender = self.get_current_profile()
    sender.usd_balance = 5000
    sender.put()
    recipient = self.create_profile(beta_tester=True)

    params = {'amount': '30.00', 'recipient': recipient.email,
              'currency': constants.USD_CURRENCY, 'pin': '2234'}
    response = self.app.post(self.uri_for('transaction.transfer'), params)
    self.assertFlashMessage(message=error_messages.PIN_INVALID,
                            level='error')
    self.assertRedirects(response, self.uri_for('transaction.transfer'))

    # Ensure the balances have not been changed and no transaction has been
    # created.
    sender = Profile.get(sender.key())
    recipient = Profile.get(recipient.key())
    self.assertEqual(5000, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)
    self.assertLength(0, Transaction.all())

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_only_double_digit_decimals_accepted_in_forms(self):
    sender = self.get_current_profile()
    sender.usd_balance = 5000
    sender.put()
    recipient = self.create_profile()

    params = {'amount': '30.005', 'recipient': recipient.email,
              'currency': constants.USD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('transaction.transfer'), params)
    self.assertFlashMessage(message=error_messages.DECIMAL_PLACES,
                            level='error', response=response)

    # Ensure the balances have not been changed and no transaction has been
    # created.
    sender = Profile.get(sender.key())
    recipient = Profile.get(recipient.key())
    self.assertEqual(5000, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)
    self.assertLength(0, Transaction.all())

  @testing.logged_in
  def test_amount_field_has_correct_step_attribute(self):
    response = self.app.get(self.uri_for('transaction.transfer'))
    self.assertOk(response)
    self.assertEqual(
        '0.01', response.pyquery('input[name=amount]').attr('step'))

  @testing.logged_in
  def test_recipient_input_field_has_email(self):
    response = self.app.get(self.uri_for('transaction.transfer'))
    self.assertOk(response)
    self.assertEqual(
        'email', response.pyquery('input#recipient').attr('type'))

  @testing.logged_in
  def test_transaction_is_added_immediately(self):
    current_profile = self.get_current_profile()
    current_profile.usd_balance = 5000
    current_profile.put()
    recipient = self.create_profile()

    # Emulate the High Replication Datastore.
    with self.datastore_consistency_policy(testing.HR_HIGH_CONSISTENCY_POLICY):
      params = {'amount': '30.00', 'recipient': recipient.email,
                'currency': constants.USD_CURRENCY,
                'pin': self.DEFAULT_UNHASHED_PIN}
      response = self.app.post(self.uri_for('transaction.transfer'), params)
      self.assertRedirects(response)

      # Ensure that requesting the receipt immediately after the transaction
      # doesn't 404.
      response = self.app.get(response.location)
      self.assertOk(response)

  @testing.logged_in
  def test_jmd_transfers(self):
    current_profile = self.get_current_profile()
    current_profile.jmd_balance = 5000
    current_profile.put()
    recipient = self.create_profile()

    params = {'amount': '20.00', 'recipient': recipient.email,
              'currency': constants.JMD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('transaction.transfer'), params)
    self.assertLength(1, Transaction.all())
    transaction = Transaction.all().get()
    self.assertRedirects(
        response, self.uri_for('transaction.view', id=transaction.key().id()))

    # Ensure a task has been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(1, tasks)
    task, = tasks
    params = task.extract_params()
    self.assertEqual(str(transaction.key()), params['transaction_key'])

    # Execute the tasks and ensure balances updated accordingly.
    with self.datastore_consistency_policy(testing.HR_LOW_CONSISTENCY_POLICY):
      response = self.app.post(task.url, params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)

    current_profile = Profile.get(current_profile.key())
    recipient = Profile.get(recipient.key())
    transaction = Transaction.get(transaction.key())

    self.assertEqual(current_profile.jmd_balance, 3000)
    self.assertEqual(recipient.jmd_balance, 2000)
    self.assertEqual(Transaction.Status.Completed, transaction.status)

    # Ensure USD balances have not changed.
    self.assertEqual(0, current_profile.usd_balance)
    self.assertEqual(0, recipient.usd_balance)

  @testing.logged_in
  def test_transfer_with_whole_number_amount(self):
    sender = self.get_current_profile()
    sender.jmd_balance = 5000
    sender.put()
    recipient = self.create_profile()

    params = {'amount': '30', 'recipient': recipient.email,
              'currency': constants.JMD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('transaction.transfer'), params)
    self.assertLength(1, Transaction.all())
    transaction = Transaction.all().get()
    self.assertRedirects(response, self.uri_for('transaction.view',
                         id=transaction.key().id()))

    # Ensure the transaction has the correct amount.
    self.assertEqual(3000, transaction.amount)

  @testing.logged_in
  def test_transfers_cannot_be_made_with_over_maximum_usd(self):
    sender = self.get_current_profile()
    sender.usd_balance = 10000
    sender.put()
    recipient = self.create_profile()

    params = {'amount': '80.00', 'recipient': recipient.email,
              'currency': constants.USD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('transaction.transfer'), params)
    self.assertFlashMessage(level='error', response=response)

    # Ensure no transactions have been created, and that the
    # balances have remained the same.
    sender = Profile.get(sender.key())
    recipient = Profile.get(recipient.key())
    self.assertLength(0, Transaction.all())
    self.assertEqual(10000, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)
    self.assertEqual(0, sender.jmd_balance)
    self.assertEqual(0, recipient.jmd_balance)

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_transfers_cannot_be_made_with_over_maximum_jmd(self):
    sender = self.get_current_profile()
    sender.jmd_balance = 1000000
    sender.put()
    recipient = self.create_profile()

    params = {'amount': '8000.00', 'recipient': recipient.email,
              'currency': constants.JMD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('transaction.transfer'), params)
    self.assertFlashMessage(level='error', response=response)

    # Ensure no transactions have been created, and that the
    # balances have remained the same.
    sender = Profile.get(sender.key())
    recipient = Profile.get(recipient.key())
    self.assertLength(0, Transaction.all())
    self.assertEqual(0, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)
    self.assertEqual(1000000, sender.jmd_balance)
    self.assertEqual(0, recipient.jmd_balance)

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_recipient_email_field_is_case_insensitive(self):
    sender = self.get_current_profile()
    sender.jmd_balance = 5000
    sender.put()
    recipient = self.create_profile()

    # Attempt to make a transfer with an uppercase email address.
    params = {'amount': '20.00', 'recipient': recipient.email.upper(),
              'currency': constants.JMD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('transaction.transfer'), params)

    # Ensure a transaction has been created.
    self.assertLength(1, Transaction.all())
    transaction = Transaction.all().get()
    self.assertRedirects(
        response, self.uri_for('transaction.view', id=transaction.key().id()))

    # Ensure the recipient email address is added to the transaction correctly.
    self.assertEqual(recipient.email, transaction.recipient.email)

  @testing.logged_in
  def test_transfer_form_repopulates_on_failure(self):
    recipient = self.create_profile()

    params = {'amount': '-40.00', 'recipient': recipient.email,
              'currency': constants.USD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('transaction.transfer'), params)
    self.assertFlashMessage(level='error', response=response)

    # Ensure the form is re-populated.
    self.assertEqual(
        params['amount'], response.pyquery('input#amount').attr('value'))
    self.assertEqual(params['recipient'],
                     response.pyquery('input#recipient').attr('value'))
    option = response.pyquery('#currency option[selected="selected"]')
    self.assertEqual(params['currency'], option.attr('value'))

  @testing.logged_in
  def test_email_is_sent_after_successful_transfer(self):
    sender = self.get_current_profile()
    sender.jmd_balance = 5000
    sender.put()
    recipient = self.create_profile(name='recipient')

    params = {'amount': '20.00', 'recipient': recipient.email,
              'currency': constants.JMD_CURRENCY,
              'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(self.uri_for('transaction.transfer'), params)
    self.assertLength(1, Transaction.all())
    transaction = Transaction.all().get()
    self.assertRedirects(
        response, self.uri_for('transaction.view', id=transaction.key().id()))

    # Ensure a task has been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(1, tasks)
    task, = tasks
    params = task.extract_params()
    self.assertEqual(str(transaction.key()), params['transaction_key'])

    # Execute the tasks and ensure balances updated accordingly.
    with self.datastore_consistency_policy(testing.HR_LOW_CONSISTENCY_POLICY):
      response = self.app.post(task.url, params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)

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
