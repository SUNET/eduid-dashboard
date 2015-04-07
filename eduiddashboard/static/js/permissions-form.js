(function ($) {
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
}(jQuery));
