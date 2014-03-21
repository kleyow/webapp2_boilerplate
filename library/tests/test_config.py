import mock
import unittest2

import config
from library import testing


class TestConfig(testing.TestCase, unittest2.TestCase):

  @mock.patch('library.template_filters')
  def test_config_has_proper_template_filters(self, template_filters):
    template_filters.__all__ = ['foo']
    template_filters.foo = lambda x: None
    reload(config)
    self.assertEqual(
        {'foo': template_filters.foo},
        config.webapp2_config['webapp2_extras.jinja2']['filters'])
