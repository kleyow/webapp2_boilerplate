import unittest2

from google.appengine.ext import deferred

from library import constants
from library import testing


class TestPartnerHandler(testing.TestCase, unittest2.TestCase):

  def test_get_page(self):
    self.assertNotLoggedIn()
    response = self.app.get(self.uri_for('partner'))
    self.assertOk(response)
    self.assertTemplateUsed('partner.haml')
    self.assertLength(1, response.pyquery('#partner'))

  def test_send_contact_request(self):
    response = self.app.post(self.uri_for('partner'), {
        'owner_name': 'Name', 'organization_name': 'Buisness',
        'address': 'Nothing', 'email': 'test@test.com',
        'phone_number': '987-9876'})
    self.assertRedirects(response, self.uri_for('partner'))
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
    self.assertEqual(constants.CONTACT_EMAIL, message.to)
    self.assertEqual(constants.NO_REPLY_EMAIL, message.sender)

  def test_contact_request_invalid_email(self):
    # E-mail is invalid (missing .com at the end).
    with testing.silence_logging():
      response = self.app.post(self.uri_for('partner'), {
          'owner_name': 'Name', 'organization_name': 'Buisness',
          'address': 'Nothing', 'email': 'test@test',
          'phone_number': '987-9876'})
    self.assertFlashMessage('Your message was unable to be sent!')
    self.assertRedirects(response, self.uri_for('partner'))
