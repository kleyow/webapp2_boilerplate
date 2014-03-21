from babel.dates import format_datetime
from google.appengine.ext import deferred
from pyquery import PyQuery
import mock
import unittest2

from library import constants
from library.constants import email
from forms import error_messages
from library import testing
from models.funding_source import FundingSource
from models.profile import Profile
from models.transaction import Transaction


class TestTransactionHandler(testing.TestCase, unittest2.TestCase):

  def test_view_add_credit_page_not_logged_in(self):
    self.assertNotLoggedIn()
    response = self.app.get(self.uri_for('transaction.add_credit'))
    redirect_url = self.uri_for(
        'login', redirect=self.uri_for('transaction.add_credit'))
    self.assertRedirects(response, redirect_url)

  @testing.logged_in
  def test_view_add_credit_page_logged_in(self):
    response = self.app.get(self.uri_for('transaction.add_credit'))
    self.assertOk(response)
    self.assertLength(1, response.pyquery('table.funding-sources'))
    # Check that add credit button is present.
    self.assertLength(1, response.pyquery('.span12 button'))
    self.assertTemplateUsed('transaction_add_credit.haml')

  @testing.logged_in
  def test_add_credit_transaction_added_to_queue(self):
    funding_source = self.create_funding_source(
        parent=self.get_current_profile(),
        status=FundingSource.Status.Accepted)

    params = {'amount': '20.00', 'funding_source': str(funding_source.key())}
    response = self.app.post(self.uri_for('transaction.add_credit'), params)
    self.assertRedirects(response, self.uri_for('home'))

    # Check that the tranasction processing job has been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(1, tasks)

    # Check that the transaction has been created.
    self.assertLength(1, Transaction.all())

    # Check that the transaction has a task queued to process it.
    task, = tasks
    params = task.extract_params()
    transaction = Transaction.all().get()
    self.assertEqual(str(transaction.key()), params['transaction_key'])
    self.assertEqual(self.uri_for('transaction.process'), task.url)

    # Check that the transaction starts with the correct status.
    self.assertEqual(transaction.Status.Pending, transaction.status)

    # Run the transaction processing job and verify that it is successful.
    with mock.patch('stripe.Charge.create') as stripe_charge:
      stripe_charge.return_value = mock.Mock(id='ch_1stsWjqBqYSOtr')
      response = self.app.post(task.url, params,
                               headers=self.TASKQUEUE_HEADERS)
    self.assertOk(response)

    # Reload transaction from the data store and ensure the status changed.
    transaction, = Transaction.all()
    self.assertEqual(transaction.Status.Completed, transaction.status)

    # Reload the profile from the data store and check that the balance has
    # been updated.
    profile = Profile.get(self.current_profile.key())
    self.assertEqual(2000, profile.usd_balance)

  def test_add_credit_not_logged_in(self):
    params = {'amount': '20.00', 'funding_source': 'Fake'}
    response = self.app.post(self.uri_for('transaction.add_credit'),
                             params)

    redirect_url = self.uri_for('transaction.add_credit')
    self.assertRedirects(response,
                         self.uri_for('login', redirect=redirect_url))

  def test_invalid_transaction_key_logs_error(self):
    with mock.patch('logging.error') as logging_error:
      params = {'transaction_key': 'BAD KEY'}
      response = self.app.post(self.uri_for('transaction.process'),
                               params, headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)
      self.assertTrue(logging_error.called)
      self.assertEqual(1, logging_error.call_count)

  @testing.logged_in
  def test_add_credit_fails_without_a_funding_source(self):
    params = {'amount': 20.00, 'funding_source': ''}
    response = self.app.post(self.uri_for('transaction.add_credit'), params)
    self.assertOk(response)
    self.assertFlashMessage(message=error_messages.FUNDING_SOURCE_REQUIRED,
                            level='error', response=response)

    # Ensure no transactions are created.
    self.assertLength(0, Transaction.all())

  @testing.logged_in
  def test_email_is_sent_after_successful_deposit(self):
    profile = self.get_current_profile()
    funding_source = self.create_funding_source(
        parent=profile, status=FundingSource.Status.Accepted)

    params = {'amount': '20.00', 'funding_source': str(funding_source.key())}
    response = self.app.post(self.uri_for('transaction.add_credit'), params)
    self.assertRedirects(response, self.uri_for('home'))

    # Check that the tranasction processing job has been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('transaction.process'))
    self.assertLength(1, tasks)

    # Check that the transaction has a task queued to process it.
    task, = tasks
    params = task.extract_params()
    transaction = Transaction.all().get()
    self.assertEqual(str(transaction.key()), params['transaction_key'])
    self.assertEqual(self.uri_for('transaction.process'), task.url)

    # Run the transaction processing job and verify that it is successful.
    with mock.patch('stripe.Charge.create') as stripe_charge:
      stripe_charge.return_value = mock.Mock(id='ch_1stsWjqBqYSOtr')
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
    profile = self.get_current_profile()
    message, = messages
    self.assertEqual('"%s" <%s>' % (profile.name, profile.email), message.to)
    self.assertEqual(email.DEPOSIT_SUBJECT, message.subject)
    self.assertEqual(constants.FULL_NO_REPLY_EMAIL, message.sender)
    self.assertEqual(constants.FULL_SUPPORT_EMAIL, message.reply_to)
    self.assertTemplateUsed('emails/transaction.haml')

    email_greeting = PyQuery(message.html.decode())('h3.email_greeting')
    self.assertEqual('Hi %s,' % profile.name, email_greeting.text())

    email_message = PyQuery(message.html.decode())('p.email_message')
    self.assertEqual(email.DEPOSIT_MESSAGE, email_message.text())

    email_table = PyQuery(message.html.decode())('tbody td')
    self.assertEqual(format_datetime(transaction.get_recipient_time()),
                     email_table.filter('.email_time').text())
    self.assertEqual(transaction.get_transaction_amount(),
                     format(email_table.filter('.email_amount').text()))
    self.assertEqual(Transaction.Status.Completed,
                     email_table.filter('.email_status').text())

  @testing.logged_in
  def test_email_is_not_sent_after_unsuccessful_deposit(self):
    params = {'amount': 20.00, 'funding_source': ''}
    response = self.app.post(self.uri_for('transaction.add_credit'), params)
    self.assertOk(response)

    # Ensure no transactions are created and no mail sending task is in queue.
    self.assertLength(0, Transaction.all())
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_add_credit_fails_with_invalid_funding_source(self):
    params = {'amount': 20.00, 'funding_source': 'INVALID'}
    response = self.app.post(self.uri_for('transaction.add_credit'), params)
    self.assertFlashMessage(message=error_messages.FUNDING_SOURCE_NOT_FOUND,
                            level='error', response=response)
    self.assertLength(0, Transaction.all())
    self.assertEqual(0, self.get_current_profile().usd_balance)

  @testing.logged_in
  def test_add_credit_fails_with_unauthorized_funding_source(self):
    funding_source = self.create_funding_source()
    params = {'amount': 20, 'funding_source': str(funding_source.key())}
    response = self.app.post(self.uri_for('transaction.add_credit'), params)
    self.assertFlashMessage(message=error_messages.UNAUTHORIZED_FUNDING_SOURCE,
                            level='error', response=response)
    self.assertLength(0, Transaction.all())
    self.assertEqual(0, self.get_current_profile().usd_balance)
