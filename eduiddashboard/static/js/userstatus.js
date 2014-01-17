/*jslint vars: false, browser: true, nomen: true, regexp: true */
/*global jQuery, alert */

var userstatus = {

  renderStatus: function (status_url) {
    var pendingActionsHTML, index;

    $.ajax({
      url: status_url,
      type: "GET"
    }).done(function (userData) {
      $('.loa-big .level').html(userData.loa);
      $('.level-assurance-description .level').html(userData.loa);
      $('.profile-filled .percentaje').html(userData.profile_filled);
      $('.profile-filled .bar').css('width', userData.profile_filled);
      $('.circles-widget').addClass('level-' + userData.loa);
      pendingActionsHTML = '';
      for (index in userData.pending_actions) {
        var formid = userData.pending_actions[index][0],
          action = userData.pending_actions[index][1],
          action_type = userData.pending_actions[index][2],
          verification_needed = userData.pending_actions[index][3];
        if (verification_needed === -1) {
            pendingActionsHTML = pendingActionsHTML + '<li><a href="#' + formid + '"' + '>' + action + '</a></li>';
        } else {
            var link = '#' + formid + '/' + action_type + '/' + verification_needed;
            pendingActionsHTML = pendingActionsHTML + '<li><a href="' + link + '">' + action + '</a></li>';
        }
      }
      $('.pending-actions').empty();
      $('.pending-actions').html(pendingActionsHTML);
      $('body').trigger('reloadtabs');

    });
  }
};

