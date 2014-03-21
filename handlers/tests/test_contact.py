import unittest2

from google.appengine.ext import deferred

from library import constants
from library import testing


class TestContactHandler(testing.TestCase, unittest2.TestCase):

  def test_get_page(self):
    response = self.app.get(self.uri_for('contact'))
    self.assertOk(response)
    self.assertIn('Contact', response.body)
    self.assertTemplateUsed('contact.haml')

  def test_send_contact_request(self):
    response = self.app.post(self.uri_for('contact'), {
        'name': 'Name', 'email': 'test@example.org', 'topic': 'Nothing',
        'message': 'a msg'})
    self.assertRedirects(response, self.uri_for('contact'))
    self.assertFlashMessage('Thanks! Your message has been sent!')

    # Run the task (it uses the deferred library).
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

  def test_contact_request_invalid_email(self):
    # E-mail is invalid (missing .com at the end).
    with testing.silence_logging():
      response = self.app.post(self.uri_for('contact'), {
          'name': 'Name', 'email': 'test@example', 'topic': 'Nothing',
          'message': 'a msg'})
    self.assertFlashMessage('Your message was unable to be sent!')
    self.assertRedirects(response, self.uri_for('contact'))
