from google.appengine.ext import deferred
from pyquery import PyQuery
import unittest2

from forms import error_messages
from library import constants, testing
from models.profile import Profile


class TestProfileUpdateHandler(testing.TestCase, unittest2.TestCase):
  UPDATE_DATA = {'name': 'New Test Name', 'email': 'newtest@example.org',
                 'new_password': 'newpass', 'pin': 2345,
                 'old_password': 'passwr0d'}

  @testing.logged_in
  def test_update_page_renders_to_logged_in_users(self):
    response = self.app.get(self.uri_for('profile.update'))
    self.assertOk(response)
    self.assertTemplateUsed('update_profile.haml')

  def test_update_page_redirects_non_users(self):
    response = self.app.get(self.uri_for('profile.update'))
    self.assertRedirects(response)

  @testing.logged_in
  def test_update_inputs_have_proper_types(self):
    # We rely on some client-side browser-built-in validation with fields,
    # so we should check that we don't accidentally change an email field
    # to a text field.
    response = self.app.get(self.uri_for('profile.update'))

    email_field = response.pyquery('input#email')
    self.assertLength(1, email_field)
    self.assertEqual('email', email_field.attr['type'])
    self.assertEqual('email', email_field.attr['name'])
    self.assertEqual('test@example.org', email_field.attr['value'])

    name_field = response.pyquery('input#name')
    self.assertLength(1, name_field)
    self.assertEqual('text', name_field.attr['type'])
    self.assertEqual('name', name_field.attr['name'])

    old_password_field = response.pyquery('input#old-password')
    self.assertLength(1, old_password_field)
    self.assertEqual('password', old_password_field.attr['type'])
    self.assertEqual('old_password', old_password_field.attr['name'])

    new_password_field = response.pyquery('input#new-password')
    self.assertLength(1, new_password_field)
    self.assertEqual('password', new_password_field.attr['type'])
    self.assertEqual('new_password', new_password_field.attr['name'])

    pin_field = response.pyquery('input#pin')
    self.assertLength(1, pin_field)
    self.assertEqual('password', pin_field.attr['type'])
    self.assertEqual('pin', pin_field.attr['name'])

  @testing.logged_in
  def test_update_page_flow_without_old_password(self):

    profile = self.get_current_profile()
    data = {'email': self.UPDATE_DATA['email'],
            'new_password': self.UPDATE_DATA['new_password'],
            'name': self.UPDATE_DATA['name'],
            'pin': self.UPDATE_DATA['pin']}

    response = self.app.post(self.uri_for('profile.update'), data)

    self.assertOk(response, self.uri_for('profile.update'))

    # Reload profile to ensure user info hasn't changed.
    profile = Profile.get(profile.key())

    self.assertEqual(testing.TestCase.DEFAULT_PROFILE_NAME, profile.name)
    self.assertEqual(testing.TestCase.DEFAULT_EMAIL, profile.email)
    self.assertTrue(profile.check_pin(testing.TestCase.DEFAULT_UNHASHED_PIN))
    self.assertNotEqual(self.UPDATE_DATA['pin'], profile.pin)

    self.logout()
    response = self.login(self.UPDATE_DATA['email'],
                          self.UPDATE_DATA['new_password'])

    self.assertNotLoggedIn()
    self.assertOk(response, self.uri_for('login'))

  @testing.logged_in
  def test_update_page_flow_with_invalid_old_password(self):

    profile = self.get_current_profile()
    data = {'email': self.UPDATE_DATA['email'],
            'new_password': self.UPDATE_DATA['new_password'],
            'old_password': 'wrong_password',
            'name': self.UPDATE_DATA['name'],
            'pin': self.UPDATE_DATA['pin']}

    response = self.app.post(self.uri_for('profile.update'), data)

    self.assertOk(response, self.uri_for('profile.update'))

    # Reload profile to ensure user info hasn't changed.
    profile = Profile.get(profile.key())

    self.assertEqual(testing.TestCase.DEFAULT_PROFILE_NAME, profile.name)
    self.assertEqual(testing.TestCase.DEFAULT_EMAIL, profile.email)
    self.assertTrue(profile.check_pin(testing.TestCase.DEFAULT_UNHASHED_PIN))
    self.assertNotEqual(self.UPDATE_DATA['pin'], profile.pin)

    self.logout()
    response = self.login(self.UPDATE_DATA['email'],
                          self.UPDATE_DATA['new_password'])

    self.assertNotLoggedIn()
    self.assertOk(response, self.uri_for('login'))

  @testing.logged_in
  def test_update_page_flow(self):

    profile = self.get_current_profile()
    data = {'email': self.UPDATE_DATA['email'],
            'new_password': self.UPDATE_DATA['new_password'],
            'old_password': self.UPDATE_DATA['old_password'],
            'name': self.UPDATE_DATA['name'],
            'pin': self.UPDATE_DATA['pin']}

    response = self.app.post(self.uri_for('profile.update'), data)

    self.assertRedirects(response, self.uri_for('home'))

    # Reload profile to get updated profile name.
    profile = Profile.get(profile.key())

    self.assertEqual(self.UPDATE_DATA['name'], profile.name)
    self.assertEqual(self.UPDATE_DATA['email'], profile.email)
    self.assertTrue(profile.check_pin(self.UPDATE_DATA['pin']))
    self.assertNotEqual(self.UPDATE_DATA['pin'], profile.pin)
    self.assertIsNotNone(profile.activation_key)

    self.logout()
    response = self.login(email=self.UPDATE_DATA['email'],
                          password=self.UPDATE_DATA['new_password'])

    self.assertRedirects(response, self.uri_for('home'))

  @testing.logged_in
  def test_profile_update_invalid_email(self):
    profile_email = self.get_current_profile().email
    data = {'email': 'INVALID',
            'old_password': self.UPDATE_DATA['old_password']}
    response = self.app.post(self.uri_for('profile.update'), data)
    self.assertFlashMessage(message=error_messages.INVALID_EMAIL,
                            level='error', response=response)

    # Ensure the email has not changed.
    profile = Profile.get(self.get_current_profile().key())
    self.assertEqual(profile_email, profile.email)

  @testing.logged_in
  def test_email_alone_submitted(self):
    profile = self.get_current_profile()
    response = self.app.get(self.uri_for('profile.update'))
    form = response.forms['update-form']
    form['email'] = self.UPDATE_DATA['email']
    form['old_password'] = self.UPDATE_DATA['old_password']
    response = form.submit()
    profile = Profile.get(profile.key())
    self.assertRedirects(response, self.uri_for('home'))
    self.assertEqual(self.UPDATE_DATA['email'], profile.email)
    self.assertEqual('Test Profile', profile.name)
    self.assertTrue(profile.check_pin('1234'))
    self.logout()
    response = self.login(self.UPDATE_DATA['email'],
                          self.UPDATE_DATA['old_password'])
    self.assertRedirects(response, self.uri_for('home'))

  @testing.logged_in
  def test_name_alone_submitted(self):
    profile = self.get_current_profile()
    response = self.app.get(self.uri_for('profile.update'))
    form = response.forms['update-form']
    form['name'] = self.UPDATE_DATA['name']
    form['old_password'] = self.UPDATE_DATA['old_password']
    response = form.submit()
    profile = Profile.get(profile.key())
    self.assertRedirects(response, self.uri_for('home'))
    self.assertEqual(self.UPDATE_DATA['name'], profile.name)
    self.assertEqual('test@example.org', profile.email)
    self.assertTrue(profile.check_pin('1234'))
    self.logout()
    response = self.login(email=profile.email)
    self.assertRedirects(response, self.uri_for('home'))

  @testing.logged_in
  def test_password_alone_submitted(self):
    profile = self.get_current_profile()
    response = self.app.get(self.uri_for('profile.update'))
    form = response.forms['update-form']
    form['new_password'] = self.UPDATE_DATA['new_password']
    form['old_password'] = self.UPDATE_DATA['old_password']
    response = form.submit()
    self.assertRedirects(response, self.uri_for('home'))
    profile = Profile.get(profile.key())
    self.assertEqual('test@example.org', profile.email)
    self.assertTrue(profile.check_pin('1234'))
    self.assertEqual('Test Profile', profile.name)

    self.logout()
    response = self.login(password=self.UPDATE_DATA['new_password'])
    self.assertRedirects(response, self.uri_for('home'))

  @testing.logged_in
  def test_pin_alone_submitted(self):
    profile = self.get_current_profile()
    response = self.app.get(self.uri_for('profile.update'))
    form = response.forms['update-form']
    form['pin'] = self.UPDATE_DATA['pin']
    form['old_password'] = self.UPDATE_DATA['old_password']
    response = form.submit()
    profile = Profile.get(profile.key())
    self.assertRedirects(response, self.uri_for('home'))
    self.assertTrue(profile.check_pin(self.UPDATE_DATA['pin']))
    self.assertEqual('Test Profile', profile.name)
    self.logout()
    response = self.login()
    self.assertRedirects(response, self.uri_for('home'))

  @testing.logged_in
  def test_name_doesnt_require_password_to_update(self):
    profile = self.get_current_profile()
    response = self.app.get(self.uri_for('profile.update'))
    form = response.forms['update-form']
    form['name'] = self.UPDATE_DATA['name']
    # Blank out email since it's auto-populated.
    form['email'] = ''
    response = form.submit()
    profile = Profile.get(profile.key())
    self.assertRedirects(response, self.uri_for('home'))
    self.assertEqual(self.UPDATE_DATA['name'], profile.name)
    self.assertEqual('test@example.org', profile.email)
    self.assertTrue(profile.check_pin('1234'))
    self.logout()
    response = self.login(email=profile.email)
    self.assertRedirects(response, self.uri_for('home'))

  @testing.logged_in
  def test_pin_update_requires_password(self):
    profile = self.get_current_profile()
    response = self.app.get(self.uri_for('profile.update'))
    form = response.forms['update-form']
    form['pin'] = self.UPDATE_DATA['pin']
    response = form.submit()
    self.assertFlashMessage(
        message=error_messages.PASSWORD_REQUIRED_UPDATE, level='error',
        response=response)
    profile = Profile.get(profile.key())
    self.assertFalse(profile.check_pin(self.UPDATE_DATA['pin']))

  @testing.logged_in
  def test_update_profile_form_email_marks_profile_inactive(self):
    profile = self.get_current_profile()
    profile.activated = True
    profile.put()

    response = self.app.get(self.uri_for('profile.update'))
    form = response.forms['update-form']
    form['email'] = 'new-email@example.com'
    form['old_password'] = self.UPDATE_DATA['old_password']

    self.assertTrue(profile.activated)
    response = form.submit()
    self.assertRedirects(response)

    # Reload the profile and verify that the profile is not activated.
    profile = Profile.get(profile.key())
    self.assertFalse(profile.activated)

  @testing.logged_in
  def test_update_profile_form_email_changes_activation_key(self):
    profile = self.get_current_profile()
    profile.activated = True
    profile.put()

    old_activation_key = profile.activation_key

    response = self.app.get(self.uri_for('profile.update'))
    form = response.forms['update-form']
    form['email'] = 'new-email@example.com'
    form['old_password'] = self.UPDATE_DATA['old_password']
    response = form.submit()
    self.assertRedirects(response)

    # Reload the profile and verify that the activation key has changed.
    profile = Profile.get(profile.key())
    self.assertNotEqual(old_activation_key, profile.activation_key)

  @testing.logged_in
  def test_update_profile_form_email_sends_activation_message(self):
    profile = self.get_current_profile()
    response = self.app.get(self.uri_for('profile.update'))
    form = response.forms['update-form']
    form['email'] = 'new-email@example.com'
    form['old_password'] = self.UPDATE_DATA['old_password']
    response = form.submit()
    self.assertRedirects(response)

    # Verify that a task was scheduled
    tasks = self.taskqueue_stub.get_filtered_tasks()
    self.assertLength(1, tasks)

    # Run the task and check that an e-mail is sent
    task, = tasks
    deferred.run(task.payload)
    messages = self.mail_stub.get_sent_messages()
    self.assertLength(1, messages)

    profile = Profile.get(profile.key())
    message, = messages
    self.assertEqual('"%s" <%s>' % (profile.name, profile.email), message.to)
    self.assertTemplateUsed('emails/welcome.haml')

    # Ensure the activation link is correct.
    self.assertIsNotNone(profile.activation_key)
    activation_link = '%s%s' % (
        constants.PUBLIC_HOST,
        self.uri_for('profile.activate', k=profile.activation_key))
    message_body = PyQuery(message.html.decode())
    self.assertLength(1, message_body('a[href="%s"]' % activation_link))

  @testing.logged_in
  def test_update_profile_form_email_same_doesnt_mark_as_inactive(self):
    profile = self.get_current_profile()
    profile.activated = True
    profile.put()

    response = self.app.get(self.uri_for('profile.update'))
    form = response.forms['update-form']
    form['email'] = profile.email
    form['old_password'] = self.UPDATE_DATA['old_password']
    response = form.submit()
    self.assertRedirects(response)

    # Reload the profile and verify that the profile is not activated.
    profile = Profile.get(profile.key())
    self.assertTrue(profile.activated)

  @testing.logged_in
  def test_update_profile_form_email_same_doesnt_send_activation_message(self):
    profile = self.get_current_profile()
    response = self.app.get(self.uri_for('profile.update'))
    form = response.forms['update-form']
    form['email'] = profile.email
    form['old_password'] = self.UPDATE_DATA['old_password']
    response = form.submit()
    self.assertRedirects(response)

    # Verify that no tasks were scheduled
    tasks = self.taskqueue_stub.GetTasks('mail')
    self.assertLength(0, tasks)
