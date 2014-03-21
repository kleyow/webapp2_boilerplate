from contextlib import contextmanager
import logging

import stripe


@contextmanager
def stripe_connection(func, *args, **kwargs):
  """Context manager for making Stripe API calls.

  Allows us to use

    with stripe_connection(stripe.Customer.retrieve, customer_id) as customer:
      do_something(customer)

  to make Stripe API calls without all the error handling boilerplate.

  If an error occurs while connection the the Stripe API, we set the value
  returned by this context manager to None.
  """

  try:
    value = func(*args, **kwargs)

  except stripe.APIConnectionError, e:
    # Reraise all `stripe.APIConnectionError`s, so they can be repeated by the
    # taskqueue.
    logging.exception(e.message)
    raise e

  except Exception, e:
    # Any other kind of exception should simply be logged and the value
    # returned by the Stripe API call should be None.
    logging.exception(e.message)
    value = None

  finally:
    yield value
