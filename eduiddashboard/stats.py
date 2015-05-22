"""
Statistics gathering.

An instance of either NoOpStats() or StatHat() is made available through the
request object, so that statistics information can be logged without any checks
for configured object or not.

Example usage in some view:

    request.stats.count('dashboard/verify_code_completed', 1)

"""

from stathatasync import StatHat

__author__ = 'ft'


class NoOpStats(object):
    """
    No-op class used when stathats_user is not set.

    Having this no-op class initialized in case there is no stathats_user
    configured allows us to not check if request.stats is set everywhere.
    """
    def __init__(self, logger = None):
        self.logger = logger

    def count(self, name, value):
        if self.logger:
            self.logger.info('No-op stats count: {!r} {!r}'.format(name, value))

    def value(self, name, value):
        if self.logger:
            self.logger.info('No-op stats value: {!r} {!r}'.format(name, value))


def get_stats_instance(settings, logger):
    """
    Use the configuration to determine what kind of statistics logger we should use.

    :param settings: Pyramid settings
    :param logger: logging logger
    :return: Instance of object with a `count` and a `value` function.
    """
    if 'stathat_username' in settings:
        return StatHat(settings.get('stathat_username'))
    return NoOpStats(logger = logger)
