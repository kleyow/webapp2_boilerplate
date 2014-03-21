import decimal
import re

from wtforms import ValidationError


class DecimalPlaces(object):
  """Validates the number of decimal places entered in a field."""

  def __init__(self, min=2, max=2, message=None):
    self.min = min
    self.max = max
    self.message = message

  def __call__(self, form, field):
    if not isinstance(field.data, decimal.Decimal):
      raise ValidationError('Expected decimal.Decimal, got %s.'
                            % type(field.data))

    regex = r'^\d+(\.\d{%d,%d})?$' % (self.min, self.max)

    if not re.match(regex, field.raw_data[0]):
      message = self.message or ('Field must have at between %d and %d '
                                 'decimal places.' % (self.min, self.max))
      raise ValidationError(message)
