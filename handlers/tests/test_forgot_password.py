from google.appengine.ext import deferred
import unittest2

from library import constants
from library import testing
from models.profile import Profile


class TestForgotPassword(testing.TestCase, unittest2.TestCase):

  @testing.logged_in
  def test_forgot_password_already_logged_in(self):
    response = self.app.get(self.uri_for('forgot-password'))
    self.assertRedirects(response, self.uri_for('home'))

  def test_forgot_password_get_first_page(self):
    self.assertNotLoggedIn()
    response = self.app.get(self.uri_for('forgot-password'))
    self.assertTemplateUsed('forgot_password.haml')
    self.assertTemplateUsed('components/forgot_password_form.haml')
    self.assertLength(1, response.pyquery('form#forgot-password'))
    self.assertLength(1, response.pyquery('input[name="email"]'))

  def test_forgot_password_post_via_form(self):
    self.assertNotLoggedIn()
    profile = self.create_profile()
    response = self.app.get(self.uri_for('forgot-password'))
    form = response.forms['forgot-password']
    form['email'] = profile.email
    response = form.submit()
    self.assertOk(response)
    self.assertTemplateUsed('forgot_password.haml')
    self.assertTemplateNotUsed('components/forgot_password_form.haml')

  def test_forgot_password_post_sends_email(self):
    self.assertNotLoggedIn()
    profile = self.create_profile()
    response = self.app.get(self.uri_for('forgot-password'))
    form = response.forms['forgot-password']
    form['email'] = profile.email
    response = form.submit()

    # Check the task was put on the mail queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertIn('mail', tasks[0].headers['X-AppEngine-QueueName'])
    task, = tasks
    deferred.run(task.payload)
    messages = self.mail_stub.get_sent_messages()
    self.assertLength(1, messages)
    message, = messages
    profile = Profile.get(profile.key())

    # Reload profile to get new activation key.
    self.assertEqual('"%s" <%s>' % (profile.name, profile.email),
                     message.to)
    self.assertEqual('"Blaze" <%s>' % constants.NO_REPLY_EMAIL,
                     message.sender)
    self.assertEqual('"Blaze Support" <%s>' % constants.SUPPORT_EMAIL,
                     message.reply_to)
    self.assertIn(profile.activation_key, message.body.decode())
    self.assertIn(profile.activation_key, message.html.decode())

    recover_uri = self.uri_for('forgot-password', k=profile.activation_key)
    self.assertIn(recover_uri, message.body.decode())
    self.assertIn(recover_uri, message.html.decode())

  def test_forgot_password_email_has_proper_public_host(self):
    self.assertNotLoggedIn()
    profile = self.create_profile()
    response = self.app.get(self.uri_for('forgot-password'))
    form = response.forms['forgot-password']
    form['email'] = profile.email
    response = form.submit()

    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertIn('mail', tasks[0].headers['X-AppEngine-QueueName'])
    task, = tasks
    deferred.run(task.payload)
    messages = self.mail_stub.get_sent_messages()
    self.assertLength(1, messages)
    message, = messages
    self.assertNotIn('http://localhost', message.body.decode())
    self.assertNotIn('http://localhost', message.html.decode())
    self.assertIn(constants.PUBLIC_DOMAIN, message.body.decode())
    self.assertIn(constants.PUBLIC_DOMAIN, message.html.decode())

  def test_forgot_password_post_resets_activation_key(self):
    profile = self.create_profile()
    old_activation_key = profile.activation_key

    params = {'email': profile.email}
    response = self.app.post(self.uri_for('forgot-password'), params)
    self.assertOk(response)
    profile = Profile.get(profile.key())
    self.assertNotEqual(old_activation_key, profile.activation_key)

  def test_forgot_password_post_with_invalid_email(self):
    # This should just say that we will try to send an e-mail to that
    # address.
    print "test_forgot_password_post_with_invalid_email"
    params = {'email': 'not an email'}
    response = self.app.post(self.uri_for('forgot-password'), params)
    self.assertOk(response)
    self.assertTemplateUsed('forgot_password.haml')

  def test_forgot_password_post_with_missing_email(self):
    # We should show the form again like nothing happened.
    response = self.app.post(self.uri_for('forgot-password'), {})
    self.assertRedirects(response, self.uri_for('forgot-password'))

  def test_forgot_password_post_with_email_trailing_whitespace(self):
    profile = self.create_profile()
    params = {'email': profile.email + '   '}
    response = self.app.post(self.uri_for('forgot-password'), params)
    self.assertOk(response)

    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertIn('mail', tasks[0].headers['X-AppEngine-QueueName'])
    task, = tasks
    deferred.run(task.payload)
    self.assertLength(1, self.mail_stub.get_sent_messages())
    message, = self.mail_stub.get_sent_messages()
    profile = Profile.get(profile.key())
    self.assertEqual('"%s" <%s>' % (profile.name, profile.email), message.to)

  def test_forgot_password_post_with_email_whitespace_only(self):
    # We should show the form again like nothing happened.
    params = {'email': '     '}
    response = self.app.post(self.uri_for('forgot-password'), params)
    self.assertRedirects(response, self.uri_for('forgot-password'))

  def test_forgot_password_post_with_email_not_member(self):
    params = {'email': 'test@example.org'}
    self.assertIsNone(Profile.get_by_email(params['email']))
    response = self.app.post(self.uri_for('forgot-password'), params)
    self.assertOk(response)
    self.assertTemplateUsed('forgot_password.haml')

  def test_forgot_password_post_doesnt_have_form(self):
    params = {'email': 'test@example.org'}
    self.assertIsNone(Profile.get_by_email(params['email']))
    response = self.app.post(self.uri_for('forgot-password'), params)
    self.assertOk(response)
    self.assertTemplateUsed('forgot_password.haml')
    self.assertLength(0, response.pyquery('form'))

  def test_forgot_password_get_with_key(self):
    profile = self.create_profile()
    key = profile.activation_key
    response = self.app.get(self.uri_for('forgot-password', k=key))
    self.assertOk(response)
    self.assertTemplateUsed('forgot_password.haml')
    self.assertTemplateUsed('components/forgot_password_form.haml')
    self.assertLength(1, response.pyquery('form'))
    self.assertLength(1, response.pyquery('input#email'))
    self.assertLength(1, response.pyquery('input[name="password"]'))
    self.assertEqual(profile.email, response.pyquery('input#email').val())

  def test_forgot_password_get_with_empty_key(self):
    response = self.app.get(self.uri_for('forgot-password', k=''))
    self.assertOk(response)
    self.assertTemplateUsed('forgot_password.haml')
    self.assertTemplateUsed('components/forgot_password_form.haml')
    self.assertLength(1, response.pyquery('input[name="email"]'))

  def test_forgot_password_get_with_invalid_key(self):
    response = self.app.get(self.uri_for('forgot-password', k='invalid'))
    self.assertOk(response)
    self.assertTemplateUsed('forgot_password.haml')
    self.assertTemplateUsed('components/forgot_password_form.haml')
    self.assertLength(1, response.pyquery('input[name="email"]'))

  def test_forgot_password_submit_form_password_empty(self):
    profile = self.create_profile()
    key = profile.activation_key
    response = self.app.get(self.uri_for('forgot-password', k=key))
    form = response.forms['forgot-password']
    form['password'] = ''
    response = form.submit()
    self.assertRedirects(response, self.uri_for('forgot-password', k=key))

  def test_forgot_password_submit_form_password_whitespace_only(self):
    profile = self.create_profile()
    key = profile.activation_key
    response = self.app.get(self.uri_for('forgot-password', k=key))
    form = response.forms['forgot-password']
    form['password'] = '    '
    response = form.submit()
    self.assertRedirects(response, self.uri_for('forgot-password', k=key))

  def test_forgot_password_submit_form_password_trailing_whitespace(self):
    profile = self.create_profile()
    key = profile.activation_key
    response = self.app.get(self.uri_for('forgot-password', k=key))
    form = response.forms['forgot-password']
    form['password'] = 'test     '
    response = form.submit()
    self.assertRedirects(response, self.uri_for('home'))
    self.logout()
    self.assertNotLoggedIn()

    params = {'email': profile.email, 'password': 'test'}
    response = self.app.post(self.uri_for('login'), params)
    self.assertRedirects(response)
    self.assertLoggedIn()

  def test_forgot_password_post_with_key_password_missing(self):
    profile = self.create_profile()
    key = profile.activation_key
    response = self.app.post(self.uri_for('forgot-password', k=key), {})
    self.assertRedirects(response, self.uri_for('forgot-password', k=key))

  def test_forgot_password_submit_with_valid_password_updates_password(self):
    profile = self.create_profile()
    key = profile.activation_key
    response = self.app.get(self.uri_for('forgot-password', k=key))
    form = response.forms['forgot-password']
    form['password'] = 'my-new-password'
    response = form.submit()
    self.assertRedirects(response, self.uri_for('home'))
    self.logout()
    self.assertNotLoggedIn()
    params = {'email': profile.email, 'password': 'my-new-password'}
    response = self.app.post(self.uri_for('login'), params)
    self.assertRedirects(response)
    self.assertLoggedIn()

  def test_forgot_password_submit_form_logs_you_in_if_beta_tester(self):
    profile = self.create_profile()
    key = profile.activation_key
    response = self.app.get(self.uri_for('forgot-password', k=key))
    form = response.forms['forgot-password']
    form['password'] = 'my-new-password'
    response = form.submit()
    self.assertRedirects(response, self.uri_for('home'))
    self.assertLoggedIn()

  def test_forgot_password_submit_form_redirects_if_not_beta_tester(self):
    profile = self.create_profile(beta_tester=False)
    key = profile.activation_key
    response = self.app.get(self.uri_for('forgot-password', k=key))
    form = response.forms['forgot-password']
    form['password'] = 'my-new-password'
    response = form.submit()
    profile = Profile.get(profile.key())
    self.assertNotLoggedIn()
    self.assertRedirects(response, self.uri_for('home'))
    self.assertNotLoggedIn()

  def test_forgot_password_lowercase_email(self):
    profile = self.create_profile(beta_tester=False)
    response = self.app.get(self.uri_for('forgot-password'))
    form = response.forms['forgot-password']
    form['email'] = profile.email.upper()
    response = form.submit()
    self.assertOk(response)
    self.assertNotLoggedIn()

    # Ensure the password has been reset.
    profile = Profile.get(profile.key())
    response = self.app.get(
        self.uri_for('forgot-password', k=profile.activation_key))
    self.assertOk(response)
    form = response.forms['forgot-password']
    form['password'] = 'new-password'
    response = form.submit()
    self.assertRedirects(response, self.uri_for('home'))
