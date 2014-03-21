import wtforms
from wtforms import validators, ValidationError

from forms import error_messages
from models.transaction import Transaction


class RefundForm(wtforms.Form):

  transaction = wtforms.TextField(validators=[validators.Required(
      message=error_messages.TRANSACTION_REQUIRED)])

  def validate_transaction(self, field):
    transaction = Transaction.get_by_uuid(field.data)

    if not transaction:
      raise ValidationError(error_messages.TRANSACTION_NOT_FOUND)

    if transaction.transaction_type != Transaction.Type.Purchase:
      raise ValidationError(error_messages.REFUND_PURCHASE_ONLY)

    if transaction.status != Transaction.Status.Completed:
      raise ValidationError(error_messages.REFUND_COMPLETED_ONLY)

    field.data = transaction
