(function ($) {
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
}(jQuery));
