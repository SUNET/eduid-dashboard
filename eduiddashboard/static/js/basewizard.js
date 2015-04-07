(function ($) {
    var dataholder = $('span.dataholder#basewizard-data'),
        step = dataholder.data('step'),
        datakey = dataholder.data('datakey'),
        model = dataholder.data('model'),
        path = dataholder.data('path'),
        msg_done = dataholder.data('msg_done'),
        msg_sending = dataholder.data('msg_sending'),
        msg_next = dataholder.data('msg_next'),
        msg_back = dataholder.data('msg_back'),
        msg_dismiss = dataholder.data('msg_dismiss'),
        msg_invalidnin = dataholder.data('msg_invalidnin');

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
}(jQuery));
