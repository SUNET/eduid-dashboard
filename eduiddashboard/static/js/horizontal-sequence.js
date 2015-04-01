function ($) {
    var field_oid = $('span.dataholder#field-oid').data('fieldoid'),
        min_len = $('span.dataholder#field-oid').data('min_len'),
        max_len = $('span.dataholder#field-oid').data('max_len'),
        now_len = $('span.dataholder#field-oid').data('now_len'),
        orderable = $('span.dataholder#field-oid').data('orderable');
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
}(jQuery);

