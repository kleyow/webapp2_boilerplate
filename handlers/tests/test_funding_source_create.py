import mock
import stripe
import unittest2

from library import testing
from models.funding_source import FundingSource


class TestFundingSource(testing.TestCase, unittest2.TestCase):

  def test_create_funding_source_not_logged_in(self):
    params = {'card_token': 'CARD_TOKEN', 'card_last_four_digits': '4242',
              'card_exp_month': '10', 'card_exp_year': '2040'}
    response = self.app.post(self.uri_for('funding_source.create'), params)
    login_url = self.uri_for('login',
                             redirect=self.uri_for('funding_source.create'))
    self.assertRedirects(response, login_url)

  @testing.logged_in
  def test_create_funding_source_logged_in(self):
    params = {'card_token': 'CARD_TOKEN', 'card_last_four_digits': '4242',
              'card_exp_month': '10', 'card_exp_year': '2040'}
    response = self.app.post(self.uri_for('funding_source.create'), params)
    self.assertRedirects(response, self.uri_for('profile.view'))

    # Ensure a funding source has been added to the database.
    self.assertLength(1, FundingSource.all())
    funding_source = FundingSource.all().get()
    self.assertEqual(params['card_token'], funding_source.card_token)
    self.assertEqual(params['card_last_four_digits'],
                     funding_source.last_four_digits)
    self.assertEqual(params['card_exp_month'], funding_source.exp_month)
    self.assertEqual(params['card_exp_year'], funding_source.exp_year)

    # Ensure a task has been added to the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('funding_source.create_stripe_customer'))
    self.assertLength(1, tasks)
    task, = tasks
    params = task.extract_params()
    self.assertEqual(str(funding_source.key()), params['funding_source'])

    # Execute the task, and ensure the customer was created.
    with mock.patch('stripe.Customer.create') as create_stripe_customer:
      create_stripe_customer.return_value = mock.Mock(id='42')
      response = self.app.post(
          self.uri_for('funding_source.create_stripe_customer'), params,
          headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)

    # Ensure the funding source is updated with the customer ID.
    funding_source = FundingSource.get(funding_source.key())
    self.assertEqual('42', funding_source.customer_id)

  def test_create_stripe_customer_fails_outside_of_taskqueue(self):
    funding_source = FundingSource(parent=self.create_profile())
    funding_source.put()

    # Ensure stripe customer requests cannot be processed outside of taskqueue.
    with mock.patch('logging.error') as error_logger:
      params = {'funding_source': str(funding_source.key())}
      response = self.app.post(
          self.uri_for('funding_source.create_stripe_customer'), params)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

    # Ensure funding source has not been updated with a customer id.
    funding_source = FundingSource.get(funding_source.key())
    self.assertIsNone(funding_source.customer_id)

  def test_invalid_credit_card_fails(self):
    funding_source = FundingSource(parent=self.create_profile())
    funding_source.put()

    # Simulate an invalid credit card, and ensure the error is logged.
    with mock.patch('stripe.Customer.create') as create_customer:
      with mock.patch('logging.exception') as exception_logger:
        # stripe.CardError takes 3 args: message, param and code. Since we
        # don't have any use for them in this test, just use dummy strings.
        create_customer.side_effect = stripe.CardError('message', 'param',
                                                       'code')
        params = {'funding_source': str(funding_source.key())}
        response = self.app.post(
            self.uri_for('funding_source.create_stripe_customer'), params,
            headers=self.TASKQUEUE_HEADERS)
        self.assertOk(response)

        self.assertTrue(exception_logger.called)
        self.assertEqual(1, exception_logger.call_count)

    # Reload the funding source and ensure it has been rejected, and has not
    # been given a customer id.
    funding_source = FundingSource.get(funding_source.key())
    self.assertIsNone(funding_source.customer_id)
    self.assertEqual(FundingSource.Status.Rejected, funding_source.status)

  def test_invalid_funding_source_key_fails(self):
    with mock.patch('logging.error') as error_logger:
      params = {'funding_source': 'INVALID_KEY'}
      response = self.app.post(
          self.uri_for('funding_source.create_stripe_customer'), params,
          headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

  def test_rejected_funding_source_cannot_be_replayed(self):
    funding_source = FundingSource(parent=self.create_profile())
    funding_source.status = FundingSource.Status.Rejected
    funding_source.put()

    with mock.patch('logging.error') as error_logger:
      params = {'funding_source': str(funding_source.key())}
      response = self.app.post(
          self.uri_for('funding_source.create_stripe_customer'), params,
          headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

  def test_accepted_funding_source_cannot_be_replayed(self):
    funding_source = FundingSource(parent=self.create_profile())
    funding_source.status = FundingSource.Status.Accepted
    funding_source.put()

    with mock.patch('logging.error') as error_logger:
      params = {'funding_source': str(funding_source.key())}
      response = self.app.post(
          self.uri_for('funding_source.create_stripe_customer'), params,
          headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)
