
(function () {

    window.forms_helper_functions = {
        
        passwords: function () {
            $('#changePassword').click(function (e) {
                $('#changePasswordDialog').modal('show');
            });
            $('#init-termination-btn').click(function (e) {
                $('#terminate-account-dialog').modal('show');
            });
        },

        postaladdress: function () {
            window.deform && deform.addCallback(
               'postaladdressview-form',
               function() {
                  $('button.alternative-postal-address-button').click(function (){
                      $(this).toggleClass('hide');
                      $('.alternative-postal-address-form').toggleClass('hide');
                  });
           
                  $("#postaladderessview-form div.controls input").first().focus();
               }
           );
        },

        auto_displayname: function () {
            var givenName = $('input[name="givenName"]'),
                sn = $('input[name="sn"]');
            var update_displayname = function () {
                var displayName = $('input[name="displayName"]');
                if ( (!displayName.val()) &&
                     (givenName.val()) &&
                     (sn.val()) ) {
                       displayName.val(givenName.val() + ' ' + sn.val());
                }
            };
            givenName.blur(update_displayname);
            sn.blur(update_displayname);
        },

        horizontal_sequence: function () {
            var dataholder = $('span.dataholder#field-oid'),
                field_oid = dataholder.data('fieldoid'),
                min_len = parseInt(dataholder.data('min_len')),
                max_len = parseInt(dataholder.data('max_len')),
                now_len = parseInt(dataholder.data('now_len')),
                orderable = parseInt(dataholder.data('orderable'));
             deform.addCallback(
               field_oid,
               function(oid) {
                 oid_node = $('#'+ oid);
                 deform.processSequenceButtons(oid_node, min_len,
                                               max_len, now_len,
                                               orderable);
               }
             );
            if (orderable) {
                $( "#${oid}-orderable" ).sortable({handle: "span.deformOrderbutton"});
            }
        },

        form_always: function () {
            var field_formid = $('span.dataholder#field-formid').data('fieldformid');
            // Highlight all tabs with errors, move to the first one with the error
            window.deform && deform.addCallback(
               field_formid,
               function() {
                var alreadySelected = false;
        
                // If we get some errors, remove the active classes
                if($("div.tab-content fieldset div.has-error").length !== 0){
                  $("ul.form-tabs li.active").removeClass('active');
                  $("div.tab-content fieldset.active").removeClass('active in');
                }
                // Go through the errors, set first one to active and focus the field,
                // and add an 'error' class to all of the tabs with errors in them
                $("div.tab-content fieldset div.has-error").each( function() {
                  var errorId = $(this.parentNode).attr('id');
                  if(!alreadySelected){
                    $("ul.form-tabs li#" + errorId + '-list').addClass('active');
                    $("div.tab-content fieldset#" + errorId).addClass('active in');
                    $("#" + $(this).attr('id') + " div.controls input").focus();
                    alreadySelected = true;
                  }
                  $("ul.form-tabs li#" +errorId + '-list').addClass('text-danger');
                });
            });
            window.deform && deform.addCallback(
                field_formid,
                function () {
                    $('body').trigger('formready');
                }
            );
        },

        form_use_ajax: function () {
            var dataholder = $('span.dataholder#field-formid'),
                field_formid = dataholder.data('fieldformid'),
                ajax_options = dataholder.data('ajax_options');
            window.deform && deform.addCallback(
               field_formid,
               function(oid) {
                 if (window.beforeSubmit === undefined) {
                    window.beforeSubmit = function () {};
                 }
                 var targetElem = $('#' + oid);
                 var options = {
                        target: '#' + oid,
                        replaceTarget: true,
                        success: function(response_text, status_text, xhr) {
                          var loc = xhr.getResponseHeader('X-Relocate');
                          if (loc) {
                              document.location = loc;
                          };
                          targetElem.initDeformCallbacks();
                          deform.processCallbacks();
                          deform.focusFirstInput();
                          $('body').trigger('form-submitted');
                        },
                        error: function() {
                          $('body').trigger('communication-error');
                        },
                        beforeSubmit: window.beforeSubmit
        
                     },
                     extra_options = ajax_options || {};
                 console.log('Set AJAX form at ' + oid);
                 targetElem.ajaxForm($.extend(options, extra_options));
               }
            );
        },
        
        permissions: function () {
            var dataholder = $('span.dataholder#permissionsform-data'),
                formname = dataholder.data('formname'),
                msg_confirm = dataholder.data('msg_confirm');
        
            if ($('#' + formname + '-form').length > 0) {
                window.beforeSubmit = function (arr, $form, options) {
                    var q=confirm(msg_confirm);
                    if (!q) {
                      return false
                    }
                }
            }
        },

        nins: function () {
            var msg_verifying = $('span.dataholder#ninsform-data').data('msg_verifying');
            window.beforeSubmit = function () {
                $('#ninsview-formadd').
                    prop('disabled', true).
                    after('<p class="nin-wait">' + msg_verifying + '</p>');
            };
        },

        basewizard: function () {
            var dataholder = $('span.dataholder#basewizard-data'),
                step = parseInt(dataholder.data('step')),
                datakey = dataholder.data('datakey'),
                model = dataholder.data('model'),
                path = dataholder.data('path'),
                msg_done = dataholder.data('msg_done'),
                msg_sending = dataholder.data('msg_sending'),
                msg_next = dataholder.data('msg_next'),
                msg_back = dataholder.data('msg_back'),
                msg_dismiss = dataholder.data('msg_dismiss'),
                eduidwizard;
        
            $.fn.wizard.logging = true;
        
            eduidwizard = EduidWizard("#"+model+"-wizard", step, {
                    showCancel: true,
                    isModal: true,
                    submitUrl: path,
                    buttons: {
                      submitText: msg_done,
                      submittingText: msg_sending,
                      nextText: msg_next,
                      backText: msg_back,
                      cancelText: msg_dismiss,
                    },
                }
            );
        },

        wizard_norEduPersonNIN: function () {
            var msg_invalidnin = $('span.dataholder#ninwizard-data').data('msg_invalidnin');
        
            window.validateNIN = function (el) {
                var val = el.val(),
                    re = /^(18|19|20)\d{2}(0[1-9]|1[0-2])\d{2}[-\s]?\d{4}$/,
                    ret = {
                      status: true
                    };
                if (!re.test(val)) {
                  ret.status = false;
                  ret.msg = msg_invalidnin;
                }
                // if format is valid, then try to send to server
                return ret;
            };
        }
    };
}());
