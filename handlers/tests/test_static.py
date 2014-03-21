from google.appengine.api import memcache

import unittest2

from library import testing


class TestStaticHandlers(testing.TestCase, unittest2.TestCase):

  @unittest2.skip('Skipping until we define a FAQ page.')
  def test_faq_page(self):
    response = self.app.get(self.uri_for('faq'))
    self.assertOk(response)
    self.assertTrue(response.body)
    self.assertIn('Questions', response.body)
    self.assertTemplateUsed('faq.html')

  def test_faq_page_caches_response(self):
    self.assertEqual(0, memcache.get_stats()['items'])

    response = self.app.get(self.uri_for('faq'))
    self.assertEqual(1, memcache.get_stats()['items'])
    self.assertEqual(0, memcache.get_stats()['hits'])
    self.assertEqual(1, memcache.get_stats()['misses'])

    response = self.app.get(self.uri_for('faq'))
    self.assertOk(response)
    self.assertEqual(1, memcache.get_stats()['hits'])

  @unittest2.skip('Skipping until we define a features page.')
  def test_features_page(self):
    response = self.app.get(self.uri_for('features'))
    self.assertOk(response)
    self.assertTrue(response.body)
    self.assertTemplateUsed('features.html')

  def test_features_page_caches_response(self):
    self.assertEqual(0, memcache.get_stats()['items'])

    response = self.app.get(self.uri_for('features'))
    self.assertEqual(1, memcache.get_stats()['items'])
    self.assertEqual(0, memcache.get_stats()['hits'])
    self.assertEqual(1, memcache.get_stats()['misses'])

    response = self.app.get(self.uri_for('features'))
    self.assertOk(response)
    self.assertEqual(1, memcache.get_stats()['hits'])

  def test_about_page(self):
    response = self.app.get(self.uri_for('about'))
    self.assertOk(response)
    self.assertTemplateUsed('about.haml')
    self.assertLength(3, response.pyquery('h1'))
    self.assertLength(1, response.pyquery('.get-started'))

  def test_about_page_caches_response(self):
    self.assertEqual(0, memcache.get_stats()['items'])

    response = self.app.get(self.uri_for('about'))
    self.assertEqual(1, memcache.get_stats()['items'])
    self.assertEqual(0, memcache.get_stats()['hits'])
    self.assertEqual(1, memcache.get_stats()['misses'])

    response = self.app.get(self.uri_for('about'))
    self.assertOk(response)
    self.assertEqual(1, memcache.get_stats()['hits'])
