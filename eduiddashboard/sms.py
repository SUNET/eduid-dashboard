import logging
logger = logging.getLogger(__name__)

#from eduid_msg import tasks

def send_sms(request, mobile_number, msg):
    site_name = request.registry.settings.get("site.name", "eduID")
    msg = u'[%s] %s' % (site_name, msg)
    logger.info(u"SMS to %s: %s" % (mobile_number, msg))
    #tasks.send(msg, mobile_number)
