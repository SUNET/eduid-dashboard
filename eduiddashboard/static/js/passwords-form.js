(function () {
    $(document).ready(function (e) {
        $('#changePassword').click(function (e) {
            $('#changePasswordDialog').modal('show');
        });
        $('#init-termination-btn').click(function (e) {
            $('#terminate-account-dialog').modal('show');
        });
    });
}());
