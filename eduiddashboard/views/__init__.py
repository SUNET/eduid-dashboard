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
    route = None

    def __init__(self, context, request):
        self.request = request
        self.user = request.session.get('user', None)
        self.schema = self.schema()

        classname = self.__class__.__name__.lower()

        if self.route is None:
            self.route = classname

        ajax_options = {
            'replaceTarget': True,
            'url': self.request.route_url(self.route),
            'target': "div.{classname}-form".format(classname=classname)
        }

        self.form = Form(self.schema, buttons=('submit',),
                         use_ajax=True,
                         ajax_options=json.dumps(ajax_options),
                         formid="{classname}-form".format(classname=classname))

        self.context = {
            'form': self.form,
            'formname': classname,
            'object': self.schema.serialize(self.user),
        }

    def get(self):
        raise NotImplemented()

    def post(self):
        raise NotImplemented()
