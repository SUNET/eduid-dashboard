function ($) {
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
}(jQuery);
