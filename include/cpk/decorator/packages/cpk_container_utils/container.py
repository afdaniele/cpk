import os
import logging

from .constants import HEALTH_FILE

# create logger
logging.basicConfig()
logger = logging.getLogger(os.environ.get('CPK_PROJECT_NAME', 'container'))
logger.setLevel(logging.INFO)
if 'DEBUG' in os.environ and os.environ['DEBUG'].lower() in ['true', 'yes', '1']:
    logger.setLevel(logging.DEBUG)


def get_container_health():
    health = "ND"
    if os.path.isfile(HEALTH_FILE):
        try:
            with open(HEALTH_FILE, 'rt') as fin:
                health = fin.read().strip('\n').strip(' ')
        except BaseException:
            logger.warning('An error occurred while trying to fetch the container\'s health.')
    return health


def _set_container_health(new_health):
    health = get_container_health()
    if new_health not in ['healthy', 'unhealthy']:
        logger.warning('Health "{0}" not recognized!'.format(new_health))
        return
    # ---
    if health == new_health:
        return
    logger.info('Updating container health [{0}] -> [{1}]'.format(health, new_health))
    # try to write the health status
    try:
        with open(HEALTH_FILE, 'wt') as fout:
            fout.write(new_health)
    except BaseException:
        logger.warning('An error occurred while trying to set the container\'s health.')


def set_container_healthy():
    _set_container_health('healthy')


def set_container_unhealthy():
    _set_container_health('unhealthy')
