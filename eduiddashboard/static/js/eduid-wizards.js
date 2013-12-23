/*jslint vars: false, nomen: true, browser: true */
/*global $, console, alert, Wizard */


$.fn.serializeObject = function () {
    var o = {};
    var a = this.serializeArray();
    $.each(a, function() {
        if (o[this.name] !== undefined) {
            if (!o[this.name].push) {
                o[this.name] = [o[this.name]];
            }
            o[this.name].push(this.value || '');
        } else {
            o[this.name] = this.value || '';
        }
    });
    return o;
};


var EduidWizard = function (container_path, options) {

    var wizard = $(container_path).wizard(options);

    Wizard.prototype._onNextClick = function () {
        var jsondata,
            currentCard = this.getActiveCard(),
            step = currentCard.index;

        this.log("handling 'next' button click (custom method)");

        if (currentCard.index === (this._cards.length - 1)) {
            // This is the last card
            this.reset().close();

        } else if (currentCard.validate()) {
            jsondata = currentCard.el.find('input, select').serializeObject();
            $.extend(jsondata, {
                step: currentCard.index,
                action: 'next_step'
            });
            $.ajax({
                url: this.args.submitUrl,
                data: jsondata,
                type: 'POST',
                success: function (data, textStatus, jqXHR){
                    if (data.status === 'ok') {
                        // go to next card
                        currentCard = wizard.incrementCard();
                    }
                    else if (data.status == 'failure') {
                        for(var input in data.data) {
                            if (wizard.el.find('[name=' + input + ']')) {
                                wizard.el.find('[name=' + input + ']').after(
            "<span class=\"help-inline\"><span class=\"error\">" + data.data[input] +
            "</span></span>");
                            }
                        }

                        // handle the errors form or another server messages
                    }
                },
                error: function (event, jqXHR, ajaxSettings, thrownError) {
                    console.debug('Hey!, there are some errors here ' +
                                  thrownError);
                }
            });
        }
    };

    wizard.cancelButton.click(function (e) {
        $.ajax({
            url: wizard.args.submitUrl,
            data: {
                action: 'dismissed'
            },
            type: 'POST',
            success: function (data, textStatus, jqXHR){
                wizard.reset().close();
            },
            error: function (event, jqXHR, ajaxSettings, thrownError) {
                console.debug('Hey!, there are some errors here ' +
                              thrownError);
                wizard.close();
            }
        });
    });


    wizard.show();
};
