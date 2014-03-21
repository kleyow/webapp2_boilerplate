import time

from google.appengine.api import memcache


class lock(object):
  """Library for handling locking using memcache."""

  def __init__(self, key, *args, **kwargs):
    self.key = key
    self.args = args
    self.kwargs = kwargs

  def __enter__(self):
    lock = acquire_lock(self.key, *self.args, **self.kwargs)
    if not lock:
      raise RuntimeError('Unable to acquire lock for "%s"' % self.key)

  def __exit__(self, exc_type, exc_val, exc_tb):
    release_lock(self.key)


def acquire_lock(key, tries=None, backoff=2):
  """Acquires a lock on a specific key, blocking until it is acquired."""

  if tries is not None and tries < 0:
    raise ValueError('tries must be greater than 0.')

  if backoff <= 1:
    raise ValueError('backoff must be greater than 1.')

  if tries is None:
    tries_left = True
  else:
    tries_left = tries

  delay = 3

  while tries_left:
    # Try to acquire the lock and return successfully.
    lock_acquired = memcache.add(get_lock_key_name(key), True)
    if lock_acquired:
      return True

    # Someone else has the lock.
    # Decrement tries_left, sleep, and increase the future delay.
    else:
      if tries_left is not True:
        tries_left -= 1

      time.sleep(delay)
      delay *= backoff

  # If we exit the while loop, we've run out of tries.
  return False


def release_lock(key):
  memcache.delete(get_lock_key_name(key))


def get_lock_key_name(key):
  if not isinstance(key, basestring):
    raise ValueError('Expected string, got %s' % type(key))
  return '%s.lock' % key
