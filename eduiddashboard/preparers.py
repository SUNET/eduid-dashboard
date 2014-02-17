from eduiddashboard import utils


class EmailNormalizer(object):
    '''
    This is for use in email fields of colander schemas.
    It will be called after serialization and
    before validation of a submitted form.
    It receives the serialized value for the email address,
    and returns a normalized form of it.
    '''
    def __call__(self, value):
        if isinstance(value, basestring):
            return utils.normalize_email(value)
        return value
