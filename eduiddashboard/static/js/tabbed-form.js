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
            $.get(url + '/', {}, function (data, status_text, xhr) {
                var loc = xhr.getResponseHeader('X-Relocate');
                if (loc) {
                      document.location = loc;
                };
                target.html(data);
                $('div.tab-pane.active button.btn-primary').enable(false);
                if (deform.callbacks !== undefined &&
                        deform.callbacks.length === 0) {
                    $('form script').each(function (i, e) {
                        var f = new Function(e.innerHTML);
                        f();
                    });
                }
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

        initialize_pending_actions = function () {
            $('ul.pending-actions a').click(function (e) {
                var action_path = e.target.href.split('#')[1];
                initialize_verification(action_path);
            });
        },

        initialize_verification = function(action_path) {
            if (action_path !== undefined && action_path !== "") {
                if (action_path.indexOf('/') === -1) {
                    container.find('.nav-tabs a[href=#' + action_path + ']').click();
                } else {
                    var segments = action_path.split('/');
                    $(document).one('formready', function () {
                        var form_container = $('.' + segments[0] + 'view-form-container');
                        var link_selector = 'input.btn-link[name="' + segments[1] + '"]';
                        var verification_links = form_container.find(link_selector);
                        if (verification_links.length === 1) {
                            var verification_link = verification_links[0];
                        } else {
                            var link_index = + segments[2];
                            var verification_link = verification_links[link_index];
                        }
                        verification_link.click();
                    });
                    container.find('.nav-tabs a[href=#' + segments[0] + ']').click();
                }
            }
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

        initialize_account_termination = function () {
            $('#init-termination-btn').click(function (e) {
                $('#terminate-account-dialog').modal('show');
            });
        },

        initialize = function () {
            var opentab = location.toString().split('#')[1];

            initialize_nav_tabs();

            initialize_pending_actions();

            $('body').bind('formready', function () {
                // callbacks
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
                initialize_verification(opentab);
            }

            initialize_account_termination();
        };

    initialize();
};

$(document).ready(new TabbedForm($('.tabbable')));
