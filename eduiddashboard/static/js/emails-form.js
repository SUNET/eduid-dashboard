/*jslint vars: false, nomen: true, browser: true */
/*global $, console, alert, tabbedform */


(function () {
    "use strict";

    var success = function(data) {
            contaner_e.html(data);
        },


        initialize = function (container, url) {

            container.find('.add-new-email').click(function (e) {
                container.find('.emailform').toggleClass('hide');
                container.find('.add-new-email').toggleClass('active');
            });

            container.find('table.emails a').click(function (e) {
                e.preventDefault();
                e.stopPropagation();
                var action = e.target.parentNode.href.split('#')[1],
                    email = $(e.target).parents('tr').find('td.email').html();

                container.find('form input[name=email]').val(email);
                container.find('form button[name=' + action + ']').clic(;  };  ;
        tabbedform.changetabs_calls.push(initialize);

}());
