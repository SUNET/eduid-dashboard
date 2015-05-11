(function ($) {
    var dataholder = $('span.dataholder#home-data'),
        sLengthMenu = dataholder.data('sLengthMenu'),
        sInfo = dataholder.data('sInfo'),
        sInfoFiltered = dataholder.data('sInfoFiltered'),
        sSearch = dataholder.data('sSearch'),
        sZeroRecords = dataholder.data('sZeroRecords'),
        sNext = dataholder.data('sNext'),
        sPrevious = dataholder.data('sPrevious');

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
}(jQuery));
