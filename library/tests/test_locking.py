import unittest2

from google.appengine.api import memcache
from library import testing, locking


class TestLocking(testing.TestCase, unittest2.TestCase):

  def test_get_lock_key_name_only_accepts_strings(self):
    self.assertEqual('item.lock', locking.get_lock_key_name('item'))
    self.assertRaises(ValueError, locking.get_lock_key_name, object())

  def test_acquire_lock_creates_memcache_entry(self):
    key = 'KEY'
    self.assertTrue(locking.acquire_lock(key))
    lock_key_name = locking.get_lock_key_name(key)
    self.assertTrue(memcache.get(lock_key_name))

  def test_release_lock(self):
    # Ensure that a lock's memcache entry is deleted upon release.
    key = 'KEY'
    self.assertTrue(locking.acquire_lock(key))
    lock_key_name = locking.get_lock_key_name(key)
    self.assertTrue(memcache.get(lock_key_name))
    stats = memcache.get_stats()
    self.assertEqual(1, stats['items'])
    locking.release_lock(key)
    self.assertIsNone(memcache.get(lock_key_name))

  def test_lock_context_manager(self):
    # Ensure that lock creates an entry in memcache.
    key = 'KEY'
    lock_key_name = locking.get_lock_key_name(key)
    with locking.lock(key):
      self.assertTrue(memcache.get(lock_key_name))
      stats = memcache.get_stats()
      self.assertEqual(1, stats['items'])
    self.assertIsNone(memcache.get(lock_key_name))

  def test_lock_context_manager_raises_exeception_when_key_is_locked(self):
    # Acquire lock on a key.
    key = 'KEY'
    lock_key_name = locking.get_lock_key_name(key)
    locking.acquire_lock(lock_key_name)
    stats = memcache.get_stats()
    self.assertEqual(1, stats['items'])

    # Ensure a RuntimeError is raised.
    with self.assertRaises(RuntimeError):
      with locking.lock(lock_key_name, tries=1):
        pass
