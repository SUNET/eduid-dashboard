import json

from pyramid_deform import FormView


class BaseFormView(FormView):

    route = ''

    buttons = ('save', )
    use_ajax = True

    def __init__(self, context, request):
        super(BaseFormView, self).__init__(request)
        self.user = context.user
        self.context = context

        self.classname = self.__class__.__name__.lower()

        self.ajax_options = json.dumps({
            'replaceTarget': True,
            'url': context.route_url(self.route),
            'target': "div.{classname}-form-container".format(
                classname=self.classname)
        })

        self.form_options = {
            'formid': "{classname}-form".format(classname=self.classname),
        }

        bootstrap_form_style = getattr(self, 'bootstrap_form_style', None)
        if bootstrap_form_style is not None:
            self.form_options['bootstrap_form_style'] = bootstrap_form_style

    def appstruct(self):
        return self.schema.serialize(self.user)

    def get_template_context(self):

        return {
            'formname': self.classname
        }

    def failure(self, e):
        context = super(BaseFormView, self).failure(e)

        context.update(self.get_template_context())

        return context

    def show(self, form):
        context = super(BaseFormView, self).show(form)

        context.update(self.get_template_context())

        return context
