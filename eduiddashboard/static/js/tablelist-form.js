/*jslint vars: false, nomen: true, browser: true */
/*global $, console, alert, tabbedform */


(function () {
    "use strict";

    var success = function(data) {
            contaner_e.html(data);
        },

        initialize = function (container, url) {
            if (container.find('.form-content .alert-error').length > 0){
                container.find('.form-content').show();
            }

            container.find('.add-new').click(function (e) {
                container.find('.form-content').toggleClass('hide');
                container.find('.add-new').toggleClass('active');
            });

            container.find('table.table input[type=radio]').click(function (e) {
                var action = $(e.target).attr('name'),
                    value = $(e.target).val(),
                    actions_url = $('.actions-url').attr('data-url');

                container.find('.form-content').addClass('hide');
                container.find('.add-new').removeClass('active');

                $.post(actions_url, {
                    action: action,
                    identifier: value
                },
                function(data, statusText, xhr) {
                    var messageHTML = '<div class="alert alert-' + data.result +
                    '"><button type="button" class="close" data-dismiss="alert">&times;</button>' +
                    data.message + '</div>';
                    container.find('.tab-content').prepend(messageHTML);
                    if(data.action == 'remove' && data.result == 'ok') {
                        // special case of removing rows
                        container.find('table.table tr[data-identifier=' + data.identifier +']').remove();
                    }
                    $('body').trigger('action-executed');
                },
                'json');
            });
    };
    tabbedform.changetabs_calls.push(initialize);
}());
