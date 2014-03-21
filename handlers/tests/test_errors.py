from google.appengine.api import memcache
from google.appengine.ext import deferred
import mock
import unittest2

from library import constants, testing


class TestErrorHandler(testing.TestCase, unittest2.TestCase):

  def test_unknown_route_renders_404_page(self):
    self.app.get('/invalid-url/', status=404)
    self.assertTemplateUsed('404.haml')

  def test_unhandled_exception_renders_500_page(self):
    # Simulate an unhandled exception in a handler.
    with mock.patch('handlers.home.HomeHandler.home') as method:
      method.side_effect = Exception

      # Ensure exception is logged.
      with mock.patch('logging.exception') as exception_logger:
        response = self.app.get(self.uri_for('home'), status=500)
        self.assertTemplateUsed('500.haml')
        self.assertTrue(exception_logger.called)

    # Check for form on 500 page.
    self.assertLength(1, response.pyquery('form#report-error'))

  def test_error_report_sends_mail(self):
    error_headers = {'referer': self.uri_for('error.report')}
    params = {'name': 'Test Name', 'email': 'test@example.com',
              'message': 'Test message.'}
    response = self.app.post(self.uri_for('error.report'), params,
                             headers=error_headers)
    self.assertRedirects(response, self.uri_for('home'))
    self.assertFlashMessage(level='success')

    # Run the task.
    tasks = self.taskqueue_stub.get_filtered_tasks()
    self.assertLength(1, tasks)
    task, = tasks
    deferred.run(task.payload)

    # Check the message sender and recipient.
    messages = self.mail_stub.get_sent_messages()
    self.assertLength(1, messages)
    message, = messages
    self.assertEqual(constants.SUPPORT_EMAIL, message.to)
    self.assertEqual(constants.NO_REPLY_EMAIL, message.sender)

  def test_404_error_page_caches_response(self):
    self.assertEqual(0, memcache.get_stats()['items'])

    self.app.get('/invalid-url/', status=404)
    self.assertEqual(1, memcache.get_stats()['items'])
    self.assertEqual(0, memcache.get_stats()['hits'])
    self.assertEqual(1, memcache.get_stats()['misses'])

    self.app.get('/invalid-url/', status=404)
    self.assertEqual(1, memcache.get_stats()['hits'])

  def test_500_error_page_caches_response(self):
    # Simulate an unhandled exception in a handler.
    with mock.patch('handlers.home.HomeHandler.home') as method:
      method.side_effect = Exception

      with mock.patch('logging.exception') as exception_logger:
        self.app.get(self.uri_for('home'), status=500)
        self.assertEqual(1, memcache.get_stats()['items'])
        self.assertEqual(0, memcache.get_stats()['hits'])
        self.assertEqual(1, memcache.get_stats()['misses'])

        self.app.get(self.uri_for('home'), status=500)
        self.assertEqual(1, memcache.get_stats()['hits'])

        # Ensure error is logged.
        self.assertTrue(exception_logger.called)

  def test_post_data_is_not_passed_to_error_report_form(self):
    # Simulate an unhandled exception caused by a POST request to a handler.
    with mock.patch('handlers.contact.ContactHandler.contact') as method:
      method.side_effect = Exception

      with mock.patch('logging.exception') as exception_logger:
        response = self.app.post(self.uri_for('contact'), status=500)

        # Ensure there is no flash message.
        self.assertLength(0, response.pyquery('#notification-bar .alert'))

        # Ensure exception is logged.
        self.assertTrue(exception_logger.called)

  def test_500_error_logs_exception(self):
    # Simulate an unhandled exception in a handler.
    with mock.patch('handlers.home.HomeHandler.home') as method:
      method.side_effect = Exception

      # Ensure the exception was logged.
      with mock.patch('logging.exception') as exception_logger:
        self.app.get(self.uri_for('home'), status=500)
        self.assertTrue(exception_logger.called)
        self.assertEqual(1, exception_logger.call_count)
