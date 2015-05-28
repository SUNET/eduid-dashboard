/*jslint vars: false, nomen: true, browser: true */
/*global $, console, alert, deform */

if (window.tabbedform === undefined) {
    window.tabbedform = {};
}

if (window.tabbedform.changetabs_calls === undefined) {
    window.tabbedform.changetabs_calls = [];
}

jQuery.fn.initDeformCallbacks = function () {
    "use strict";
    if (deform.callbacks !== undefined &&
            deform.callbacks.length === 0) {
        $(this).find('span.scriptholder').each(function (i, e) {
            var script = $(e).data('script');
            console.log('Executing form script: ' + script);
            window.forms_helper_functions[script]();
        });
    }
};

var TabbedForm = function (container) {
    "use strict";

    var get_form = function (url, target) {
            $.get(url + '/', {}, function (data, status_text, xhr) {
                var loc = xhr.getResponseHeader('X-Relocate');
                if (loc) {
                      document.location = loc;
                };
                target.html(data);
                $('div.tab-pane.active button.btn-primary').enable(false);
                target.initDeformCallbacks();
                deform.processCallbacks();
                $('div.tab-pane.active button.btn-primary').enable(true);

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

        initialize_nav_tabs = function () {
            var nav_tabs = container.find('.nav-tabs a.main-nav-tabs');
            $(nav_tabs).unbind('click');
            $(nav_tabs).click(function (e) {
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

            window.forms_helper_functions.initialize_pending_actions();

            $('body').bind('formready', function () {
                // callbacks
                window.tabbedform.changetabs_calls.forEach(function (func) {
                    if (func !== undefined) {
                        func(container);
                    }
                });
            });

            $('body').one('reloadtabs', function () {
                initialize_nav_tabs();
                window.forms_helper_functions.initialize_pending_actions();
            });

            if (opentab === undefined || opentab === "") {
                container.find('.nav-tabs a.main-nav-tabs').first().click();
            } else {
                window.forms_helper_functions.initialize_verification(opentab);
            }
            window.tabbedform.changetabs_calls.push(window.forms_helper_functions.auto_displayname);
        };

    initialize();
};

$(document).ready(new TabbedForm($('.tabbable')));
