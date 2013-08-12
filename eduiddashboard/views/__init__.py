import json

from deform import Form


class BaseFormView(object):
    """
    Provide the handler to personal data form
        * GET = Rendering template
        * POST = Creating or modifing personal data,
                    return status and flash message
    """

    schema = None

    def __init__(self, request):
        self.request = request
        self.user = request.session.get('user', None)
        self.schema = self.schema()

        classname = self.__class__.__name__.lower()

        ajax_options = {
            'replaceTarget': True,
            'url': self.request.route_url(classname),
            'target': "div.{classname}-form".format(classname=classname)
        }

        self.form = Form(self.schema, buttons=('submit',),
                         use_ajax=True,
                         ajax_options=json.dumps(ajax_options))

        self.context = {
            'form': self.form,
            'formname': classname,
            'object': self.schema.serialize(self.user),
        }

    def get(self):
        raise NotImplemented()

    def post(self):
        raise NotImplemented()
