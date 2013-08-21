from colander import null
import deform


class MongoCheckboxWidget(deform.widget.CheckboxWidget):

    def __init__(self, true_val=True, false_val=False, **kwargs):
        super(MongoCheckboxWidget, self).__init__(true_val=true_val,
                                                  false_val=false_val,
                                                  **kwargs)

    def deserialize(self, field, pstruct):
        if pstruct is null:
            return self.false_val

        if (pstruct == self.true_val or
                (isinstance(self.true_val, bool) and
                    bool(pstruct) == self.true_val)):
            return self.true_val

        return self.false_val


class HorizontalSequenceWidget(deform.widget.SequenceWidget):

    def __init__(
            self,
            template=('horizontal-squence'),
            item_template=('horizontal-sequence_item'),
            **kwargs
    ):
        super(HorizontalSequenceWidget, self).__init__(
            item_template=item_template,
            **kwargs
        )
