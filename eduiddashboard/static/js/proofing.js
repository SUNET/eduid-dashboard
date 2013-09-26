/*jslint vars: false, nomen: true, browser: true */
/*global $, console, alert, deform */

if (window.proofing === undefined) {
    window.proofing = {};
}

if (window.tabbedform === undefined) {
    window.tabbedform = {};
}
if (window.tabbedform.changetabs_calls === undefined) {
    window.tabbedform.changetabs_calls = [];
}


var Proofing = function (container) {
    "use strict";

    var save_and_go = function (e) {
            // Save the actual form
            var proofing_url = e.target.value,
                fieldset = $(e.target).parents('.deformSeqItem');

            if (fieldset.length > 0) {
                proofing_url += '?index=' + fieldset.index()
            }

            e.preventDefault();

            container.find('button[value=save]').click();

            $('body').bind('formready', function () {
                document.location = proofing_url;
            })

        },

        initialize = function () {
            $('body').bind('formready', function (e) {
                container.find('button[type=proofing]').click(save_and_go);

            });
            $('a.deformSeqAdd').click(function () {
                container.find('button[type=proofing]').unbind('click');
                container.find('button[type=proofing]').click(save_and_go);
            });
        };

    initialize();
};

$(document).ready(new Proofing($('.tabbable')));
