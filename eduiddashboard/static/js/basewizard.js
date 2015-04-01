function ($) {
    var step = $('span.dataholder#basewizard-data').data('step'),
        datakey = $('span.dataholder#basewizard-data').data('datakey'),
        model = $('span.dataholder#basewizard-data').data('model'),
        path = $('span.dataholder#basewizard-data').data('path'),
        msg_done = $('span.dataholder#basewizard-data').data('msg_done'),
        msg_sending = $('span.dataholder#basewizard-data').data('msg_sending'),
        msg_next = $('span.dataholder#basewizard-data').data('msg_next'),
        msg_back = $('span.dataholder#basewizard-data').data('msg_back'),
        msg_dismiss = $('span.dataholder#basewizard-data').data('msg_dismiss'),
        msg_invalidnin = $('span.dataholder#basewizard-data').data('msg_invalidnin');

    $.fn.wizard.logging = true;
    var active_card = step,
        datakey = datakey,
        eduidwizard;
    eduidwizard = EduidWizard("#"+model+"-wizard", active_card, {
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
        });

    window.exampleValidator = function (el) {
      var val = el.val(),
          re = /^[0-9]{8}-?[0-9]{4}$/,
          ret = {
            status: true
          };
      if (!re.test(val)) {
        ret.status = false;
        ret.msg = msg_invalidnin;
      }
      return ret;
    }
}(jQuery);
