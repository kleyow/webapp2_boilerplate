import unittest2

from forms import error_messages
from library import testing


class TestLoginHandler(testing.TestCase, unittest2.TestCase):
  def test_get_login_page(self):
    response = self.app.get(self.uri_for('login'))
    self.assertEqual(200, response.status_int)
    self.assertIn('Login', response.body)

  def test_get_login_page_with_redirect(self):
    email, password = 'test@example.org', 'mypass'
    self.create_profile(email, password)

    original_page = self.uri_for('profile.view')
    login_redirect = self.uri_for('login', redirect=original_page)

    # Try to go to a protected page
    response = self.app.get(original_page)
    self.assertRedirects(response, login_redirect)

    # Load up the page that it redirected us to
    response = self.app.post(response.location, {'email': email,
                                                 'password': password})
    self.assertRedirects(response, original_page)

  def test_login(self):
    email, password = 'test@example.org', 'pass'
    self.create_profile(email, password)

    # First test that we're not logged in:
    response = self.app.get(self.uri_for('profile.view'))
    self.assertRedirects(response)

    # Log us in.
    response = self.app.post(self.uri_for('login'), {'email': email,
                                                     'password': password})
    self.assertRedirects(response, self.uri_for('home'))

    # Test that we can now view that page.
    response = self.app.get(self.uri_for('profile.view'))
    self.assertOk(response)

  @testing.logged_in
  def test_login_already_logged_in(self):
    response = self.app.get(self.uri_for('login'))
    self.assertRedirects(response, self.uri_for('home'))

  def test_not_beta_tester(self):
    email, password = 'test@example.org', 'pass',
    self.create_profile(email, password, beta_tester=False)

    # First test that we're not logged in:
    self.assertNotLoggedIn()

    # Log us in, and fail.
    login_data = {'email': email, 'password': password}
    response = self.app.post(self.uri_for('login'), login_data)

    # Redirects to logout and logs us out.
    self.assertRedirects(response, self.uri_for('home'))
    self.assertFlashMessage(message=error_messages.NOT_BETA_TESTER,
                            level='error')

  def test_login_case_insensitive_field(self):
    email, password = 'test@example.org', 'pass'
    self.create_profile(email, password)

    # Ensure we're not logged in.
    self.assertNotLoggedIn()

    # Attempt to log in with uppercase email address.
    params = {'email': email.upper(), 'password': password}
    response = self.app.post(self.uri_for('login'), params)
    self.assertRedirects(response, self.uri_for('home'))

    # Ensure we're logged in.
    self.assertLoggedIn()

  def test_login_nonexisting_account(self):
    email, password = 'not@correct.com', 'pass'

    # Attempt to log in with invalid credentials.
    params = {'email': email, 'password': password}
    response = self.app.post(self.uri_for('login'), params)
    self.assertOk(response)
    self.assertLength(1, response.pyquery('.login-error'))
    self.assertNotLoggedIn()

  def test_login_incorrect_password(self):
    profile = self.create_profile()
    params = {'email': profile.email, 'password': 'WRONG'}
    response = self.app.post(self.uri_for('login'), params)
    self.assertOk(response)
    self.assertLength(1, response.pyquery('.login-error'))
    self.assertNotLoggedIn()

  def test_login_external_url_in_redirect(self):
    profile = self.create_profile(password='test')
    response = self.app.get(
        self.uri_for('login', redirect='http://google.com'))
    self.assertOk(response)

    form = response.forms[0]
    form['email'] = profile.email
    form['password'] = 'test'
    response = form.submit()
    self.assertRedirects(response, self.uri_for('home'))

  def test_staff_login_link_on_form(self):
    response = self.app.get(self.uri_for('login'))
    self.assertOk(response)
    self.assertTemplateUsed('login.haml')
    self.assertLength(
        1, response.pyquery('a[href="%s"]' % self.uri_for('staff.login')))
