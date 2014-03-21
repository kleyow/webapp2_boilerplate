import unittest2

from library import constants
from library import testing


class TestLibraryConstants(testing.TestCase, unittest2.TestCase):

  def test_public_domain(self):
    self.assertEqual('', constants.PUBLIC_DOMAIN)
