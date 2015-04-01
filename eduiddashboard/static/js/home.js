function ($) {
    var sLengthMenu = $('span.dataholder#home-data').data('sLengthMenu'),
        sInfo = $('span.dataholder#home-data').data('sInfo'),
        sInfoFiltered = $('span.dataholder#home-data').data('sInfoFiltered'),
        sSearch = $('span.dataholder#home-data').data('sSearch'),
        sZeroRecords = $('span.dataholder#home-data').data('sZeroRecords'),
        sNext = $('span.dataholder#home-data').data('sNext'),
        sPrevious = $('span.dataholder#home-data').data('sPrevious');

        $(document).ready( function () {
            $('#user-table').dataTable({
                "oLanguage": {
                     "sLengthMenu": sLengthMenu,
                     "sInfo": sInfo,
                     "sInfoFiltered": " - " + sInfoFiltered,
                     "sSearch": sSearch + ":",
                     "sZeroRecords": sZeroRecords + ".",
                     "oPaginate": {
                        "sNext": sNext,
                        "sPrevious": sPrevious
                     }
                },
                "aoColumnDefs": [
                    { "bSearchable": false, "aTargets": [ -1 ] },
                    { "bSortable": false, "aTargets": [ -1 ] },
                    { "sClass": "text-center", "aTargets": [ -1 ] }
                ]
            });
        } );
}(jQuery);

