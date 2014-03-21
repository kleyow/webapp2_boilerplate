import decimal

import mock
import unittest2
from wtforms.validators import ValidationError

from forms.custom_validators import DecimalPlaces
from library import testing


class TestDecimalPlaces(testing.TestCase, unittest2.TestCase):

  def test_decimal_places(self):
    # Mock a form and a field.
    form = mock.Mock()
    field = mock.Mock(data=decimal.Decimal('3.14'), raw_data=['3.14'])
    # Ensure that the validation was successful.
    self.assertIsNone((DecimalPlaces()(form, field)))

  def test_decimal_places_whole_number(self):
    form = mock.Mock()
    field = mock.Mock(data=decimal.Decimal('3'), raw_data=['3'])
    self.assertIsNone(DecimalPlaces()(form, field))

  def test_decimal_places_min_max(self):
    form = mock.Mock()
    field = mock.Mock(data=decimal.Decimal('3.142'), raw_data=['3.142'])
    self.assertIsNone(DecimalPlaces(min=0, max=3)(form, field))

  def test_decimal_places_raises_error_with_float_input(self):
    # Ensure that a ValidationError is raised if a float is passed to
    # it.
    form = mock.Mock()
    field = mock.Mock(data=3.14, raw_data=['3.14'])
    self.assertRaises(ValidationError, DecimalPlaces(), form, field)

  def test_decimal_places_raises_error_with_incorrect_decimal_places(self):
    # Ensure that a ValidationError is raised if it recieves a number
    # with too many decimal places.
    form = mock.Mock()
    field = mock.Mock(data=decimal.Decimal('3.1428'), raw_data=['3.1428'])
    self.assertRaises(ValidationError, DecimalPlaces(), form, field)

  def test_decimal_places_raises_error_with_one_decimal_place(self):
    form = mock.Mock()
    field = mock.Mock(data=decimal.Decimal('3.1'), raw_data=['3.1'])
    self.assertRaises(ValidationError, DecimalPlaces(), form, field)
