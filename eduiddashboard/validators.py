import translationstring
from colander import Invalid

_ = translationstring.TranslationStringFactory('eduiddashboard')

PASSWORD_MIN_LENGTH = 5


class PasswordValidator(object):
    """ Validator which check the security level of the password """

    def __call__(self, node, value):
        if len(value) < PASSWORD_MIN_LENGTH:
            err = _('"${val}" has to be more than ${len} characters length',
                    mapping={'val':value, 'len':PASSWORD_MIN_LENGTH})
            raise Invalid(node, err)
