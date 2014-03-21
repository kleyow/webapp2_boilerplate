import datetime
import uuid

import pytz
import unittest2

from library import constants, testing
from models.organization import Organization
from models.profile import Profile
from models.staff import Staff
from models.transaction import Transaction
from models.transaction_receipt import TransactionReceipt


class TestTransaction(testing.TestCase, unittest2.TestCase):

  AMOUNT = 2000

  def test_default_values(self):
    transaction = Transaction()
    self.assertAlmostEqual(datetime.datetime.now(), transaction.created,
                           delta=datetime.timedelta(seconds=5))
    self.assertIsNone(transaction.verified_time)
    self.assertAlmostEqual(datetime.datetime.now(), transaction.modified,
                           delta=datetime.timedelta(seconds=5))
    self.assertIsNone(transaction.stripe_charge_id)
    self.assertIsNone(transaction.amount)
    self.assertEqual(transaction.Status.Pending, transaction.status)
    self.assertIsNone(transaction.transaction_type)
    self.assertIsNone(transaction.sender)
    self.assertIsNone(transaction.recipient)
    self.assertIsNone(transaction.verifier)
    self.assertIsNone(transaction.seller)
    self.assertIsNone(transaction.uuid)
    self.assertEqual(0, transaction.fees)
    self.assertEqual(0, transaction.total_amount)
    self.assertEqual(0, transaction.tip_amount)

  def test_is_viewable_by_organization(self):
    owner_profile = self.create_profile()
    sender_profile = self.create_profile()
    unauthorized_profile = self.create_profile()
    organization = self.create_organization(owner=owner_profile)
    transaction = self.create_transaction(
        recipient=organization,
        sender=sender_profile,
        transaction_type=Transaction.Type.Purchase)

    self.assertTrue(transaction.is_viewable_by(owner_profile))
    self.assertTrue(transaction.is_viewable_by(sender_profile))
    self.assertFalse(transaction.is_viewable_by(unauthorized_profile))

  def test_is_viewable_by_profile(self):
    sender_profile = self.create_profile()
    recipient_profile = self.create_profile()
    unauthorized_profile = self.create_profile()
    transaction = self.create_transaction(
        recipient=recipient_profile,
        sender=sender_profile,
        transaction_type=Transaction.Type.Transfer)

    self.assertTrue(transaction.is_viewable_by(sender_profile))
    self.assertTrue(transaction.is_viewable_by(recipient_profile))
    self.assertFalse(transaction.is_viewable_by(unauthorized_profile))

  def test_is_viewable_by_staff(self):
    sender_profile = self.create_profile()
    recipient_organization = self.create_organization()
    staff = self.create_staff(organization=recipient_organization)
    unauthorized_staff = self.create_staff(username='test@example')
    transaction = self.create_transaction(
        recipient=recipient_organization,
        sender=sender_profile,
        transaction_type=Transaction.Type.Purchase)
    self.assertTrue(transaction.is_viewable_by(sender_profile))
    self.assertTrue(transaction.is_viewable_by(staff))
    self.assertFalse(transaction.is_viewable_by(unauthorized_staff))

  def test_is_viewable_by_other(self):
    recipient = self.create_profile()
    unauthorized_object = self.create_funding_source()
    transaction = self.create_transaction(
        recipient=recipient,
        sender=self.create_profile(),
        transaction_type=Transaction.Type.Transfer)

    self.assertFalse(transaction.is_viewable_by(unauthorized_object))

  def test_cancel_pending_transfer(self):
    """Ensure that cancelling a pending transfer changes the status."""
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Transfer)
    self.assertEqual(Transaction.Status.Pending, transaction.status)
    transaction.cancel()
    self.assertEqual(Transaction.Status.Cancelled, transaction.status)

    # Ensure that receipts are created for sender and recipient.
    self.assertLength(2, TransactionReceipt.all())
    sender_receipt, recipient_receipt = TransactionReceipt.all()
    self.assertEqual(transaction.sender.key(),
                     sender_receipt.get_owner().key())
    self.assertEqual(transaction.recipient.key(),
                     recipient_receipt.get_owner().key())

  def test_cancel_processing_transfer(self):
    """Ensure that cancelling a processing transfer changes the status."""
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Transfer,
        status=Transaction.Status.Processing)
    self.assertEqual(Transaction.Status.Processing, transaction.status)
    transaction.cancel()
    self.assertEqual(Transaction.Status.Cancelled, transaction.status)

    # Ensure that receipts are created for sender and recipient.
    self.assertLength(2, TransactionReceipt.all())
    sender_receipt, recipient_receipt = TransactionReceipt.all()
    self.assertEqual(transaction.sender.key(),
                     sender_receipt.get_owner().key())
    self.assertEqual(transaction.recipient.key(),
                     recipient_receipt.get_owner().key())

  def test_cancel_pending_purchase(self):
    """Ensure that cancelling a pending purchase changes the status."""
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        recipient=self.create_organization())
    self.assertEqual(Transaction.Status.Pending, transaction.status)
    transaction.cancel()
    self.assertEqual(Transaction.Status.Cancelled, transaction.status)

    # Ensure that receipts are created for sender and recipient.
    self.assertLength(2, TransactionReceipt.all())
    recipient_receipt, sender_receipt = TransactionReceipt.all()
    self.assertEqual(transaction.sender.key(),
                     sender_receipt.get_owner().key())
    self.assertEqual(transaction.recipient.key(),
                     recipient_receipt.get_owner().key())

  def test_cancel_processing_purchase(self):
    """Ensure that cancelling a processing purchase changes the status."""
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Processing,
        recipient=self.create_organization())
    self.assertEqual(Transaction.Status.Processing, transaction.status)
    transaction.cancel()
    self.assertEqual(Transaction.Status.Cancelled, transaction.status)

    # Ensure that receipts are created for sender and recipient.
    self.assertLength(2, TransactionReceipt.all())
    recipient_receipt, sender_receipt = TransactionReceipt.all()
    self.assertEqual(transaction.sender.key(),
                     sender_receipt.get_owner().key())
    self.assertEqual(transaction.recipient.key(),
                     recipient_receipt.get_owner().key())

  def test_cancel_processing_deposit(self):
    """Ensure that cancelling a processing deposit changes the status."""
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Deposit,
        status=Transaction.Status.Processing)
    self.assertEqual(Transaction.Status.Processing, transaction.status)
    transaction.cancel()
    self.assertEqual(Transaction.Status.Cancelled, transaction.status)

    # Ensure that a receipt is created for recipient.
    self.assertLength(1, TransactionReceipt.all())
    recipient_receipt = TransactionReceipt.all().get()
    self.assertEqual(transaction.recipient.key(),
                     recipient_receipt.get_owner().key())

  def test_cancel_pending_deposit(self):
    """Ensure that cancelling a pending deposit changes the status."""
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Deposit,
        status=Transaction.Status.Pending)
    transaction.put()
    self.assertEqual(Transaction.Status.Pending, transaction.status)
    transaction.cancel()
    self.assertEqual(Transaction.Status.Cancelled, transaction.status)

    # Ensure that a receipt is created for recipient.
    self.assertLength(1, TransactionReceipt.all())
    recipient_receipt = TransactionReceipt.all().get()
    self.assertEqual(transaction.recipient.key(),
                     recipient_receipt.get_owner().key())

  def test_cancel_completed_transaction(self):
    transaction = Transaction(
        transaction_type=Transaction.Type.Transfer,
        status=Transaction.Status.Completed)
    transaction.put()
    self.assertRaises(RuntimeError, transaction.cancel)

    # Ensure no receipts are created.
    self.assertLength(0, TransactionReceipt.all())

  def test_cancel_cancelled_transaction(self):
    transaction = Transaction(
        transaction_type=Transaction.Type.Transfer,
        status=Transaction.Status.Cancelled)
    transaction.put()
    self.assertRaises(RuntimeError, transaction.cancel)

    # Ensure no receipts are created.
    self.assertLength(0, TransactionReceipt.all())

  def test_cancel_processing_refund(self):
    """Ensure that cancelling a processing refund changes the status."""
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        recipient=self.create_organization(), is_cash_deposit=True,
        status=Transaction.Status.Refunding)
    self.assertEqual(Transaction.Status.Refunding, transaction.status)
    transaction.cancel()
    self.assertEqual(Transaction.Status.Cancelled, transaction.status)

    # Ensure that receipts are created for sender and recipient.
    self.assertLength(2, TransactionReceipt.all())
    recipient_receipt, sender_receipt = TransactionReceipt.all()
    self.assertEqual(transaction.sender.key(),
                     sender_receipt.get_owner().key())
    self.assertEqual(transaction.recipient.key(),
                     recipient_receipt.get_owner().key())

  def test_cancel_processing_cash_deposit(self):
    """Ensure that cancelling a processing refund changes the status."""
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Deposit,
        recipient=self.create_profile(), is_cash_deposit=True,
        status=Transaction.Status.Processing)
    self.assertEqual(Transaction.Status.Processing, transaction.status)
    transaction.cancel()
    self.assertEqual(Transaction.Status.Cancelled, transaction.status)

    # Ensure that receipts are created for sender and recipient.
    self.assertLength(2, TransactionReceipt.all())
    recipient_receipt, sender_receipt = TransactionReceipt.all()
    self.assertEqual(transaction.sender.key(),
                     sender_receipt.get_owner().key())
    self.assertEqual(transaction.recipient.key(),
                     recipient_receipt.get_owner().key())

  def test_cancel_pending_cash_deposit(self):
    """Ensure that cancelling a pending cash deposit changes the status."""
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Deposit, is_cash_deposit=True)
    self.assertEqual(Transaction.Status.Pending, transaction.status)
    transaction.cancel()
    self.assertEqual(Transaction.Status.Cancelled, transaction.status)

    # Ensure that receipts are created for sender and recipient.
    self.assertLength(2, TransactionReceipt.all())
    recipient_receipt, sender_receipt = TransactionReceipt.all()
    self.assertEqual(transaction.sender.key(),
                     sender_receipt.get_owner().key())
    self.assertEqual(transaction.recipient.key(),
                     recipient_receipt.get_owner().key())

  def test_cancel_refunding_cash_deposit(self):
    """Ensure that cancelling a refunding cash deposit changes the status."""
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Deposit,
        status=Transaction.Status.Refunding, is_cash_deposit=True)
    self.assertEqual(Transaction.Status.Refunding, transaction.status)
    transaction.cancel()
    self.assertEqual(Transaction.Status.Cancelled, transaction.status)

    # Ensure that receipts are created for sender and recipient.
    self.assertLength(2, TransactionReceipt.all())
    recipient_receipt, sender_receipt = TransactionReceipt.all()
    self.assertEqual(transaction.sender.key(),
                     sender_receipt.get_owner().key())
    self.assertEqual(transaction.recipient.key(),
                     recipient_receipt.get_owner().key())

  def test_cancel_non_admin_cash_deposit(self):
    """Ensure that cancelling a processing cash deposit changes the status.

    This test ensures that we can cancel any invalid cash deposits
    (from a non-admin)."""
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Deposit,
        sender=self.create_profile(),
        recipient=self.create_profile(), is_cash_deposit=True,
        status=Transaction.Status.Processing)
    self.assertEqual(Transaction.Status.Processing, transaction.status)
    transaction.cancel()
    self.assertEqual(Transaction.Status.Cancelled, transaction.status)

    # Ensure that receipts are created for sender and recipient.
    self.assertLength(2, TransactionReceipt.all())
    sender_receipt, recipient_receipt = TransactionReceipt.all()
    self.assertEqual(transaction.sender.key(),
                     sender_receipt.get_owner().key())
    self.assertEqual(transaction.recipient.key(),
                     recipient_receipt.get_owner().key())

  def test_cancel_edge_cases(self):
    """Ensure only pending and processing transactions can be cancelled."""
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Transfer,
        status=Transaction.Status.Completed)
    self.assertRaises(RuntimeError, transaction.cancel)

    transaction = Transaction()
    transaction.status = Transaction.Status.Cancelled
    transaction.put()
    self.assertRaises(RuntimeError, transaction.cancel)

  def test_transfer_funds_usd_transfer(self):
    sender = self.create_profile('sender@example.com', usd_balance=3000)
    recipient = self.create_profile()
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Transfer,
        status=Transaction.Status.Processing,
        currency=constants.USD_CURRENCY,
        sender=sender, amount=self.AMOUNT,
        recipient=recipient)

    transaction.transfer_funds()

    # Reload all involved entities and ensure transaction was successful.
    sender = Profile.get(sender.key())
    recipient = Profile.get(recipient.key())
    transaction = Transaction.get(transaction.key())

    self.assertEqual(1000, sender.usd_balance)
    self.assertEqual(0, sender.jmd_balance)
    self.assertEqual(self.AMOUNT, transaction.recipient.usd_balance)

  def test_transfer_funds_usd_purchase(self):
    sender = self.create_profile('sender@example.com', usd_balance=3000)
    organization = self.create_organization()
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Processing,
        currency=constants.USD_CURRENCY,
        sender=sender, amount=self.AMOUNT,
        recipient=organization)

    transaction.transfer_funds()

    # Reload all involved entiies.
    sender = Profile.get(sender.key())
    organization = Organization.get(organization.key())
    transaction = Transaction.get(transaction.key())

    # Ensure all balances and fees have been updated accordingly.
    self.assertEqual(1000, transaction.sender.usd_balance)
    self.assertEqual(self.AMOUNT, transaction.recipient.usd_balance)
    self.assertEqual(Transaction.Status.Completed, transaction.status)
    fees = int(transaction.recipient.get_fee_percentage() * self.AMOUNT)
    self.assertEqual(fees, transaction.fees)
    self.assertEqual(0, organization.jmd_fees)
    self.assertEqual(transaction.fees, organization.usd_fees)
    self.assertEqual(transaction.amount - fees, transaction.total_amount)

  def test_transfer_funds_jmd_transfer(self):
    sender = self.create_profile('sender@example.com', jmd_balance=3000)
    profile = self.create_profile()
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Transfer,
        status=Transaction.Status.Processing,
        currency=constants.JMD_CURRENCY,
        sender=sender, amount=self.AMOUNT,
        recipient=profile)

    transaction.transfer_funds()

    # Reload all involved entities.
    sender = Profile.get(sender.key())
    profile = Profile.get(profile.key())
    transaction = Transaction.get(transaction.key())

    # Ensure balances have been updated accordingly.
    self.assertEqual(1000, sender.jmd_balance)
    self.assertEqual(0, sender.usd_balance)
    self.assertEqual(self.AMOUNT, transaction.recipient.jmd_balance)

  def test_transfer_funds_jmd_purchase(self):
    sender = self.create_profile('sender@example.com', jmd_balance=3000)
    organization = self.create_organization()
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Processing,
        currency=constants.JMD_CURRENCY,
        sender=sender, amount=self.AMOUNT,
        recipient=organization)

    transaction.transfer_funds()

    # Reload all involved entiies.
    sender = Profile.get(sender.key())
    organization = Organization.get(organization.key())
    transaction = Transaction.get(transaction.key())

    # Ensure all balances and fees have been updated accordingly.
    self.assertEqual(1000, transaction.sender.jmd_balance)
    self.assertEqual(self.AMOUNT, transaction.recipient.jmd_balance)
    self.assertEqual(Transaction.Status.Completed, transaction.status)
    fees = int(transaction.recipient.get_fee_percentage() * self.AMOUNT)
    self.assertEqual(fees, transaction.fees)
    self.assertEqual(transaction.fees, organization.jmd_fees)
    self.assertEqual(0, organization.usd_fees)
    self.assertEqual(transaction.amount - fees, transaction.total_amount)

  def test_transfer_funds_jmd_refund(self):
    sender = self.create_profile()
    recipient = self.create_organization(jmd_balance=5000, jmd_fees=40)
    fees = int(recipient.get_fee_percentage() * self.AMOUNT)
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Refunding,
        currency=constants.JMD_CURRENCY,
        sender=sender, amount=self.AMOUNT,
        recipient=recipient, fees=fees)

    transaction.transfer_funds()

    # Reload all involved entiies.
    sender = Profile.get(sender.key())
    recipient = Organization.get(recipient.key())
    transaction = Transaction.get(transaction.key())

    # Ensure all balances and fees have been updated accordingly.
    self.assertEqual(self.AMOUNT, sender.jmd_balance)
    self.assertEqual(3000, recipient.jmd_balance)
    self.assertEqual(0, recipient.usd_balance)
    self.assertEqual(0, sender.usd_balance)
    self.assertEqual(0, recipient.jmd_fees)
    self.assertEqual(0, recipient.usd_fees)
    self.assertEqual(Transaction.Status.Refunded, transaction.status)

  def test_transfer_funds_usd_refund(self):
    sender = self.create_profile()
    recipient = self.create_organization(usd_balance=5000, usd_fees=40)
    fees = int(recipient.get_fee_percentage() * self.AMOUNT)
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Refunding,
        currency=constants.USD_CURRENCY,
        sender=sender, amount=self.AMOUNT,
        recipient=recipient, fees=fees)

    transaction.transfer_funds()

    # Reload all involved entiies.
    sender = Profile.get(sender.key())
    recipient = Organization.get(recipient.key())
    transaction = Transaction.get(transaction.key())

    # Ensure the fees and balances have been updated accordingly, and the
    # transaction has been marked as completed.
    self.assertEqual(0, recipient.usd_fees)
    self.assertEqual(3000, transaction.recipient.usd_balance)
    self.assertEqual(self.AMOUNT, transaction.sender.usd_balance)
    self.assertEqual(Transaction.Status.Refunded, transaction.status)
    self.assertEqual(0, recipient.jmd_balance)
    self.assertEqual(0, sender.jmd_balance)
    self.assertEqual(0, recipient.jmd_fees)
    self.assertEqual(0, recipient.usd_fees)

  def test_refund_transaction(self):
    profile = self.create_profile(jmd_balance=5000)
    organization = self.create_organization()
    fees = int(organization.get_fee_percentage() * self.AMOUNT)
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase, amount=self.AMOUNT,
        sender=profile, recipient=organization,
        currency=constants.JMD_CURRENCY,
        status=Transaction.Status.Processing)

    # Make the purchase and ensure it was successful.
    transaction.transfer_funds()

    # Reload all involved entities.
    profile = Profile.get(profile.key())
    organization = Organization.get(organization.key())
    transaction = Transaction.get(transaction.key())

    self.assertEqual(self.AMOUNT, organization.jmd_balance)
    self.assertEqual(fees, organization.jmd_fees)
    self.assertEqual(0, organization.usd_fees)
    self.assertEqual(3000, profile.jmd_balance)
    self.assertEqual(0, profile.usd_balance)
    self.assertEqual(Transaction.Status.Completed, transaction.status)

    # Trigger a refund.
    transaction.status = Transaction.Status.Refunding
    transaction.put()
    transaction.transfer_funds()

    # Reload all involved entities.
    profile = Profile.get(profile.key())
    organization = Organization.get(organization.key())
    transaction = Transaction.get(transaction.key())

    # Ensure all fees and balances have been updated.
    self.assertEqual(Transaction.Status.Refunded, transaction.status)
    self.assertEqual(5000, profile.jmd_balance)
    self.assertEqual(0, organization.jmd_balance)
    self.assertEqual(0, organization.jmd_fees)
    self.assertEqual(0, organization.usd_fees)

  def test_transfer_funds_edge_cases(self):
    sender = self.create_profile('sender@example.com', usd_balance=1000)
    organization = self.create_organization()
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        currency=constants.USD_CURRENCY,
        sender=sender, amount=self.AMOUNT,
        recipient=organization)

    # Ensure that an exception is raised when transactions with negative
    # amounts are attempted.
    self.assertRaises(ValueError, transaction.transfer_funds)
    self.assertEqual(1000, transaction.sender.usd_balance)
    self.assertEqual(0, transaction.recipient.usd_balance)

  def test_purchase_with_usd_tip(self):
    tip_amount = int(self.AMOUNT * 0.1)
    sender = self.create_profile('sender@example.com', usd_balance=3000)
    organization = self.create_organization()
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Processing,
        currency=constants.USD_CURRENCY,
        sender=sender, amount=self.AMOUNT,
        tip_amount=tip_amount, recipient=organization)

    transaction.transfer_funds()

    # Reload all involved entiies.
    sender = Profile.get(sender.key())
    organization = Organization.get(organization.key())
    transaction = Transaction.get(transaction.key())

    # Ensure all balances and fees have been updated accordingly.
    total_amount = self.AMOUNT + tip_amount
    fees = int(transaction.recipient.get_fee_percentage() * total_amount)
    self.assertEqual(0, sender.jmd_balance)
    self.assertEqual(800, sender.usd_balance)
    self.assertEqual(total_amount, organization.usd_balance)
    self.assertEqual(0, organization.jmd_balance)
    self.assertEqual(Transaction.Status.Completed, transaction.status)
    self.assertEqual(fees, transaction.fees)
    self.assertEqual(transaction.fees, organization.usd_fees)
    self.assertEqual(0, organization.jmd_fees)
    self.assertEqual(transaction.amount - fees, transaction.total_amount)

  def test_purchase_with_jmd_tip(self):
    tip_amount = int(self.AMOUNT * 0.1)
    sender = self.create_profile('sender@example.com', jmd_balance=3000)
    organization = self.create_organization()
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Processing,
        currency=constants.JMD_CURRENCY,
        sender=sender, amount=self.AMOUNT,
        tip_amount=tip_amount, recipient=organization)

    transaction.transfer_funds()

    # Reload all involved entiies.
    sender = Profile.get(sender.key())
    organization = Organization.get(organization.key())
    transaction = Transaction.get(transaction.key())

    # Ensure all balances and fees have been updated accordingly.
    total_amount = self.AMOUNT + tip_amount
    fees = int(transaction.recipient.get_fee_percentage() * total_amount)
    self.assertEqual(0, sender.usd_balance)
    self.assertEqual(800, sender.jmd_balance)
    self.assertEqual(0, organization.usd_balance)
    self.assertEqual(total_amount, organization.jmd_balance)
    self.assertEqual(Transaction.Status.Completed, transaction.status)
    self.assertEqual(fees, transaction.fees)
    self.assertEqual(transaction.fees, organization.jmd_fees)
    self.assertEqual(0, organization.usd_fees)
    self.assertEqual(transaction.amount - fees, transaction.total_amount)

  def test_jmd_cash_deposit_admin_profile(self):
    sender = self.create_profile(jmd_balance=4000, is_admin=True)
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Deposit, sender=sender,
        status=Transaction.Status.Processing, amount=3000,
        currency=constants.JMD_CURRENCY, is_cash_deposit=True)
    transaction.transfer_funds()

    sender = Profile.get(sender.key())
    recipient = Profile.get(transaction.recipient.key())

    self.assertEqual(4000, sender.jmd_balance)
    self.assertEqual(3000, recipient.jmd_balance)
    self.assertEqual(0, transaction.fees)
    self.assertEqual(transaction.status, Transaction.Status.Completed)

  def test_usd_cash_deposit_admin_profile(self):
    sender = self.create_profile(usd_balance=4000, is_admin=True)
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Deposit, sender=sender,
        status=Transaction.Status.Processing, amount=3000,
        currency=constants.USD_CURRENCY, is_cash_deposit=True)
    transaction.transfer_funds()

    sender = Profile.get(sender.key())
    recipient = Profile.get(transaction.recipient.key())

    self.assertEqual(4000, sender.usd_balance)
    self.assertEqual(3000, recipient.usd_balance)
    self.assertEqual(0, transaction.fees)
    self.assertEqual(transaction.status, Transaction.Status.Completed)

  def test_jmd_cash_deposit_refund_admin_profile(self):
    sender = self.create_profile(jmd_balance=4000, is_admin=True)
    recipient = self.create_profile(jmd_balance=3000)
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Deposit, sender=sender,
        status=Transaction.Status.Refunding, amount=3000,
        recipient=recipient, currency=constants.JMD_CURRENCY,
        is_cash_deposit=True)
    transaction.transfer_funds()

    sender = Profile.get(sender.key())
    recipient = Profile.get(transaction.recipient.key())

    self.assertEqual(4000, sender.jmd_balance)
    self.assertEqual(0, recipient.jmd_balance)
    self.assertEqual(0, transaction.fees)
    self.assertEqual(transaction.status, Transaction.Status.Refunded)

  def test_usd_cash_deposit_refund_admin_profile(self):
    sender = self.create_profile(usd_balance=4000, is_admin=True)
    recipient = self.create_profile(usd_balance=3000)
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Deposit, sender=sender,
        status=Transaction.Status.Refunding, amount=3000,
        currency=constants.USD_CURRENCY, recipient=recipient,
        is_cash_deposit=True)
    transaction.transfer_funds()

    sender = Profile.get(sender.key())
    recipient = Profile.get(transaction.recipient.key())

    self.assertEqual(4000, sender.usd_balance)
    self.assertEqual(0, recipient.usd_balance)
    self.assertEqual(0, transaction.fees)
    self.assertEqual(transaction.status, Transaction.Status.Refunded)

  def test_jmd_refund_verifier_removes_staff_tip(self):
    organization = self.create_organization()
    staff = self.create_staff(
        organization=organization, jmd_tip_balance=300)
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase, verifier=staff,
        recipient=organization, tip_amount=300,
        currency=constants.JMD_CURRENCY, status=Transaction.Status.Refunding)
    transaction.transfer_funds()

    # Reload staff and ensure their tip_balance was decremented.
    staff = Staff.get(staff.key())
    self.assertEqual(0, staff.jmd_tip_balance)
    self.assertEqual(0, staff.usd_tip_balance)

  def test_usd_refund_verifier_removes_staff_tip(self):
    organization = self.create_organization()
    staff = self.create_staff(
        organization=organization, usd_tip_balance=300)
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase, verifier=staff,
        recipient=organization, tip_amount=300,
        currency=constants.USD_CURRENCY, status=Transaction.Status.Refunding)
    transaction.transfer_funds()

    # Reload staff and ensure their tip_balance was decremented.
    staff = Staff.get(staff.key())
    self.assertEqual(0, staff.jmd_tip_balance)
    self.assertEqual(0, staff.usd_tip_balance)

  def test_put_sets_uuid(self):
    transaction = Transaction()
    self.assertIsNone(transaction.uuid)
    transaction.put()
    self.assertIsNotNone(transaction.uuid)

  def test_put_keeps_existing_uuid(self):
    transaction_uuid = str(uuid.uuid4())
    transaction = Transaction(uuid=transaction_uuid)
    transaction.put()
    self.assertEqual(transaction_uuid, transaction.uuid)

  def test_get_by_uuid(self):
    transaction_uuid = str(uuid.uuid4())
    transaction = Transaction(uuid=transaction_uuid)
    transaction.put()
    self.assertIsNotNone(Transaction.get_by_uuid(transaction_uuid))

  def test_get_by_uuid_doesnt_exist(self):
    transaction = Transaction()
    transaction.put()
    self.assertIsNone(Transaction.get_by_uuid(str(uuid.uuid4())))

  def test_get_by_uuid_none(self):
    transaction = Transaction()
    transaction.put()
    self.assertIsNone(Transaction.get_by_uuid(None))

  def test_get_by_uuid_empty_string(self):
    transaction = Transaction()
    transaction.put()
    self.assertIsNone(Transaction.get_by_uuid(''))

  def test_get_by_uuid_trailing_whitespace(self):
    transaction = Transaction()
    transaction.put()
    uuid = transaction.uuid + ' '
    self.assertIsNone(Transaction.get_by_uuid(uuid))

  def test_is_refundable_by(self):
    owner_profile = self.create_profile()
    unauthorized_profile = self.create_profile()
    unauthorized_staff = self.create_staff(username='test@example')
    organization = self.create_organization(owner=owner_profile)
    staff = self.create_staff(organization=organization)

    transaction = self.create_transaction(
        recipient=organization,
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Completed)

    self.assertTrue(transaction.is_refundable_by(staff))
    self.assertTrue(transaction.is_refundable_by(owner_profile))
    self.assertFalse(transaction.is_refundable_by(unauthorized_profile))
    self.assertFalse(transaction.is_refundable_by(unauthorized_staff))

  def test_pending_transactions_cannot_be_refunded(self):
    owner_profile = self.create_profile()
    unauthorized_profile = self.create_profile()
    unauthorized_staff = self.create_staff()
    organization = self.create_organization(owner=owner_profile)
    staff = self.create_staff(organization=organization)

    transaction = self.create_transaction(
        recipient=organization,
        transaction_type=Transaction.Type.Purchase)

    self.assertFalse(transaction.is_refundable_by(staff))
    self.assertFalse(transaction.is_refundable_by(owner_profile))
    self.assertFalse(transaction.is_refundable_by(unauthorized_profile))
    self.assertFalse(transaction.is_refundable_by(unauthorized_staff))

  def test_transfers_cannot_be_refunded(self):
    recipient_profile = self.create_profile()
    sender_profile = self.create_profile()
    transaction = self.create_transaction(
        recipient=recipient_profile,
        transaction_type=Transaction.Type.Transfer)

    self.assertFalse(transaction.is_refundable_by(sender_profile))
    self.assertFalse(transaction.is_refundable_by(recipient_profile))

  def test_sender_cannot_refund_transaction(self):
    owner_profile = self.create_profile()
    organization = self.create_organization(owner=owner_profile)

    transaction = self.create_transaction(
        recipient=organization,
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Completed)

    self.assertTrue(transaction.is_refundable_by(owner_profile))
    self.assertFalse(transaction.is_refundable_by(transaction.sender))

  def test_refunds_are_not_refundable(self):
    owner_profile = self.create_profile()
    sender_profile = self.create_profile()
    unauthorized_profile = self.create_profile()
    unauthorized_staff = self.create_staff()
    organization = self.create_organization(owner=owner_profile)
    staff = self.create_staff(organization=organization)

    transaction = self.create_transaction(
        recipient=organization,
        sender=sender_profile,
        status=Transaction.Status.Refunded,
        transaction_type=Transaction.Type.Purchase)

    self.assertFalse(transaction.is_refundable_by(staff))
    self.assertFalse(transaction.is_refundable_by(owner_profile))
    self.assertFalse(transaction.is_refundable_by(sender_profile))
    self.assertFalse(transaction.is_refundable_by(unauthorized_staff))
    self.assertFalse(transaction.is_refundable_by(unauthorized_profile))

  def test_get_sender_time(self):
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Transfer)
    localized_time = pytz.utc.localize(
        transaction.created).astimezone(transaction.sender.get_timezone())
    self.assertEqual(localized_time, transaction.get_sender_time())

  def test_get_recipient_time(self):
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Transfer)
    localized_time = pytz.utc.localize(
        transaction.created).astimezone(transaction.recipient.get_timezone())
    self.assertEqual(localized_time, transaction.get_recipient_time())

  def test_get_localized_time(self):
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Transfer)
    localized_time = pytz.utc.localize(
        transaction.created).astimezone(transaction.recipient.get_timezone())
    self.assertEqual(
        localized_time,
        transaction.get_localized_time(transaction.recipient.get_timezone()))

  def test_get_jmd_transaction_amount(self):
    transaction = self.create_transaction(
        amount=1000,
        currency=constants.JMD_CURRENCY,
        status=Transaction.Status.Completed,
        transaction_type=Transaction.Type.Purchase)

    self.assertEqual('J$ 10.00', transaction.get_transaction_amount())

  def test_get_usd_transaction_amount(self):
    transaction = self.create_transaction(
        amount=1000,
        currency=constants.USD_CURRENCY,
        status=Transaction.Status.Completed,
        transaction_type=Transaction.Type.Purchase)

    self.assertEqual('US$ 10.00', transaction.get_transaction_amount())

  def test_get_jmd_transaction_amount_with_tip(self):
    transaction = self.create_transaction(
        amount=1000,
        tip_amount=100,
        currency=constants.JMD_CURRENCY,
        status=Transaction.Status.Completed,
        transaction_type=Transaction.Type.Purchase)

    self.assertEqual('J$ 11.00', transaction.get_transaction_amount())

  def test_get_usd_transaction_amount_with_tip(self):
    transaction = self.create_transaction(
        amount=1000,
        tip_amount=100,
        currency=constants.USD_CURRENCY,
        status=Transaction.Status.Completed,
        transaction_type=Transaction.Type.Purchase)

    self.assertEqual('US$ 11.00', transaction.get_transaction_amount())

  def test_verify_transaction_usd(self):
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        currency=constants.USD_CURRENCY, tip_amount=300,
        status=Transaction.Status.Completed)
    staff = self.create_staff(organization=transaction.recipient)
    self.assertIsNone(transaction.verifier)

    # Verify the transaction, and reload the staff and transaction.
    transaction.verify(staff)
    transaction = Transaction.get(transaction.key())
    staff = Staff.get(staff.key())

    # Ensure the verifier is set correctly, and the tip has been transferred.
    self.assertIsNotNone(transaction.verifier)
    self.assertIsNotNone(transaction.verified_time)
    self.assertAlmostEqual(datetime.datetime.now(), transaction.verified_time,
                           delta=datetime.timedelta(seconds=5))
    self.assertEqual(staff.key(), transaction.verifier.key())
    self.assertEqual(300, staff.get_tip_balance(constants.USD_CURRENCY))
    self.assertEqual(0, staff.get_tip_balance(constants.JMD_CURRENCY))

  def test_verify_transaction_jmd(self):
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        currency=constants.JMD_CURRENCY, tip_amount=300,
        status=Transaction.Status.Completed)
    staff = self.create_staff(organization=transaction.recipient)
    self.assertIsNone(transaction.verifier)

    # Verify the transaction, and reload the staff and transaction.
    transaction.verify(staff)
    transaction = Transaction.get(transaction.key())
    staff = Staff.get(staff.key())

    # Ensure the verifier is set correctly, and the tip has been transferred.
    self.assertIsNotNone(transaction.verifier)
    self.assertIsNotNone(transaction.verified_time)
    self.assertAlmostEqual(datetime.datetime.now(), transaction.verified_time,
                           delta=datetime.timedelta(seconds=5))
    self.assertEqual(staff.key(), transaction.verifier.key())
    self.assertEqual(0, staff.get_tip_balance(constants.USD_CURRENCY))
    self.assertEqual(300, staff.get_tip_balance(constants.JMD_CURRENCY))

  def test_verifying_verified_transaction_raises_error(self):
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        currency=constants.JMD_CURRENCY, tip_amount=300,
        verifier=self.create_staff(),
        status=Transaction.Status.Completed)
    staff = self.create_staff(organization=transaction.recipient)

    # Attempt to verify the transaction, and reload the staff and transaction,
    # and ensure it raises a RuntimeError
    self.assertRaises(RuntimeError, transaction.verify, staff)

    # Ensure the verifier information is unchanged, and no tips were
    # transferred.
    transaction = Transaction.get(transaction.key())
    staff = Staff.get(staff.key())
    self.assertIsNotNone(transaction.verifier)
    self.assertIsNone(transaction.verified_time)
    self.assertNotEqual(staff.key(), transaction.verifier.key())
    self.assertEqual(0, staff.get_tip_balance(constants.USD_CURRENCY))
    self.assertEqual(0, staff.get_tip_balance(constants.JMD_CURRENCY))

  def test_non_purchases_cannot_be_verified(self):
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Transfer,
        status=Transaction.Status.Completed)
    organization = self.create_organization()
    transaction.recipient = organization
    staff = self.create_staff(organization=organization)
    self.assertRaises(RuntimeError, transaction.verify, staff)

    # Ensure the transaction is not verified.
    self.assertIsNone(transaction.verifier)
    self.assertIsNone(transaction.verified_time)
    self.assertEqual(0, staff.get_tip_balance(constants.USD_CURRENCY))
    self.assertEqual(0, staff.get_tip_balance(constants.JMD_CURRENCY))

  def test_unauthorized_staff_cannot_verify_transaction(self):
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Completed)
    staff = self.create_staff()
    self.assertRaises(RuntimeError, transaction.verify, staff)

    # Ensure the transaction is not verified.
    self.assertIsNone(transaction.verifier)
    self.assertIsNone(transaction.verified_time)
    self.assertEqual(0, staff.get_tip_balance(constants.USD_CURRENCY))
    self.assertEqual(0, staff.get_tip_balance(constants.JMD_CURRENCY))

  def test_pending_purchases_cannot_be_verified(self):
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        tip_amount=300)
    organization = self.create_organization()
    transaction.recipient = organization
    staff = self.create_staff(organization=organization)
    self.assertRaises(RuntimeError, transaction.verify, staff)

    # Ensure the transaction is not verified.
    self.assertIsNone(transaction.verifier)
    self.assertIsNone(transaction.verified_time)
    self.assertEqual(0, staff.get_tip_balance(constants.USD_CURRENCY))
    self.assertEqual(0, staff.get_tip_balance(constants.JMD_CURRENCY))

  def test_processing_purchases_cannot_be_verified(self):
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Processing,
        tip_amount=300)
    organization = self.create_organization()
    transaction.recipient = organization
    staff = self.create_staff(organization=organization)
    self.assertRaises(RuntimeError, transaction.verify, staff)

    # Ensure the transaction is not verified.
    self.assertIsNone(transaction.verifier)
    self.assertIsNone(transaction.verified_time)
    self.assertEqual(0, staff.get_tip_balance(constants.USD_CURRENCY))
    self.assertEqual(0, staff.get_tip_balance(constants.JMD_CURRENCY))

  def test_cancelled_purchases_cannot_be_verified(self):
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Cancelled,
        tip_amount=300)
    organization = self.create_organization()
    transaction.recipient = organization
    staff = self.create_staff(organization=organization)
    self.assertRaises(RuntimeError, transaction.verify, staff)

    # Ensure the transaction is not verified.
    self.assertIsNone(transaction.verifier)
    self.assertIsNone(transaction.verified_time)
    self.assertEqual(0, staff.get_tip_balance(constants.USD_CURRENCY))
    self.assertEqual(0, staff.get_tip_balance(constants.JMD_CURRENCY))

  def test_refunding_purchases_cannot_be_verified(self):
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Refunding,
        tip_amount=300)
    organization = self.create_organization()
    transaction.recipient = organization
    staff = self.create_staff(organization=organization)
    self.assertRaises(RuntimeError, transaction.verify, staff)

    # Ensure the transaction is not verified.
    self.assertIsNone(transaction.verifier)
    self.assertIsNone(transaction.verified_time)
    self.assertEqual(0, staff.get_tip_balance(constants.USD_CURRENCY))
    self.assertEqual(0, staff.get_tip_balance(constants.JMD_CURRENCY))

  def test_refunded_purchases_cannot_be_verified(self):
    transaction = self.create_transaction(
        transaction_type=Transaction.Type.Purchase,
        status=Transaction.Status.Refunded,
        tip_amount=300)
    organization = self.create_organization()
    transaction.recipient = organization
    staff = self.create_staff(organization=organization)
    self.assertRaises(RuntimeError, transaction.verify, staff)

    # Ensure the transaction is not verified.
    self.assertIsNone(transaction.verifier)
    self.assertIsNone(transaction.verified_time)
    self.assertEqual(0, staff.get_tip_balance(constants.USD_CURRENCY))
    self.assertEqual(0, staff.get_tip_balance(constants.JMD_CURRENCY))
