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
          action = userData.pending_actions[index][1];
        pendingActionsHTML = pendingActionsHTML + '<li><a href="#' + formid + '"' + '>' + action + '</a></li>';
      }
      $('.pending-actions').empty();
      $('.pending-actions').html(pendingActionsHTML);
      $('body').trigger('reloadtabs');

      for (index in userData.tabs) {
        var tab = userData.tabs[index],
          tabHTML = tab.label,
          pending_actions = '';

        if (tab.status && tab.status.pending_actions) {
            pending_actions = tab.status.pending_actions;
        }
        if (tab.status && tab.status.icon) {
          tabHTML = '<i class="' + tab.status.icon + '"></i> ' + tabHTML;
        }
        $('.nav-tabs a[href=#' + tab.id + ']').html(tabHTML);
        $('.nav-tabs a[href=#' + tab.id + ']').attr('title', pending_actions);
      }
    });
  }
};

