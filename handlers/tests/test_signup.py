from itertools import chain, combinations

from google.appengine.ext import deferred
import unittest2

from forms import error_messages
from library import constants
from library import testing
from models.profile import Profile


class TestSignupHandler(testing.TestCase, unittest2.TestCase):
  SIGNUP_DATA = {'name': 'Test Name', 'email': 'test@example.org',
                 'password': 'pass', 'pin': '1234'}

  def test_signup(self):
    response = self.app.get(self.uri_for('signup'))
    self.assertOk(response)
    self.assertTemplateUsed('signup.haml')

  def test_signup_inputs_have_proper_types(self):
    # We rely on some client-side browser-built-in validation with fields,
    # so we should check that we don't accidentally change an email field
    # to a text field.
    response = self.app.get(self.uri_for('signup'))

    email_field = response.pyquery('input#email')
    self.assertLength(1, email_field)
    self.assertEqual('email', email_field.attr['type'])
    self.assertEqual('email', email_field.attr['name'])
    self.assertIsNotNone(email_field.attr['required'])

    name_field = response.pyquery('input#name')
    self.assertLength(1, name_field)
    self.assertEqual('text', name_field.attr['type'])
    self.assertEqual('name', name_field.attr['name'])
    self.assertIsNotNone(name_field.attr['required'])

    password_field = response.pyquery('input#password')
    self.assertLength(1, password_field)
    self.assertEqual('password', password_field.attr['type'])
    self.assertEqual('password', password_field.attr['name'])
    self.assertIsNotNone(password_field.attr['required'])

    pin_field = response.pyquery('input#pin')
    self.assertLength(1, pin_field)
    self.assertEqual('password', pin_field.attr['type'])
    self.assertEqual('pin', pin_field.attr['name'])
    self.assertIsNotNone(pin_field.attr['required'])

  def test_post_signup_missing_data(self):
    # Required fields are: name, email, password.
    # If any of these are missing, an error should happen:

    # This isn't the entire powerset. The entire set is ignored (since that
    # would be valid).
    powerset = chain.from_iterable(combinations(self.SIGNUP_DATA.keys(), size)
                                   for size in range(len(self.SIGNUP_DATA)))
    for field_list in powerset:
      data = dict((k, self.SIGNUP_DATA[k]) for k in field_list)
      response = self.app.post(self.uri_for('signup'), data)
      self.assertOk(response)
      self.assertTemplateUsed('signup.haml')

      for field_name in self.SIGNUP_DATA:
        field = response.pyquery('input#%s' % field_name)
        self.assertLength(1, field)

        if field_name in data:
          # We provided this field so it should be fine.
          self.assertEqual('', field.attr['data-error'],
                           field_name + ' should not have errors.')
        else:
          # This field was missing, so we should have an error.
          self.assertNotEqual('', field.attr['data-error'],
                              field_name + ' should have an error.')

  @unittest2.skip('Skipping until beta test is over.')
  def test_signup_page_flow(self):
    # Check that things are empty.
    self.assertLength(0, Profile.all())

    # Sign up with the form.
    response = self.app.post(self.uri_for('signup'), self.SIGNUP_DATA)
    self.assertRedirects(response, self.uri_for('home'))

    # Check that we are actually logged in.
    response = self.app.get(response.location)
    self.assertLoggedIn()

    # Check that one of everything was created.
    self.assertLength(1, Profile.all())

    profile = Profile.all().get()

    # Check the basic data.
    self.assertEqual(self.SIGNUP_DATA['email'], profile.email)
    self.assertEqual(self.SIGNUP_DATA['name'], profile.name)
    self.assertTrue(profile.check_pin(self.SIGNUP_DATA['pin']))
    self.assertNotEqual(self.UPDATE_DATA['pin'], profile.pin)

    # Logout and log back in to test that the password works.
    self.logout()
    response = self.login(self.SIGNUP_DATA['email'],
                          self.SIGNUP_DATA['password'])
    self.assertRedirects(response, self.uri_for('home'))

  def test_signup_sends_welcome_email(self):
    # Sign up successfully.
    response = self.app.post(self.uri_for('signup'), self.SIGNUP_DATA)
    self.assertRedirects(response, self.uri_for('login'))

    # Check that a profile was created.
    profile = Profile.get_by_email(self.SIGNUP_DATA['email'])
    self.assertIsNotNone(profile)

    # Check that a mail-sending task is in the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(1, tasks)

    # Run the task (it should be a deferred call) and check that an e-mail
    # is sent.
    task, = tasks
    deferred.run(task.payload)
    messages = self.mail_stub.get_sent_messages()
    self.assertLength(1, messages)

    message, = messages
    self.assertEqual('"%s" <%s>' % (profile.name, profile.email), message.to)
    self.assertEqual('Welcome to Blaze!', message.subject)
    self.assertEqual('%s' % (constants.FULL_NO_REPLY_EMAIL), message.sender)
    self.assertEqual('%s' % (constants.FULL_SUPPORT_EMAIL), message.reply_to)

  def test_signup_welcome_email_has_proper_public_host(self):
    response = self.app.post(self.uri_for('signup'), self.SIGNUP_DATA)
    self.assertRedirects(response, self.uri_for('login'))

    # Check that a mail-sending task is in the queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names='mail')
    self.assertLength(1, tasks)
    task, = tasks
    deferred.run(task.payload)
    messages = self.mail_stub.get_sent_messages()
    self.assertLength(1, messages)
    message, = messages
    self.assertNotIn('http://localhost', message.body.decode())
    self.assertNotIn('http://localhost', message.html.decode())
    self.assertIn(constants.PUBLIC_DOMAIN, message.body.decode())
    self.assertIn(constants.PUBLIC_DOMAIN, message.html.decode())

  def test_signup_with_existing_email(self):
    profile = self.create_profile()
    SIGNUP_DATA = self.SIGNUP_DATA.copy()
    SIGNUP_DATA['email'] = profile.email

    response = self.app.post(self.uri_for('signup'), SIGNUP_DATA)
    self.assertFlashMessage(message=error_messages.EMAIL_INVALID_OR_USED,
                            level='error', response=response)
    self.assertLength(1, Profile.all())

    email_field = response.pyquery('input#email')
    self.assertLength(1, email_field)
    self.assertNotEqual('', email_field.attr['data-error'])

  def test_signup_schedules_emails(self):
    # Sign up successfully.
    response = self.app.post(self.uri_for('signup'), self.SIGNUP_DATA)
    self.assertRedirects(response, self.uri_for('login'))

    # Check that a profile was created.
    profile = Profile.get_by_email(self.SIGNUP_DATA['email'])
    self.assertIsNotNone(profile)

    # There should be one task in the scheduler queue.
    tasks = self.taskqueue_stub.get_filtered_tasks(queue_names=['mail'])
    self.assertLength(1, tasks)

  def test_signup_page_has_link_to_terms(self):
    response = self.app.get(self.uri_for('signup'))
    self.assertLength(1, response.pyquery('#signup a[href="%s"]' % (
                                          self.uri_for('terms'))))

  def test_signup_page_has_link_to_privacy_policy(self):
    response = self.app.get(self.uri_for('signup'))
    self.assertLength(1, response.pyquery('#signup a[href="%s"]' % (
                                          self.uri_for('privacy'))))

  def test_account_activation_with_valid_key(self):
    # Set up a profile, and set profile.activated to False.
    profile = self.create_profile(activated=False)
    profile.put()

    # Try to activate the account with a valid key.
    response = self.app.get(self.uri_for('profile.activate',
                                         k=profile.activation_key))
    profile = Profile.get(profile.key())
    # Check that the profile is activated.
    self.assertEqual(True, profile.activated)
    self.assertRedirects(response, self.uri_for('home'))

  def test_account_activation_with_missing_key(self):
    # Set up a profile, and set profile.activated to False.
    profile = self.create_profile(activated=False)
    profile.put()

    # Try to activate the account with a missing key.
    response = self.app.get(self.uri_for('profile.activate'))
    profile = Profile.get(profile.key())
    # Check that the profile is not activated.
    self.assertEqual(False, profile.activated)
    self.assertRedirects(response, self.uri_for('home'))

  def test_account_activation_with_empty_key(self):
    # Set up a profile, and set profile.activated to False.
    profile = self.create_profile(activated=False)
    profile.put()

    # Try to activate the account with a empty key.
    response = self.app.get(self.uri_for('profile.activate', k=''))
    profile = Profile.get(profile.key())
    # Check that the profile is not activated.
    self.assertEqual(False, profile.activated)
    self.assertRedirects(response, self.uri_for('home'))

  def test_account_activation_with_invalid_key(self):
    # Set up a profile, and set profile.activated to False.
    profile = self.create_profile(activated=False)
    profile.put()

    # Try to activate the account with a invalid key.
    # Keys are stored as strings, so any mismatch key will,
    # be a suitable invalid key.
    response = self.app.get(self.uri_for('profile.activate',
                                         k='Invalid Key'))
    profile = Profile.get(profile.key())
    # Check that the profile is not activated.
    self.assertEqual(False, profile.activated)
    self.assertRedirects(response, self.uri_for('home'))

  def test_signup_case_insensitive_field(self):
    # Attempt to submit a signup with an uppercase email.
    SIGNUP_DATA = self.SIGNUP_DATA.copy()
    SIGNUP_DATA['email'] = SIGNUP_DATA['email'].upper()
    response = self.app.post(self.uri_for('signup'), self.SIGNUP_DATA)
    self.assertRedirects(response, self.uri_for('login'))

    # Ensure a Profile has been created, and the email address is in lowercase.
    self.assertLength(1, Profile.all())
    profile = Profile.all().get()
    self.assertEqual(SIGNUP_DATA['email'].lower(), profile.email)

  def test_signup_with_different_case_doesnt_create_duplicate_profile(self):
    # Add a user.
    self.create_profile(self.SIGNUP_DATA['email'])
    self.assertLength(1, Profile.all())

    # Attempt to create a duplicate user.
    DUPLICATE_DATA = self.SIGNUP_DATA.copy()
    response = self.app.post(self.uri_for('signup'), DUPLICATE_DATA)
    self.assertFlashMessage(message=error_messages.EMAIL_INVALID_OR_USED,
                            level='error', response=response)

    # Ensure no new profiles have been created.
    self.assertLength(1, Profile.all())

  def test_signup_flashes_success_message(self):
    # Add a user.
    response = self.app.post(self.uri_for('signup'), self.SIGNUP_DATA)
    self.assertRedirects(response, self.uri_for('login'))
    self.assertFlashMessage(level='success')

    # Ensure a Profile has been created, and the email address is in lowercase.
    self.assertLength(1, Profile.all())

  def test_signup_profile_has_no_money(self):
    # Add a user.
    response = self.app.post(self.uri_for('signup'), self.SIGNUP_DATA)
    self.assertRedirects(response, self.uri_for('login'))

    # Ensure a profile has been created.
    self.assertLength(1, Profile.all())
    profile = Profile.all().get()
    self.assertEqual(0, profile.jmd_balance)
    self.assertEqual(0, profile.usd_balance)
    self.assertTrue(profile.beta_tester)
