(function ($) {
    var msg_verifying = $('span.dataholder#ninsform-data').data('msg_verifying');

       window.beforeSubmit = function () {
           $('#ninsview-formadd').
              prop('disabled', true).
              after('<p class="nin-wait">' + msg_verifying + '</p>');
       };
}(jQuery));
