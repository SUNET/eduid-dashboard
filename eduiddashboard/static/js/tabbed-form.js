/*jslint vars: false, nomen: true, browser: true */
/*global $, console, alert, deform */

if (window.tabbedform === undefined) {
    window.tabbedform = {};
}

if (window.tabbedform.changetabs_calls === undefined) {
    window.tabbedform.changetabs_calls = [];
}


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

                container.find("a[data-toggle=tooltip]").tooltip();
                container.find("button[data-toggle=tooltip]").tooltip();
                container.find("label[data-toggle=tooltip]").tooltip();

            }, 'html').fail(function (xhr) {
                if (xhr.status == 401) {
                    $('body').trigger('communication-error-permissions');
                } else {
                    $('body').trigger('communication-error');
                }
            });
        },

        initialize_pending_actions = function () {
            $('ul.pending-actions a').click(function (e) {
                var named_tab = e.target.href.split('#')[1];
                container.find('.nav-tabs a[href=#' + named_tab + ']').click();
            });
        },

        initialize_nav_tabs = function () {
            container.find('.nav-tabs a').click(function (e) {
                var named_tab = e.target.href.split('#')[1],
                    url = named_tab;

                container.find('ul.nav-tabs a').parent().removeClass('active');
                container.find('ul.nav-tabs a[href=#' + named_tab + ']').
                    parent().addClass('active');

                get_form(url, $(".tab-pane.active"));
            });
        },

        initialize = function () {
            var opentab = location.toString().split('#')[1];

            initialize_nav_tabs();

            initialize_pending_actions();

            $('body').bind('formready', function () {
                window.tabbedform.changetabs_calls.forEach(function (func) {
                    if (func !== undefined) {
                        func(container);
                    }
                });
            });

            $('body').bind('reloadtabs', function () {
                initialize_nav_tabs();
                initialize_pending_actions();
            });

            if (opentab === undefined || opentab === "") {
                container.find('.nav-tabs a').first().click();
            } else {
                container.find('.nav-tabs a[href=#' + opentab + ']').click();
            }
        };

    initialize();
};

$(document).ready(new TabbedForm($('.tabbable')));
