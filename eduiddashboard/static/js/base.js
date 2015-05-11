(function ($) {
      if (window.messagesTimer === undefined) {
          window.messagesTimer = null;
      }

      window.clearMessages = function() {
        if (window.messagesTimer) {
          window.clearTimeout(window.messagesTimer);
        }
        $('.alert').not('.fixed').fadeOut(400, function (){
          $(this).remove();
        });
      };

      var setMessagesTimer = function () {
        window.messagesTimer = window.setTimeout(window.clearMessages, 10000);
      };

      window.messagesResetTimer = function (index) {
        window.clearTimeout(window.messagesTimer);
        // do a fancy effect
        setMessagesTimer();
        $($('.alert')[index]).animate({opacity: 0.25}, 150).delay(150).animate({opacity: 1}, 150);

      };

      $(document).ready(function () {
        $(document).ready(function () {$('div#content-block').show()});
        $('a.null-link').click(function (e) {
            e.preventDefault();
        });
        setMessagesTimer();
      });
}(jQuery));

