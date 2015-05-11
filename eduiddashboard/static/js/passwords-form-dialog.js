(function () {
    var dataholder = $('span.dataholder#password-form-dialog-data'),
        password_min_entropy = parseInt(dataholder.data('entropy')),
        msg_stronger = dataholder.data('msg_stronger'),
        msg_again = dataholder.data('msg_again'),
        pwquality_errors = undefined,
        pwequality_errors = undefined,
        pwdialog = $("#changePasswordDialog"),

        get_input = function (name) {
            // return an input container from jQuery
            return pwdialog.find("input[name=" + name + "]");
        },

        get_password = function (name) {
            // remove spaces from passwords, just like vccs-client does
            var passwd = get_input(name).val();
            if (passwd !== undefined) {
                return passwd.split(' ').join('');
            } else {
                return '';
            }
        },

        password_form_toggle = function () {
            if (get_input("use_custom_password").is(":checked")) {
                pwdialog.find("span.suggested-password").parents(".form-group").hide();
                // Show the custom password input and help text
                pwdialog.find(".custom-password").parents(".form-group").fadeIn();
                pwdialog.find("div.password-format").fadeIn();
            } else {
                // Empty the custom password field and hide help text
                pwdialog.find(".custom-password").parents(".form-group").removeClass("has-error").
                    hide().find("input").val("");
                pwdialog.find("div.password-format").hide();
                pwdialog.find(".help-block .live").remove();
                // Show the suggested password
                pwdialog.find("span.suggested-password").parents(".form-group").fadeIn();
            }
            update_save_button();
        },

        init_password_form = function () {
            // Reset form values every time the modal form is brought up
            get_input("old_password").val("");
            get_input("custom_password").val("");
            get_input("repeated_password").val("");
            get_input("use_custom_password").off("click");
            get_input("use_custom_password").click(password_form_toggle);
            password_form_toggle();
        },

        init_password_dialog = function () {
            var events,
                body = $('body');
            $("#changePassword").click(function() {
                 pwdialog.modal('show');
                 init_password_form();
                 $('#changePassword').trigger('password-dialog-open');
             });

            events = $._data(body[0], 'events')['form-submitted'];
            events = $.map(events, function (o) {
              return o.handler;
            });

            body.off('form-submitted');
            body.on('form-submitted', function () {
                msg_area = pwdialog.find('div.alert');
                if (msg_area.hasClass('alert-danger')) {
                    msg_area.addClass('fixed');
                } else {
                    msg_area.removeClass('fixed');
                    $('body').trigger('action-executed');
                    pwdialog.find('a.close').click();
                }
            });

            $.each(events, function (i, o) {
                 body.on('form-submitted', o);
            });

            $('#init-termination-btn').click(function (e) {
                $('#terminate-account-dialog').modal('show');
            });
        },

        update_save_button = function () {
            var save_btn = pwdialog.find("button[name=save]"),
                enable_button = true;

            if (get_password("old_password") == '') {
                enable_button = false;
            }
            if (enable_button) {
                if (get_input("use_custom_password").is(":checked")) {
                    if (pwquality_errors != 0 || pwequality_errors != 0) { enable_button = false }
                }
            }
            if (! enable_button) {
                save_btn.addClass('disabled');
            } else {
                save_btn.removeClass('disabled');
            }
        },

        error_messages = function (input, messages) {
            var input_parents = input.parents(".form-group")
                  .toggleClass("has-error", (messages.length > 0)),
                messages_html = '';
            input_parents.find(".controls span.help-block.errors").remove();
            if (messages.length > 0) {
                $.each(messages, function(i, message) {
                    messages_html += "<p class='text-danger live'>" + message + "</p>";
                });

                input_parents.find(".controls").append("<span class='help-block errors'>" + messages_html + "</span>");
            }
            update_save_button();
        },

        check_custom_password = function () {
            var custom_password = get_password('custom_password'),
                repeated_password = get_password('repeated_password'),
                verdict = zxcvbn(custom_password, ["eduid"]),
                suggested_password = $('.suggested-password').html().split(' ').join(''),
                messages = [],
                password_field = get_input("custom_password");

            password_field.val(custom_password);  // properly remove spaces for pwcheck

            /*
            console.debug("Entropy: " + verdict.entropy);
            console.debug("Matches: ", verdict.match_sequence);
            console.debug("Password: ", password);
            */

            if (custom_password !== suggested_password &&
                  (verdict.entropy < password_min_entropy)) {
                messages.push(msg_stronger);
            }
            pwquality_errors = messages.length;
            error_messages(password_field.parent(), messages);
            check_repeated_password();  // a change to this password might also affect equality status
        },

        check_repeated_password = function () {
            var password = get_password('custom_password'),
                repeated_password = get_password('repeated_password'),
                repeated_password_field = get_input("repeated_password"),
                messages = [];

            repeated_password_field.val(repeated_password);  // properly remove spaces for pwcheck

            if (repeated_password != password) {
                messages.push(msg_again);
            }
            pwequality_errors = messages.length;
            error_messages(repeated_password_field, messages);
        },

        check_old_password = function () {
            // old password field change, update save button status
            update_save_button();
        };

    $('body').on('form-submitted', function () {
        if (get_input("use_custom_password").is(":checked")) {
          check_custom_password();
        }
    });

    /* Password meter */
    var required_entropy = password_min_entropy;
    var pwbar_options = {};
    pwbar_options.ui = {
        //verdicts: ["Too weak", "Halfway", "Almost", "Strong"],
        showVerdicts: false,
        scores: [required_entropy * 0.25,
                 required_entropy * 0.5,
                 required_entropy * 0.75,
                 required_entropy],
        bootstrap2: false
    };
    pwbar_options.common = {
        zxcvbn: true,
        usernameField: 'eduid'   // make zxcvbn give negative score to the word eduID
    };
    get_input('custom_password').pwstrength(pwbar_options);

    // Set up triggers on change events
    var triggers = "change focusout keyup onpaste paste mouseleave";
    get_input('old_password').on(triggers, check_old_password);
    get_input('custom_password').on(triggers, check_custom_password);
    get_input('repeated_password').on(triggers, check_repeated_password);

    $(document).ready(function () {
        init_password_form();
        init_password_dialog();
    });
}());
