function ($) {
    var formname = $('span.dataholder#permissionsform-data').data('formname'),
        msg_confirm = $('span.dataholder#permissionsform-data').data('msg_confirm');

  if ($('#' + formname + '-form').length > 0) {
      window.beforeSubmit = function (arr, $form, options) {
          var q=confirm(msg_confirm);
          if (!q) {
            return false
          }
      }
  }
}(jQuery);
