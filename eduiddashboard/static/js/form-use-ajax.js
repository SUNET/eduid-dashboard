(function ($) {
    var field_formid = $('span.dataholder#field-formid').data('fieldformid');
    window.deform && deform.addCallback(
       field_formid,
       function(oid) {
         if (window.beforeSubmit === undefined) {
            window.beforeSubmit = function () {};
         }

         var options = {
                target: '#' + oid,
                replaceTarget: true,
                success: function(response_text, status_text, xhr) {
                  var loc = xhr.getResponseHeader('X-Relocate');
                  if (loc) {
                      document.location = loc;
                  };
                  deform.processCallbacks();
                  deform.focusFirstInput();
                  $('body').trigger('form-submitted');
                },
                error: function() {
                  $('body').trigger('communication-error');
                },
                beforeSubmit: window.beforeSubmit

             },
             extra_options = ${field.ajax_options} || {};
         $('#' + oid).ajaxForm($.extend(options, extra_options));
       }
    );
}(jQuery));
