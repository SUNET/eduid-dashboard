/*jslint vars: false, browser: true, nomen: true, regexp: true */
/*global jQuery, alert */

var userstatus = {

  renderStatus: function (status_url) {
    var result;

    $.ajax({
      url: status_url,
      type: "GET"
    }).done(function (userData) {
      $('.loa-big .level').html(userData.loa);
      $('.level-assurance-description .level').html(userData.loa);
      $('.profile-filled .percentaje').html(userData.profile_filled);
      $('.profile-filled .bar').css('width', userData.profile_filled);
      $('.circles-widget').addClass('level-' + userData.loa);
    });

    return result;
  }
};

