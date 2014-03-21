import wtforms
from wtforms import validators, ValidationError

from forms import custom_validators, error_messages
from library import constants
from models.profile import Profile


class TransferForm(wtforms.Form):

  amount = wtforms.DecimalField(
      validators=[
          validators.Required(error_messages.AMOUNT_REQUIRED),
          validators.NumberRange(
              message=error_messages.POSITIVE_AMOUNT_REQUIRED, min=0),
          custom_validators.DecimalPlaces(
              message=error_messages.DECIMAL_PLACES,
              max=2)])

  recipient = wtforms.TextField(
      validators=[
          validators.Required(error_messages.RECIPIENT_REQUIRED),
          validators.Email(error_messages.INVALID_EMAIL)])

  currency = wtforms.TextField(
      validators=[
          validators.Required(error_messages.CURRENCY_REQUIRED),
          validators.AnyOf(constants.CURRENCIES,
                           message=error_messages.INVALID_CURRENCY)])

  pin = wtforms.TextField(
      validators=[validators.Required(error_messages.PIN_REQUIRED),
                  validators.Regexp('\d{4}',
                                    message=error_messages.PIN_INVALID)])

  def validate_recipient(self, field):
    recipient = Profile.get_by_email(field.data.lower())

    if not recipient:
      raise ValidationError(error_messages.RECIPIENT_NOT_FOUND)
    elif not recipient.activated:
      raise ValidationError(error_messages.RECIPIENT_NOT_ACTIVATED)
    elif not recipient.beta_tester:
      raise ValidationError(error_messages.RECIPIENT_NOT_BETA_TESTER)

    field.data = recipient

  def validate_amount(self, field):
    field.data = int(field.data * 100)
