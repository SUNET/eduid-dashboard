/*jslint vars: false, nomen: true, browser: true */
/*global $, console, alert, deform */

if (window.deform === undefined) {
    window.deform = {};
}

var TabbedForm = function (container) {
    "use strict";

    var get_form = function (url, target) {
            $.get(url + '/', {}, function (data) {
                target.empty();
                target.html(data);
                deform.load();
            }, 'html');
        },

        initialize = function () {
            container.find('.nav-tabs a').click(function (e) {
                var named_tab = e.target.href.split('#')[1],
                    url = named_tab;
                get_form(url, $('#' + named_tab));
            });
            container.find('.nav-tabs a').first().click();
        };

    initialize();
};

$(document).ready(new TabbedForm($('.tabbable')));
