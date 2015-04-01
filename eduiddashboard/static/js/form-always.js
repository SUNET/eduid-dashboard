
function ($) {
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
}(jQuery);
