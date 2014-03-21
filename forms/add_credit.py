from google.appengine.ext import db
import wtforms
from wtforms import validators

from forms import custom_validators, error_messages
from models.funding_source import FundingSource


class AddCreditForm(wtforms.Form):

  funding_source = wtforms.TextField(
      validators=[
          validators.Required(error_messages.FUNDING_SOURCE_REQUIRED)])

  amount = wtforms.DecimalField(
      validators=[
          validators.Required(error_messages.AMOUNT_REQUIRED),
          validators.NumberRange(
              message=error_messages.POSITIVE_AMOUNT_REQUIRED, min=0),
          custom_validators.DecimalPlaces(
              message=error_messages.DECIMAL_PLACES, max=2)])

  def validate_funding_source(self, field):
    # Check that the funding source exists.
    # NOTE: We check that the current user is able to access it in
    # the handler.
    try:
      funding_source = FundingSource.get(field.data)

    except db.BadKeyError:
      funding_source = None

    if not funding_source:
      # Clear all prior error messages and stop the validation chain so
      # error_messages.FUNDING_SOURCE_NOT_FOUND is returned.
      field.errors[:] = []
      raise validators.StopValidation(error_messages.FUNDING_SOURCE_NOT_FOUND)

    field.data = funding_source
