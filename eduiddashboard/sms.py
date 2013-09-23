import logging
logger = logging.getLogger(__name__)

#from eduid_msg import tasks

def send_sms(mobile_number, msg):
    logger.info(u"SMS to %s: %s" % (mobile_number, msg))
    #tasks.send(msg, to)
