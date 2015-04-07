(function ($) {
    var dataholder = $('span.dataholder#field-oid'),
        field_oid = dataholder.data('fieldoid'),
        min_len = dataholder.data('min_len'),
        max_len = dataholder.data('max_len'),
        now_len = dataholder.data('now_len'),
        orderable = dataholder.data('orderable');
     deform.addCallback(
       field_oid,
       function(oid) {
         oid_node = $('#'+ oid);
         deform.processSequenceButtons(oid_node, min_len,
                                       max_len, now_len,
                                       orderable);
       }
     );
    if (orderable) {
        $( "#${oid}-orderable" ).sortable({handle: "span.deformOrderbutton"});
    }
}(jQuery));
