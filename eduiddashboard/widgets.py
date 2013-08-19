import deform


class MongoCheckboxWidget(deform.widget.CheckboxWidget):

    def __init__(self, true_val=True, false_val=True, **kwargs):
        super(MongoCheckboxWidget, self).__init__(true_val=true_val,
                                                  false_val=false_val,
                                                  **kwargs)
