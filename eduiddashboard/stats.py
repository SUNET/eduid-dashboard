"""
Statistics gathering.

An instance of either NoOpStats() or Statsd() is made available through the
request object, so that statistics information can be logged without any checks
for configured object or not.

Example usage in some view:

    request.stats.count('verify_code_completed')

"""

from eduid_common.stats import NoOpStats, Statsd


__author__ = 'ft'


def get_stats_instance(settings, logger):
    """
    Use the configuration to determine what kind of statistics logger we should use.

    :param settings: Pyramid settings
    :param logger: logging logger
    :return: Instance of object with a `count` and a `value` function.
    """
    if 'statsd_server' in settings:
        return Statsd(settings.get('statsd_server'), settings.get('statsd_port', 8125), prefix='dashboard')
    return NoOpStats(logger = logger, prefix='dashboard')
