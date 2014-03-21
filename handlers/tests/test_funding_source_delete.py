import mock
import stripe
import unittest2

from library import testing
from models.funding_source import FundingSource


class TestFundingSourceDelete(testing.TestCase, unittest2.TestCase):

  def test_post_funding_source_delete_delete_not_logged_in(self):
    funding_source = self.create_funding_source()
    params = {'funding_source': str(funding_source.key())}
    response = self.app.post(self.uri_for('funding_source.delete'), params)
    login_url = self.uri_for(
        'login', redirect=self.uri_for('funding_source.delete'))
    self.assertRedirects(response, login_url)

    # Ensure no tasks were dispatched.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('funding_source.delete_stripe_customer'))
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_post_funding_source_delete_delete_wrong_profile(self):
    with mock.patch('logging.error') as error_logger:
      funding_source = self.create_funding_source()
      params = {'funding_source': str(funding_source.key())}
      response = self.app.post(self.uri_for('funding_source.delete'), params,
                               status=404)
      self.assertNotFound(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

    # Ensure no tasks were dispatched.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('funding_source.delete_stripe_customer'))
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_post_funding_source_delete_empty_funding_source(self):
    with mock.patch('logging.error') as error_logger:
      params = {'funding_source': ''}
      response = self.app.post(self.uri_for('funding_source.delete'), params,
                               status=404)
      self.assertNotFound(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

    # Ensure no tasks were dispatched.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('funding_source.delete_stripe_customer'))
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_post_funding_source_delete_invalid_funding_source(self):
    # Ensure the error was logged.
    with mock.patch('logging.error') as error_logger:
      params = {'funding_source': 'INVALID'}
      response = self.app.post(self.uri_for('funding_source.delete'), params,
                               status=404)
      self.assertNotFound(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

    # Ensure no tasks were dispatched.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('funding_source.delete_stripe_customer'))
    self.assertLength(0, tasks)

  @testing.logged_in
  def test_post_funding_source_delete_logged_in(self):
    current_profile = self.get_current_profile()
    funding_source = self.create_funding_source(parent=current_profile)
    params = {'funding_source': str(funding_source.key())}
    response = self.app.post(self.uri_for('funding_source.delete'), params)
    self.assertRedirects(response, self.uri_for('profile.view'))

    # Ensure the funding source has been deleted.
    self.assertLength(0, FundingSource.all())

    # Ensure a task has been dispatched to delete the funding source.
    tasks = self.taskqueue_stub.get_filtered_tasks(
        url=self.uri_for('funding_source.delete_stripe_customer'))
    self.assertLength(1, tasks)

    # Ensure the task has the correct parameters.
    task, = tasks
    params = task.extract_params()
    self.assertEqual(funding_source.customer_id, params['customer_id'])

    # Mock out the Stripe API calls.
    with mock.patch('stripe.Customer.retrieve') as retrieve_customer:
      retrieve_customer.return_value = mock.MagicMock(spec=stripe.Customer)
      customer = retrieve_customer.return_value
      response = self.app.post(task.url, params,
                               headers=self.TASKQUEUE_HEADERS)
      self.assertOk(response)

      # Ensure the Stripe API was called correctly.
      self.assertTrue(retrieve_customer.called)
      self.assertTrue(customer.delete.called)
      self.assertEqual(1, retrieve_customer.call_count)
      self.assertEqual(1, customer.delete.call_count)

  def test_funding_source_delete_stripe_customer_outside_of_taskqueue(self):
    funding_source = self.create_funding_source()

    # Ensure error is logged.
    with mock.patch('logging.error') as error_logger:
      params = {'funding_source': str(funding_source.key())}
      response = self.app.post(
          self.uri_for('funding_source.delete_stripe_customer'), params)
      self.assertOk(response)
      self.assertTrue(error_logger.called)
      self.assertEqual(1, error_logger.call_count)

    # Ensure funding source has not been deleted.
    self.assertLength(1, FundingSource.all())

  def test_funding_source_delete_stripe_customer_no_customer(self):
    with mock.patch('stripe.Customer.retrieve') as retrieve_customer:
      with mock.patch('logging.error') as error_logger:
        retrieve_customer.return_value = None
        params = {'customer_id': self.DEFAULT_STRIPE_CUSTOMER_ID}
        response = self.app.post(
            self.uri_for('funding_source.delete_stripe_customer'), params,
            headers=self.TASKQUEUE_HEADERS)
        self.assertOk(response)
        self.assertTrue(error_logger.called)
        self.assertEqual(1, error_logger.call_count)

  def test_funding_source_delete_stripe_customer_stripe_connection_error(self):
    with mock.patch('stripe.Customer.retrieve') as retrieve_customer:
      with mock.patch('logging.exception') as exception_logger:
        retrieve_customer.return_value = mock.MagicMock(spec=stripe.Customer)
        customer = retrieve_customer.return_value
        customer.delete.side_effect = stripe.APIConnectionError()
        params = {'customer_id': self.DEFAULT_STRIPE_CUSTOMER_ID}

        # Ensure the response has a 500, causing the task to retry.
        response = self.app.post(
            self.uri_for('funding_source.delete_stripe_customer'), params,
            headers=self.TASKQUEUE_HEADERS, status=500)
        self.assertEqual(500, response.status_int)

        # Ensure the exception is logged.
        # It's logged twice, since the 500 handler logs exceptions as well.
        self.assertTrue(exception_logger.called)
        self.assertEqual(2, exception_logger.call_count)

  def test_funding_source_delete_stripe_customer_exception(self):
    with mock.patch('stripe.Customer.retrieve') as retrieve_customer:
      with mock.patch('logging.error') as error_logger:
        with mock.patch('logging.exception') as exception_logger:
          retrieve_customer.return_value = mock.MagicMock(spec=stripe.Customer)
          customer = retrieve_customer.return_value
          customer.delete.side_effect = Exception
          params = {'customer_id': self.DEFAULT_STRIPE_CUSTOMER_ID}

          response = self.app.post(
              self.uri_for('funding_source.delete_stripe_customer'), params,
              headers=self.TASKQUEUE_HEADERS)
          self.assertOk(response)

          # Ensure the error and exception are logged.
          self.assertTrue(error_logger.called)
          self.assertTrue(exception_logger.called)
          self.assertEqual(1, error_logger.call_count)
          self.assertEqual(1, exception_logger.call_count)

  def test_funding_source_delete_stripe_customer_invalid_request(self):
    # Simulate an invalid customer ID.
    with mock.patch('stripe.Customer.retrieve') as retrieve_customer:
      with mock.patch('logging.error') as error_logger:
        with mock.patch('logging.exception') as exception_logger:
          # `stripe.InvalidRequestError constructor requires params
          # `message` and `param`.
          retrieve_customer.side_effect = stripe.InvalidRequestError(
              message='', param='')
          params = {'customer_id': self.DEFAULT_STRIPE_CUSTOMER_ID}
          response = self.app.post(
              self.uri_for('funding_source.delete_stripe_customer'), params,
              headers=self.TASKQUEUE_HEADERS)
          self.assertOk(response)

          # Ensure the error and exception are logged.
          self.assertTrue(error_logger.called)
          self.assertTrue(exception_logger.called)
          self.assertEqual(1, error_logger.call_count)
          self.assertEqual(1, exception_logger.call_count)
