(function ($) {
    var dataholder = $('span.dataholder#basewizard-data'),
        step = parseInt(dataholder.data('step')),
        datakey = dataholder.data('datakey'),
        model = dataholder.data('model'),
        path = dataholder.data('path'),
        msg_done = dataholder.data('msg_done'),
        msg_sending = dataholder.data('msg_sending'),
        msg_next = dataholder.data('msg_next'),
        msg_back = dataholder.data('msg_back'),
        msg_dismiss = dataholder.data('msg_dismiss'),
        eduidwizard;

    $.fn.wizard.logging = true;

    eduidwizard = EduidWizard("#"+model+"-wizard", step, {
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

}(jQuery));
