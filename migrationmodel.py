# FROM: http://stackoverflow.com/questions/1567148/method-to-migrate-app-engine-models

"""Models which know how to migrate themselves"""

import logging
from google.appengine.ext import db
from google.appengine.api import memcache


class MigrationError(Exception):
  """Error migrating"""

class MigratingModel(db.Model):
  """A model which knows how to migrate itself.

  Subclasses must define a class-level migration_version integer attribute.
  """

  current_migration_version = db.IntegerProperty(required=True, default=0)

  def __init__(self, *args, **kw):
    if not kw.get('_from_entity'):
      # Assume newly-created entities needn't migrate.
      try:
        kw.setdefault('current_migration_version',
                      self.__class__.migration_version)
      except AttributeError:
        msg = ('migration_version required for %s'
                % self.__class__.__name__)
        logging.critical(msg)
        raise MigrationError, msg
    super(MigratingModel, self).__init__(*args, **kw)

  @classmethod
  def from_entity(cls, *args, **kw):
    # From_entity() calls __init__() with _from_entity=True
    obj = super(MigratingModel, cls).from_entity(*args, **kw)
    return obj.migrate()

  def migrate(self):
    target_version = self.__class__.migration_version
    if self.current_migration_version < target_version:
      migrations = range(self.current_migration_version+1, target_version+1)
      for self.current_migration_version in migrations:
        method_name = 'migrate_%d' % self.current_migration_version
        logging.debug('%s migrating to %d: %s'
                       % (self.__class__.__name__,
                          self.current_migration_version, method_name))
        getattr(self, method_name)()
      db.put(self)
    return self
