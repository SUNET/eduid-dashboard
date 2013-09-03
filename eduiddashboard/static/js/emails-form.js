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

            container.find('table.emails a').click(function (e) {
                e.preventDefault();
                e.stopPropagation();
                var action = e.target.parentNode.href.split('#')[1],
                    email = $(e.target).parents('tr').find('td.email').html();

                container.find('.form-content').addClass('hide');
                container.find('.add-new').removeClass('active');

                container.find('form input[name=mail]').val(email);
                container.find('form button[name=' + action + ']').click();
            });


            container.find('table.emails input[type=radio]').click(function (e) {
                var action = $(e.target).attr('name'),
                    value = $(e.target).val();

                container.find('.form-content').addClass('hide');
                container.find('.add-new').removeClass('active');

                container.find('form input[name=mail]').val(value);
                container.find('form button[name=' + action + ']').click();
            });

        };

        tabbedform.changetabs_calls.push(initialize);

}());
