(function ($) {
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
}(jQuery));
