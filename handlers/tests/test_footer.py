import unittest2

from library import constants
from library import testing


class TestFooter(testing.TestCase, unittest2.TestCase):

  @testing.logged_in
  def test_footer_rendered_on_dashboard(self):
    response = self.app.get(self.uri_for('home'))
    self.assertTemplateUsed('components/footer.haml')
    self.assertLength(1, response.pyquery('footer'))

  @testing.logged_in
  def test_footer_always_rendered_when_logged_in(self):
    response = self.app.get(self.uri_for('contact'))
    self.assertTemplateUsed('components/footer.haml')
    self.assertLength(1, response.pyquery('footer'))

  def test_footer_rendered_when_not_logged_in(self):
    response = self.app.get(self.uri_for('home'))
    self.assertTemplateUsed('components/footer.haml')
    self.assertLength(1, response.pyquery('footer'))

  def test_footer_has_proper_contact_email(self):
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    footer = response.pyquery('footer')
    self.assertLength(1, footer)
    self.assertLength(1, footer.find('.contact'))
    self.assertEqual('mailto:' + constants.CONTACT_EMAIL,
                     footer.find('.contact .email a').attr('href'))

  def test_footer_has_partner_link(self):
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertLength(1, response.pyquery('footer a[href="%s"]' %
                                          (self.uri_for('partner'))))

  def test_footer_has_about_us_section(self):
    response = self.app.get(self.uri_for('home'))
    self.assertOk(response)
    self.assertLength(1, response.pyquery('.about-us'))
