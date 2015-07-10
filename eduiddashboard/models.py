import re

import colander
import deform

from eduiddashboard.i18n import TranslationString as _
from eduiddashboard.preparers import EmailNormalizer
from eduiddashboard.validators import (EmailUniqueValidator,
                                       PasswordValidator,
                                       OldPasswordValidator,
                                       PermissionsValidator,
                                       NINReachableValidator,
                                       NINUniqueValidator,
                                       NINRegisteredMobileValidator,
                                       MobilePhoneUniqueValidator,
                                       CSRFTokenValidator,
                                       ResetPasswordFormValidator)
from eduiddashboard.widgets import permissions_widget


SEARCHER_ATTTRIBUTE_TYPES = [
    (u'mail', _('email')),
    (u'mobile', _('phone mobile number')),
    (u'norEduPersonNIN', _('national identity number')),
]


@colander.deferred
def csrf_token(node, kw):
    request = kw.get('request')
    token = request.session.get_csrf_token()
    return token


class CSRFTokenSchema(colander.MappingSchema):
    csrf = colander.SchemaNode(
        colander.String(),
        widget=deform.widget.HiddenWidget(),
        validator=CSRFTokenValidator(),
        default=csrf_token,
    )


class BooleanMongo(colander.Boolean):

    def __init__(self, false_choices=('False', 'false', '', False),
                 true_choices=('True', 'true', True),
                 false_val=False,
                 true_val=True):
        super(BooleanMongo, self).__init__(false_choices, true_choices,
                                           false_val, true_val)


class All_StopOnFirst(colander.All):

    def __call__(self, node, value):
        for validator in self.validators:
            try:
                validator(node, value)
            except colander.Invalid as e:
                raise colander.Invalid(node, e.msg)

class All_StopOnFirst_Switch(object):
    """
    Handles multiple "All_StopOnFirst" validators.
    """
    def __init__(self, All_StopOnFirst_dict):
        """
        :param All_StopOnFirst_dict: a dictionary of All_StopOnFirst objects

        For all the keys in "All_StopOnFirst_dict", a search will be made to see
        if the same value can be found in "request.POST". If the search get a hit, the corresponding validator
        will be executed.
        """
        self.validator_dict = All_StopOnFirst_dict

    def __call__(self, node, value):
        request = node.bindings.get('request')

        if 'add_by_mobile' in request.POST:
            current_validator = self.validator_dict['add_by_mobile']
        else:
            current_validator = self.validator_dict['add']
            for validator in current_validator.validators:
                try:
                    validator(node, value)
                except colander.Invalid as e:
                    raise colander.Invalid(node, e.msg)


class Email(CSRFTokenSchema):
    mail = colander.SchemaNode(colander.String(),
                               preparer=EmailNormalizer(),
                               validator=colander.All(colander.Email(),
                                                      EmailUniqueValidator()),
                               title=_('email'),
                               widget=deform.widget.TextInputWidget(
                                   mask=_('Email address'),
                                   error_class='text-danger',
                                   css_class='form-control'))


NINFormatValidator = colander.Regex(
    regex=re.compile(r'^(18|19|20)\d{2}(0[1-9]|1[0-2])\d{2}[-\s]?\d{4}$'),
    msg=_('The Swedish national identity number should be entered as yyyymmddnnnn')
)

MobileFormatValidator = colander.Regex(
    r'^\+\d{10,20}$|^07[0236]\d{7}$',
    msg=_('Invalid telephone number. It must be a valid Swedish number, or written using international notation,'
          ' starting with "+" and followed by 10-20 digits.'),
)


def normalize_nin(nin):
    # Normalize nin, removing hyphen and whitespaces
    newnin = nin.replace(' ', '')
    newnin = newnin.replace('-', '')
    return newnin


class NIN(CSRFTokenSchema):
    """
        Allowed NIN input format:

        197801011234 (normalized form)
        19780101 1234
        19780101-1234
    """

    validator_switch = All_StopOnFirst_Switch(
        {'add': All_StopOnFirst(
            NINFormatValidator,
            NINUniqueValidator(),
            NINReachableValidator()
        ), 'add_by_mobile': All_StopOnFirst(
            NINFormatValidator,
            NINUniqueValidator(),
            NINRegisteredMobileValidator()
        )})

    """
    validator_switch = All_StopOnFirst_Switch(
        {'add': All_StopOnFirst(
            NINFormatValidator,
            NINUniqueValidator(),
            NINReachableValidator()
        ), 'add_by_mobile': All_StopOnFirst(
            NINFormatValidator,
            NINUniqueValidator()
        )})
    """
    norEduPersonNIN = colander.SchemaNode(
        colander.String(),
        title=_('Swedish national identity number'),
        validator=validator_switch,
        widget=deform.widget.TextInputWidget(mask=_('yyyymmddnnnn'),
                                             css_class='form-control',
                                             error_class='text-danger')
    )

@colander.deferred
def preferred_language_widget(node, kw):
    request = kw.get('request')
    lang_choices = request.registry.settings['available_languages'].items()
    return deform.widget.SelectWidget(values=lang_choices,
                                      error_class='text-danger')


class Person(CSRFTokenSchema):
    givenName = colander.SchemaNode(colander.String(),
                                    widget=deform.widget.TextInputWidget(
                                        error_class='text-danger',
                                        css_class='form-control'),
                                    readonly=True,
                                    title=_('Given name'))
    sn = colander.SchemaNode(colander.String(),
                             widget=deform.widget.TextInputWidget(
                                        error_class='text-danger',
                                        css_class='form-control'),
                             title=_('Surname'))
    displayName = colander.SchemaNode(colander.String(),
                                      widget=deform.widget.TextInputWidget(
                                        error_class='text-danger',
                                        css_class='form-control'),
                                      title=_('Display name'))
    preferredLanguage = colander.SchemaNode(colander.String(),
                                            title=_('Preferred language'),
                                            missing='',
                                            widget=preferred_language_widget)


@colander.deferred
def password_readonly(node, kw):
    request = kw.get('request')
    return request.session.get('last_generated_password')


class Passwords(CSRFTokenSchema):

    old_password = colander.SchemaNode(
        colander.String(),
        title=_('Current password'),
        widget=deform.widget.PasswordWidget(size=20,
                                            error_class='text-danger',
                                            css_class="form-control"),
        validator=OldPasswordValidator())

    use_custom_password = colander.SchemaNode(
        colander.Boolean(),
        widget=deform.widget.CheckboxWidget(),
        title=_('Use my own password'),
        missing='false')

    suggested_password = colander.SchemaNode(
        colander.String(),
        title=_('Suggested password'),
        widget=deform.widget.TextInputWidget(
            readonly=True,
            css_class='suggested-password form-control'
        ),
        missing=password_readonly)

    custom_password = colander.SchemaNode(
        colander.String(),
        title=_('Custom password'),
        widget=deform.widget.PasswordWidget(
            size=20,
            error_class='text-danger',
            css_class='custom-password form-control'),
        validator=PasswordValidator(),
        missing='')

    repeated_password = colander.SchemaNode(
        colander.String(),
        title=_('Repeat the password'),
        widget=deform.widget.PasswordWidget(
            size=20,
            error_class='text-danger',
            css_class='custom-password form-control'),
        missing='')


class EmailResetPassword(CSRFTokenSchema):

    email_or_username = colander.SchemaNode(
        colander.String(),
        title="",
        widget=deform.widget.TextInputWidget(
            error_class='text-danger',
            css_class='form-control'
        ),
        validator=ResetPasswordFormValidator(
            NINFormatValidator,
            MobileFormatValidator,
            colander.Email(),
        )
    )


class NINResetPassword(CSRFTokenSchema):
    email_or_username = colander.SchemaNode(
        colander.String(),
        title="",
        widget=deform.widget.TextInputWidget(
            error_class='text-danger',
            css_class='form-control'
        ),
        validator=ResetPasswordFormValidator(
            NINFormatValidator,
            MobileFormatValidator,
            colander.Email(),
        )
    )


class ResetPasswordStep2(CSRFTokenSchema):
    use_custom_password = colander.SchemaNode(
        colander.Boolean(),
        widget=deform.widget.CheckboxWidget(),
        title=_('Use my own password'),
        missing='false')

    suggested_password = colander.SchemaNode(
        colander.String(),
        title=_('Suggested password'),
        widget=deform.widget.TextInputWidget(
            readonly=True,
            css_class='suggested-password form-control'
        ),
        missing=password_readonly)

    custom_password = colander.SchemaNode(colander.String(),
                                          widget=deform.widget.PasswordWidget(
                                              size=20,
                                              error_class='text-danger',
                                              css_class='form-control custom-password'
                                          ),
                                          validator=PasswordValidator(),
                                          title=_("New Password"),
                                          missing='')
    repeated_password = colander.SchemaNode(colander.String(),
                                            widget=deform.widget.PasswordWidget(
                                                size=20,
                                                error_class='text-danger',
                                                css_class='form-control custom-password'),
                                            title=_("Confirm New Password"),
                                            missing='')

    def validator(self, node, data):
        if data['custom_password'] != data['repeated_password']:
            raise colander.Invalid(node,
                                   _("Passwords doesn't match"))


@colander.deferred
def postal_address_default_country(node, kw):
    request = kw.get('request')
    default_location = request.registry.settings.get('default_country_location')
    return default_location


class PostalAddress(colander.MappingSchema):
    address = colander.SchemaNode(colander.String(),
                                  title=_('Address'),
                                  widget=deform.widget.TextInputWidget(
                                     error_class='text-danger',
                                     css_class='form-control'),
                                  )
    locality = colander.SchemaNode(colander.String(),
                                   title=_('City'),
                                   widget=deform.widget.TextInputWidget(
                                     error_class='text-danger',
                                     css_class='form-control'),
                                   )
    postalCode = colander.SchemaNode(colander.String(),
                                     title=_('Postal code'),
                                     widget=deform.widget.TextInputWidget(
                                        error_class='text-danger',
                                        css_class='form-control'),
                                     validator=colander.Length(min=5, max=6))
    country = colander.SchemaNode(colander.String(),
                                  title=_('Country'),
                                  widget=deform.widget.TextInputWidget(
                                        error_class='text-danger',
                                        css_class='form-control'),
                                  default=postal_address_default_country)


class Mobile(CSRFTokenSchema):
    mobile = colander.SchemaNode(colander.String(),
                                 validator=colander.All(
                                     MobileFormatValidator,
                                     MobilePhoneUniqueValidator()
                                 ),
                                 title=_('mobile'),
                                 widget=deform.widget.TextInputWidget(
                                     mask=_('Mobile phone number'),
                                     error_class='text-danger',
                                     css_class='form-control'))


class Permissions(colander.Schema):
    eduPersonEntitlement = colander.SchemaNode(colander.List(),
                                               title='',
                                               validator=PermissionsValidator(),
                                               missing=[],
                                               default=[],
                                               widget=permissions_widget)


class UserSearcher(colander.MappingSchema):
    query = colander.SchemaNode(colander.String(),
                                description=_('Search for users'),
                                title=_('query'),
                                widget=deform.widget.TextInputWidget(
                                    error_class='text-danger'
                                    ))
