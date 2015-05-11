(function ($) {
  var dataholder = $('span.dataholder#profile-data'),
      workmode = dataholder.data('workmode'),
      open_wizard = dataholder.data('openwizard'),
      datakey = dataholder.data('datakey'),
      wizard_nins_url = dataholder.data('wizard_nins_url'),
      userstatus_url = dataholder.data('userstatus-url'),
      polling_timeout = parseInt(dataholder.data('polling_timeout'));

  if (open_wizard === 'True') {
    open_wizard = true;
  } else {
    open_wizard = false;
  }

  var loa_popovers = function () {
    $('.circles-widget-labels a').popover({
      placement: 'bottom',
      trigger: 'hover',
      delay: {
        show: 750,
        hide: 750
      }
    });
  
    $('.circles-widget-labels a').click(function (e) {
        e.preventDefault();
    });
  };
  
  $(document).ready(function () {
      $("a[data-toggle=tooltip]").tooltip();
      $("button[data-toggle=tooltip]").tooltip();
      loa_popovers();
  
      if ((workmode === 'personal') && open_wizard) {
        if (datakey === '') {
          var params = {};
        } else {
          var params = {
              norEduPersonNIN: datakey
            },
            initial_card = 1;
        }
        $.get( wizard_nins_url, params, function (data, textStatus, jqXHR) {
            var wizardholder = $('div.openwizard');
            wizardholder.html(data);
            wizardholder.find('span.scriptholder').each(function (i, e) {
                var script = $(e).data('script');
                console.log('Executing wizard form script: ' + script);
                window.forms_helper_functions[script]();
            });
        });
      }
      // show progress
      var profile_filled = $('span.dataholder#profile-data').data('profile_filled'),
          pb = $('div.profile-filled-progress-bar');
      pb.css('width', profile_filled + '%');
  
      function showStatus() {
        userstatus.renderStatus(userstatus_url);
      }
  
      function reloadTab() {
        // reload active tab in order to refresh the HTML
        $('.nav-tabs li.active a').click();
        showStatus();
      }
  
      $('body').on('form-submitted action-executed', function() {
        // move the form messages to the messages main area
        $('.alert').not($('div.messages div.alert')).not('.fixed').each(function (index) {
            var exists = false,
                message = $(this).html();
            $('.messages div.alert').each(function (index2) {
              if ($(this).html() == message) {
                exists = true;
                messagesResetTimer(index);
              }
            });
            if (!exists) {
              $(this).appendTo(".messages");
            } else {
              $(this).hide();
            }
        });
  
        window.setTimeout(clearMessages, 10000);
      });
  
      if (workmode === 'personal') {
        $('body').on('form-submitted action-executed', function() {
          showStatus();
        });
  
        $('body').on('action-executed', function() {
          reloadTab();
        });
      } else {
        function statusPolling() {
          showStatus();
          window.setTimeout(statusPolling, polling_timeout);
        }
        statusPolling();
        $('body').on('action-executed', function() {
          location.reload();
        });
      }
  
      $('body').on('communication-error', function(){
        var message = $('#communication-error-template').text();
        $('.container div.messages').append(message);
        window.setTimeout(function () {
          $('.communication-error').fadeOut();
        }, 5*1000);
      });
  
      $('body').on('communication-error-permissions', function(){
        var message = $('#communication-error-permissions-template').text();
        $('.container div.messages').append(message);
        window.setTimeout(function () {
          $('.communication-error-permissions').fadeOut();
        }, 5*1000);
      });
  
      $("#askDialog").bind('show', function () {
      });
  
      $("#askDialog").bind('shown', function () {
        $(this).find("#askDialogInput").focus();
      });
  
      $("#askDialog .cancel-button, #askDialog .finish-button").click( function (e) {
        e.preventDefault();
        if ($("div.ninsview-form-container").length > 0) {
            $(this).hide();
            location.reload();
        } else {
            closeAskDialog();
        }
      });
  
      $("#askDialog .ok-button").click( function (e) {
        e.preventDefault();
        okAskDialog();
      });
  });
  
  function closeAskDialog() {
    $("#askDialog").modal('hide');
    $("body").trigger('action-executed');
  };
  
  function okAskDialog() {
    var input = document.getElementById("askDialogInput");
    input.askcallback(input.value);
  };
  
  window.askDialog = function (identifier, actionsURL, prompt, defaultvalue, placeholder, askcallback) {
    var input = document.getElementById("askDialogInput");
    input.value = defaultvalue;
    input.placeholder = placeholder;
    input.askcallback = askcallback; // radical
    $("#askDialog .info-container").empty();
    $("#askDialog").find('.btn').show();
    $("#askDialog").find('.divDialogElements').show();
    $("#askDialog").find('.finish-button').hide();
    document.getElementById("askDialogPrompt").innerHTML = prompt;
    $("#askDialog .resend-code").attr('data-identifier', identifier);
    $("#askDialog .resend-code").attr('href', actionsURL);
    $("#askDialog .extra-info").html($(".askdialog-extra-info").html());
    $("#askDialog").modal("show");
  };

}(jQuery));

