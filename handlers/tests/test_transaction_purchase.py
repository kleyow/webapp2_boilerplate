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


class TestTransactionPurchase(testing.TestCase, unittest2.TestCase):

  def test_get_transaction_purchase_list_not_logged_in(self):
    response = self.app.get(self.uri_for('transaction.purchase_list'))
    login_url = self.uri_for(
        'login', redirect=self.uri_for('transaction.purchase_list'))
    self.assertRedirects(response, login_url)

  @testing.logged_in
  def test_get_transaction_purchase_list_logged_in(self):
    response = self.app.get(self.uri_for('transaction.purchase_list'))
    self.assertOk(response)
    self.assertTemplateUsed('transaction_purchase_list.haml')

  def test_get_transaction_purchase_page_not_logged_in(self):
    organization = self.create_organization()
    response = self.app.get(
        self.uri_for('transaction.purchase', id=organization.key().id()))
    login_url = self.uri_for('login',
                             redirect=self.uri_for('transaction.purchase',
                             id=organization.key().id()))
    self.assertRedirects(response, login_url)

  @testing.logged_in
  def test_get_transaction_purchase_page_logged_in(self):
    organization = self.create_organization()
    response = self.app.get(
        self.uri_for('transaction.purchase', id=organization.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('transaction_purchase.haml')
    self.assertLength(1, response.pyquery('form.purchase'))

  @testing.logged_in
  def test_get_nonexistent_organization_purchase_page(self):
    response = self.app.get(
        self.uri_for('transaction.purchase', id=12), status=404)
    self.assertNotFound(response)

  @testing.logged_in
  def test_purchase_form_autocomplete_off(self):
    organization = self.create_organization()
    response = self.app.get(
        self.uri_for('transaction.purchase', id=organization.key().id()))
    self.assertOk(response)
    self.assertEqual('off',
                     response.pyquery('input#amount').attr('autocomplete'))

  def test_post_purchase_not_logged_in(self):
    recipient = self.create_organization()

    # Check that a POST request to transaction.purchase fails when not logged
    # in.
    params = {'amount': '50.00', 'currency': constants.USD_CURRENCY,
              'tip_amount': '0', 'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(
        self.uri_for('transaction.purchase', id=recipient.key().id()), params)
    login_url = self.uri_for(
        'login',
        redirect=self.uri_for('transaction.purchase', id=recipient.key().id()))
    self.assertRedirects(response, login_url)
    self.assertLength(0, Transaction.all())

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_post_purchase_logged_in_usd(self):
    # Set up self.current_profile and recipient.
    current_profile = self.get_current_profile()
    current_profile.usd_balance = 10000
    current_profile.put()
    recipient = self.create_organization()

    # Ensure organization balance is 0.
    recipient = Organization.get(recipient.key())
    self.assertEqual(0, recipient.usd_balance)

    # Make a purchase.
    params = {'amount': '50.00', 'currency': constants.USD_CURRENCY,
              'tip_amount': '0', 'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(
        self.uri_for('transaction.purchase', id=recipient.key().id()), params)
    # Verify that a transaction was created.
    self.assertLength(1, Transaction.all())
    transaction = Transaction.all().get()
    self.assertRedirects(response, self.uri_for('transaction.view',
                                                id=transaction.key().id()))

    # Verify that a task was dispatched to process the transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(1, tasks)

    # Ensure that the correct transaction is in the queue.
    task, = tasks
    params = task.extract_params()
    self.assertEqual(str(transaction.key()), params['transaction_key'])
    self.assertEqual(self.uri_for('transaction.process'), task.url)

    # Ensure that the transaction has the correct status and type.
    self.assertEqual(Transaction.Status.Pending, transaction.status)
    self.assertEqual(Transaction.Type.Purchase, transaction.transaction_type)

    # Emulate High Replication Datastore to test transactions.
    with self.datastore_consistency_policy(testing.HR_HIGH_CONSISTENCY_POLICY):
      # Process task and ensure transaction was successful.
      response = self.app.post(task.url, params,
                               headers=self.TASKQUEUE_HEADERS)
    self.assertOk(response)

    # Reload transaction and ensure it was successful.
    transaction = Transaction.get(transaction.key())
    self.assertEqual(Transaction.Status.Completed, transaction.status)

    # Ensure that both balances updated successfully.
    current_profile = Profile.get(current_profile.key())
    recipient = Organization.get(recipient.key())
    self.assertEqual(5000, current_profile.usd_balance)
    self.assertEqual(5000, recipient.usd_balance)

    # Ensure JMD balances are unchanged.
    self.assertEqual(0, current_profile.jmd_balance)
    self.assertEqual(0, recipient.jmd_balance)

  @testing.logged_in
  def test_post_purchase_logged_in_usd_no_pin(self):
    # Set up self.current_profile and recipient.
    current_profile = self.get_current_profile()
    current_profile.usd_balance = 10000
    current_profile.put()
    recipient = self.create_organization()

    # Ensure organization balance is 0.
    recipient = Organization.get(recipient.key())
    self.assertEqual(0, recipient.usd_balance)

    # Make a purchase.
    params = {'amount': '50.00', 'currency': constants.USD_CURRENCY,
              'tip_amount': '0'}
    response = self.app.post(
        self.uri_for('transaction.purchase', id=recipient.key().id()), params)
    self.assertOk(response)
    self.assertFlashMessage(message=error_messages.PIN_REQUIRED, level='error',
                            response=response)
    # Verify that a transaction wasn't created.
    self.assertLength(0, Transaction.all())

    # Verify that a task wasn't dispatched to process the transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_post_purchase_logged_in_usd_wrong_pin(self):
    # Set up self.current_profile and recipient.
    current_profile = self.get_current_profile()
    current_profile.usd_balance = 10000
    current_profile.put()
    recipient = self.create_organization()

    # Ensure organization balance is 0.
    recipient = Organization.get(recipient.key())
    self.assertEqual(0, recipient.usd_balance)

    # Make a purchase.
    params = {'amount': '50.00', 'currency': constants.USD_CURRENCY,
              'tip_amount': '0', 'pin': '2233'}

    response = self.app.post(
        self.uri_for('transaction.purchase', id=recipient.key().id()), params)
    self.assertOk(response)
    self.assertFlashMessage(message=error_messages.PIN_INVALID, level='error',
                            response=response)
    # Verify that a transaction wasn't created.
    self.assertLength(0, Transaction.all())

    # Verify that a task wasn't dispatched to process the transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_post_purchase_logged_in_usd_bad_pin(self):
    # Set up self.current_profile and recipient.
    current_profile = self.get_current_profile()
    current_profile.usd_balance = 10000
    current_profile.put()
    recipient = self.create_organization()

    # Ensure organization balance is 0.
    recipient = Organization.get(recipient.key())
    self.assertEqual(0, recipient.usd_balance)

    # Make a bad purchase.
    params = {'amount': '50.00', 'currency': constants.USD_CURRENCY,
              'tip_amount': '0', 'pin': 'qwer'}
    response = self.app.post(
        self.uri_for('transaction.purchase', id=recipient.key().id()), params)
    self.assertOk(response)
    self.assertFlashMessage(message=error_messages.PIN_INVALID, level='error',
                            response=response)

    # Verify that a transaction wasn't created.
    self.assertLength(0, Transaction.all())

    # Verify that a task wasn't dispatched to process the transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_purchase_cannot_be_made_with_negative_amount_usd(self):
    recipient = self.create_organization()

    # Ensure that setting a negative amount does not succeed.
    params = {'amount': '-50.00', 'currency': constants.USD_CURRENCY,
              'tip_amount': '0', 'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(
        self.uri_for('transaction.purchase', id=recipient.key().id()), params)
    self.assertOk(response)
    self.assertFlashMessage(message=error_messages.POSITIVE_AMOUNT_REQUIRED,
                            level='error', response=response)

    # Ensure no tasks or transactions are created.
    self.assertLength(0, Transaction.all())
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(0, tasks)

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_purchase_cannot_overdraw_sender_account_usd(self):
    recipient = self.create_organization()
    current_profile = self.get_current_profile()
    current_profile.usd_balance = 3000
    current_profile.put()

    # Ensure that attempting to overdraw account does not succeed.
    params = {'amount': '50.00', 'currency': constants.USD_CURRENCY,
              'tip_amount': '0', 'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(
        self.uri_for('transaction.purchase', id=recipient.key().id()), params)
    self.assertOk(response)
    self.assertFlashMessage(message=error_messages.INADEQUATE_BALANCE,
                            level='error', response=response)

    # Ensure no tasks or transactions are created.
    self.assertLength(0, Transaction.all())
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(0, tasks)

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_sender_cannot_send_money_to_themselves_usd(self):
    current_profile = self.get_current_profile()
    current_profile.usd_balance = 5000
    current_profile.put()
    params = {'amount': '50.00', 'currency': constants.USD_CURRENCY,
              'tip_amount': '0', 'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(
        self.uri_for('transaction.purchase', id=current_profile.key().id()),
        params, status=404)
    self.assertNotFound(response)

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_only_double_digit_decimal_amounts_accepted_in_form(self):
    recipient = self.create_organization()
    current_profile = self.get_current_profile()
    current_profile.usd_balance = 5000
    current_profile.put()
    params = {'amount': '30.009', 'currency': constants.USD_CURRENCY,
              'tip_amount': '0', 'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(
        self.uri_for('transaction.purchase', id=recipient.key().id()), params)
    self.assertOk(response)
    self.assertFlashMessage(message=error_messages.DECIMAL_PLACES,
                            level='error', response=response)
    self.assertLength(0, Transaction.all())

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_amount_input_field_in_purchase_form_has_attribute_step(self):
    organization = self.create_organization()
    response = self.app.get(self.uri_for(
        'transaction.purchase', id=organization.key().id()))
    self.assertOk(response)
    self.assertEqual(
        '0.01', response.pyquery('form.purchase #amount').attr('step'))

  @testing.logged_in
  def test_transaction_is_added_immediately(self):
    current_profile = self.get_current_profile()
    current_profile.usd_balance = 5000
    current_profile.put()
    recipient = self.create_organization()

    # Emulate the High Replication Datastore.
    with self.datastore_consistency_policy(testing.HR_HIGH_CONSISTENCY_POLICY):
      params = {'amount': '30.00', 'currency': constants.USD_CURRENCY,
                'tip_amount': '0', 'pin': self.DEFAULT_UNHASHED_PIN}
      response = self.app.post(
          self.uri_for('transaction.purchase', id=recipient.key().id()),
          params)
      self.assertRedirects(response)

      # Ensure that requesting the receipt immediately after the transaction
      # doesn't 404.
      response = self.app.get(response.location)
      self.assertOk(response)

  @testing.logged_in
  def test_jmd_purchases(self):
    current_profile = self.get_current_profile()
    current_profile.jmd_balance = 5000
    current_profile.put()
    recipient = self.create_organization()

    params = {'amount': '20.00', 'currency': constants.JMD_CURRENCY,
              'tip_amount': '0', 'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(
        self.uri_for('transaction.purchase', id=recipient.key().id()), params)
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
    recipient = Organization.get(recipient.key())
    transaction = Transaction.get(transaction.key())

    self.assertEqual(current_profile.jmd_balance, 3000)
    self.assertEqual(recipient.jmd_balance, 2000)
    self.assertEqual(Transaction.Status.Completed, transaction.status)

    # Ensure USD balances have not changed.
    self.assertEqual(0, current_profile.usd_balance)
    self.assertEqual(0, recipient.usd_balance)

  @testing.logged_in
  def test_purchase_with_whole_number_amount(self):
    sender = self.get_current_profile()
    sender.jmd_balance = 5000
    sender.put()
    recipient = self.create_organization()

    params = {'amount': '30', 'currency': constants.JMD_CURRENCY,
              'tip_amount': '0', 'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(
        self.uri_for('transaction.purchase', id=recipient.key().id()), params)
    self.assertLength(1, Transaction.all())
    transaction = Transaction.all().get()
    self.assertRedirects(response, self.uri_for('transaction.view',
                         id=transaction.key().id()))

    # Ensure the transaction has the correct amount.
    self.assertEqual(3000, transaction.amount)

  @testing.logged_in
  def test_purchases_cannot_be_made_with_over_maximum_usd(self):
    sender = self.get_current_profile()
    sender.usd_balance = 10000
    sender.put()
    recipient = self.create_organization()

    params = {'amount': '80.00', 'currency': constants.USD_CURRENCY,
              'tip_amount': '0', 'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(
        self.uri_for('transaction.purchase', id=recipient.key().id()), params)
    self.assertOk(response)
    self.assertFlashMessage(level='error', response=response)

    # Ensure no transactions have been created, and that the
    # balances have remained the same.
    sender = Profile.get(sender.key())
    recipient = Organization.get(recipient.key())
    self.assertLength(0, Transaction.all())
    self.assertEqual(10000, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)
    self.assertEqual(0, sender.jmd_balance)
    self.assertEqual(0, recipient.jmd_balance)

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_purchases_cannot_be_made_with_over_maximum_jmd(self):
    sender = self.get_current_profile()
    sender.jmd_balance = 1000000
    sender.put()
    recipient = self.create_organization()

    params = {'amount': '8000.00', 'currency': constants.JMD_CURRENCY,
              'tip_amount': '0', 'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(
        self.uri_for('transaction.purchase', id=recipient.key().id()), params)
    self.assertOk(response)
    self.assertFlashMessage(level='error', response=response)

    # Ensure no transactions have been created, and that the
    # balances have remained the same.
    sender = Profile.get(sender.key())
    recipient = Organization.get(recipient.key())
    self.assertLength(0, Transaction.all())
    self.assertEqual(0, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)
    self.assertEqual(1000000, sender.jmd_balance)
    self.assertEqual(0, recipient.jmd_balance)

    # Check that no mail task is in the queue due to failed transaction.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_email_is_sent_after_successful_purchase(self):
    current_profile = self.get_current_profile()
    current_profile.jmd_balance = 5000
    current_profile.put()
    recipient = self.create_organization()

    params = {'amount': '50.00', 'currency': constants.JMD_CURRENCY,
              'tip_amount': '0', 'pin': self.DEFAULT_UNHASHED_PIN}
    response = self.app.post(
        self.uri_for('transaction.purchase', id=recipient.key().id()), params)
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
    sender = self.get_current_profile()
    # Verify that the e-mail sent has the right information.
    message, = messages
    self.assertEqual('"%s" <%s>' % (sender.name, sender.email),
                     message.to)
    self.assertEqual(email.PURCHASE_SUBJECT, message.subject)
    self.assertEqual(constants.FULL_NO_REPLY_EMAIL, message.sender)
    self.assertEqual(constants.FULL_SUPPORT_EMAIL, message.reply_to)
    self.assertTemplateUsed('emails/transaction.haml')

    email_greeting = PyQuery(message.html.decode())('h3.email_greeting')
    self.assertEqual('Hi %s,' % sender.name, email_greeting.text())

    email_message = PyQuery(message.html.decode())('p.email_message')
    self.assertEqual(email.PURCHASE_MESSAGE, email_message.text())

    email_table = PyQuery(message.html.decode())('tbody td')
    self.assertEqual(recipient.name, email_table.filter('.email_name').text())
    self.assertEqual(format_datetime(transaction.get_sender_time()),
                     email_table.filter('.email_time').text())
    self.assertEqual(transaction.get_transaction_amount(),
                     email_table.filter('.email_amount').text())
    self.assertEqual(Transaction.Status.Completed,
                     email_table.filter('.email_status').text())

  @testing.logged_in
  def test_purchase_page_has_correct_form_field_attributes(self):
    organization = self.create_organization()
    response = self.app.get(
        self.uri_for('transaction.purchase', id=organization.key().id()))
    self.assertOk(response)
    self.assertTemplateUsed('transaction_purchase.haml')

    self.assertEqual('required',
                     response.pyquery('input#amount').attr('required'))
    self.assertEqual('number', response.pyquery('input#amount').attr('type'))
    self.assertEqual('amount', response.pyquery('input#amount').attr('name'))
    self.assertEqual('0.01', response.pyquery('input#amount').attr('step'))
    self.assertEqual('off',
                     response.pyquery('input#amount').attr('autocomplete'))
    self.assertEqual('0.00',
                     response.pyquery('input#amount').attr('placeholder'))

    self.assertEqual('password', response.pyquery('input#pin').attr('type'))
    self.assertEqual('pin', response.pyquery('input#pin').attr('name'))
    self.assertEqual('4', response.pyquery('input#pin').attr('maxlength'))
    self.assertEqual('required',
                     response.pyquery('input#pin').attr('required'))

    self.assertEqual('number',
                     response.pyquery('input#tip_amount').attr('type'))
    self.assertEqual('tip_amount',
                     response.pyquery('input#tip_amount').attr('name'))
    self.assertEqual('0.01', response.pyquery('input#tip_amount').attr('step'))
    self.assertEqual('off',
                     response.pyquery('input#tip_amount').attr('autocomplete'))
    self.assertEqual('0.00',
                     response.pyquery('input#tip_amount').attr('placeholder'))
