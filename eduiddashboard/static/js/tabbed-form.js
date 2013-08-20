/*jslint vars: false, nomen: true, browser: true */
/*global $, console, alert, deform */

var TabbedForm = function (container) {
    "use strict";

    var get_form = function (url, target) {
            $.get(url + '/', {}, function (data) {
                target.html(data);
                if (deform.callbacks !== undefined &&
                        deform.callbacks.length === 0) {
                    $('form script').each(function (i, e) {
                        var f = new Function(e.innerHTML);
                        f();
                    });
                }
                deform.processCallbacks();
            }, 'html');
        },

        initialize = function () {
            var opentab = location.toString().split('#')[1];

            container.find('.nav-tabs a').click(function (e) {
                var named_tab = e.target.href.split('#')[1],
                    url = named_tab;
                get_form(url, $(".tab-pane.active"));
            });

            if (opentab === undefined) {
                container.find('.nav-tabs a').first().click();
            } else {
                container.find('.nav-tabs a[href=#' + opentab + ']').click();
            }
        };

    initialize();
};

$(document).ready(new TabbedForm($('.tabbable')));
