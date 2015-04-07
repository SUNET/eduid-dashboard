$(document).ready(
    (function () {
        var givenName = $('input[name="givenName"]'),
            sn = $('input[name="sn"]');
        var update_displayname = function () {
            var displayName = $('input[name="displayName"]');
            if ( (!displayName.val()) &&
                 (givenName.val()) &&
                 (sn.val()) ) {
                   displayName.val(givenName.val() + ' ' + sn.val());
            }
        };
        givenName.blur(update_displayname);
        sn.blur(update_displayname);
    })()
);
