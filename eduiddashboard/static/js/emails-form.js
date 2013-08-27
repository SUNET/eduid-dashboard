/*jslint vars: false, nomen: true, browser: true */
/*global $, console, alert, tabbedform */


(function () {
    "use strict";

    var send_verification = function (url, email, callback) {
            $.post(url, {email: email}, callback, 'json');
        },

        initialize = function (container) {

            container.find('.boolean-action-widget a').click(function (e) {
                var url = e.target.parentElement.href,
                    email = $(e.target).parents('div.deformSeqItem')
                            .find('input[name=email]').val();

                e.preventDefault();
                send_verification(url, email);

            });

        };

    $(document).ready(function () {
        tabbedform.changetabs_calls.push(initialize);
    });
}());
