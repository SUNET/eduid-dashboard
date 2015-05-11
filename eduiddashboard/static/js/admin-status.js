(function ($) {
    $('#dbtabs a').click(function (e) {
        e.preventDefault();
        $(this).tab('show');
    })
    $(function () {
        $('#dbtabs a:first').tab('show');
    })
}(jQuery));
