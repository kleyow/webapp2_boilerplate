import wtforms
from wtforms import validators

from forms import custom_validators, error_messages
from library import constants


class PurchaseForm(wtforms.Form):

  amount = wtforms.DecimalField(
      validators=[
          validators.Required(error_messages.AMOUNT_REQUIRED),
          validators.NumberRange(
              message=error_messages.POSITIVE_AMOUNT_REQUIRED, min=0),
          custom_validators.DecimalPlaces(
              message=error_messages.DECIMAL_PLACES, max=2)])

  tip_amount = wtforms.DecimalField(
      validators=[
          validators.Optional(),
          validators.NumberRange(
              message=error_messages.POSITIVE_AMOUNT_REQUIRED, min=0),
          custom_validators.DecimalPlaces(
              message=error_messages.DECIMAL_PLACES, max=2)])

  currency = wtforms.TextField(
      validators=[
          validators.Required(error_messages.CURRENCY_REQUIRED),
          validators.AnyOf(constants.CURRENCIES,
                           message=error_messages.INVALID_CURRENCY)])

  pin = wtforms.TextField(
      validators=[validators.Required(error_messages.PIN_REQUIRED),
                  validators.Regexp('\d{4}',
                                    message=error_messages.PIN_INVALID)])

  def validate_amount(self, field):
    field.data = int(field.data * 100)

  def validate_tip_amount(self, field):
    field.data = int(field.data * 100)
