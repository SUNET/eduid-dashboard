import json

from pyramid_deform import FormView


class BaseFormView(FormView):

    route = ''

    buttons = ('submit', )
    use_ajax = True

    def __init__(self, request):
        super(BaseFormView, self).__init__(request)
        self.user = request.session.get('user', None)

        self.classname = self.__class__.__name__.lower()

        self.ajax_options = json.dumps({
            'replaceTarget': True,
            'url': self.request.route_url(self.route),
            'target': "div.{classname}-form-container".format(
                classname=self.classname)
        })

        self.form_options = {
            'formid': "{classname}-form".format(classname=self.classname),
        }

    def appstruct(self):
        return self.schema.serialize(self.user)

    def failure(self, e):
        context = super(BaseFormView, self).failure(e)

        context.update({
            'formname': self.classname,
            'object': self.schema.serialize(self.user),
        })

        return context

    def show(self, form):
        context = super(BaseFormView, self).show(form)

        context.update({
            'formname': self.classname,
            'object': self.schema.serialize(self.user),
        })

        return context
