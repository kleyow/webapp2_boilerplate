$(document).ready(function() {

  /*
  // All forms should take the CSRF token and make it set it as a hidden
  // input on all forms.
  (function() {
    $('form').append($('<input>').attr({
      type: 'hidden',
      name: csrf_key,
      value: csrf_token
    }));
  })();
  */

  // The #transaction.add-credit form has some quirks to it.
  (function() {
    var $form = $('#transaction form.add-credit');

    // The first funding source should be checked by default.
    $form.find('table.funding-sources :radio:first').prop('checked', true);

    $form.submit(function() {
      // Ensure we have a proper input field for the amount.
      var amount = $(this).find('.amount-choices a.active').data('value');
      $(this).append($('<input type="hidden" name="amount" />').val(amount));
    });
  })();

  // The .funding-sources table has a selector in a table.
  // Any row we choose should toggle that selector.
  // When there is a card checked, we should show the options for that card.
  (function() {
    var $table = $('table.funding-sources');
    var $actions = $table.siblings('.funding-actions');

    $table.find('tr').on('click', function() {
      $(this).find('td.selector input').prop('checked', true).change();
    });

    $table.find(':radio').change(function() {
      var $selected = $table.find(':radio:checked');
      var card = $selected.val();
      $actions.show().find('input[name="funding_source"]').val(card);
    });
  })();

  // The #transaction .add-credit form should use Stripe.
  // We assume the Stripe <script> tag is included in the template.
  (function() {
    $('form#funding-source').submit(function(e) {
      // Set our non-private key so that Stripe knows who we are.
      Stripe.setPublishableKey('pk_live_j7LsGt3eAIsqQfGij0qMx8YP');

      // Disable the submit button to prevent duplicate submits...
      $(this).find('button').attr('disabled', 'disabled');

      // Send a request to create a token, trigger the callback above.
      Stripe.createToken({
        number: $(this).find('#card_number').val(),
        cvc: $(this).find('#card_cvc').val(),
        exp_month: $(this).find('#card_exp_month').val(),
        exp_year: $(this).find('#card_exp_year').val()
      }, stripeResponseHandler);

      // Don't actually submit the form.
      return false;
    });

    // What happens when we hear back from Stripe.
    var stripeResponseHandler = function(status, response) {
      var $form = $('form#funding-source');

      if (response.error) {
        // Hide and remove all previous error tooltips.
        $form.find('input').each(function() {
          var tooltip = $(this).data('tooltip');
          if (tooltip) {
            tooltip.$tip.hide();
          }
        });
        $form.find('input').removeData('tooltip');

        // Re-enable the button so that we can try again.
        $form.find('button').removeAttr('disabled');
        $form.find('button').data('spinner-reset')();

        // Show that errors happened...
        var $field = $form.find('#card_' + response.error.param);
        $field.tooltip({
          title: response.error.message
          // trigger: 'manual' keeps the tooltip visible (and covering up
          // other fields). Let's leave this out for now.
        }).tooltip('show');
      } else {
        // Append relevate data as a hidden input to the form.
        $('<input>').attr({
          type: 'hidden',
          name: 'card_token',
          value: response['id']
        }).appendTo($form);

        // We don't want the card cvc
        $form.find('#card_cvc').remove();

        // We only want the last four digits:
        $form.find('#card_number').val(response['card']['last4']);

        // Change the name of that field before submitting.
        $form.find('#card_number').attr('name', 'card_last_four_digits');

        // And submit the HTMLElement form (not the jQuery form...).
        $form.get(0).submit();
      }
    };
  })();

  // When the button with data-spinner is clicked, it should become a spinner.
  (function() {
    $('button[data-spinner]').each(function() {
      var $button = $(this);

      $button.data('spinner-show', function() {
        // If we're showing for the first time (no progress bar created yet).
        if (!$button.data('spinner-element')) {
          var height = ($button.outerHeight() - 2) + 'px';
          var width = $button.outerWidth() + 'px';
          var $progress = $('<div>').addClass('progress progress-striped active').css({
            cursor: 'pointer',
            display: $button.css('display'),
            float: $button.css('float'),
            marginBottom: 0,
            border: '1px solid #666',
            height: height,
            width: width
          });
          var $bar = $('<div>').addClass('bar').css({
            height: height,
            width: width,
            lineHeight: height,
            fontSize: '13px',
            fontWeight: 'bold'
          }).html($button.data('spinner'));

          $bar.appendTo($progress);
          $progress.insertAfter($button).hide();
          $button.data('spinner-element', $progress);
        }

        $button.data('spinner-element').show();
        $button.hide();
      });

      $button.data('spinner-reset', function() {
        $button.data('spinner-element').hide();
        $button.show();
      });

      if ($button.parents('form').length) {
        $button.parents('form').submit($button.data('spinner-show'));
      }
      else {
        $button.click($button.data('spinner-show'));
      }
    });
  })();

  // Keypad should act like a keypad.
  /*(function() {
    return;
    var $keypad = $('#keypad');
    var $password = $('input#password');
    var $digitInputs = $keypad.find('input.digit');
    var passwordCharacter = $("<div>").html("&middot;").text();

    var updatePassword = function() {
      var password = $password.val();
      for (var i = 0; i < 4; i++) {
        if (i < password.length) {
          $($digitInputs.get(i)).val(passwordCharacter);
        } else {
          $($digitInputs.get(i)).val('');
        }
      }

      if(password.length == 4) {
        $keypad.parents('form').submit();
      }
    };

    $keypad.find('.button').hammer().on('tap', function() {
      var currentPin = $password.val();

      if ($(this).is('#delete')) {
        $password.val(currentPin.substr(0, currentPin.length-1));
      } else if (currentPin.length < 4) {
        var digit = $.trim($(this).text());
        $password.val($password.val() + digit);
      }

      return updatePassword();
    });
  })();*/

  // Auto generated function from http://toolki.com/en/google-maps,
  // for roadmap on contact page.
  (function() {
    // If we don't have the "google" variable, don't run this method.
    if (typeof google === 'undefined') return;

    var myLatlng = new google.maps.LatLng(18.007450,-76.786680);
    var myOptions = {
        zoom: 13,
        center: myLatlng,
        mapTypeId: google.maps.MapTypeId.ROADMAP}

    var map = new google.maps.Map(document.getElementById("map-canvas"), myOptions);

    var contentString = "";

    var infowindow = new google.maps.InfoWindow({
        content: contentString
    });

    var marker = new google.maps.Marker({
        position: myLatlng,
        map: map,
        title: ""
    });
    google.maps.event.addListener(marker, 'click', function() {
        infowindow.open(map,marker);
    });
  })();


  // Use data-modal to show the nearest modal matching the selector.
  (function() {
    $('[data-modal]').removeAttr('href').click(function() {
      var selector = '.modal.' + $(this).data('modal');
      var $modal = $(this).closest(':has(' + selector + ')').find(selector);
      $modal.modal();
    });
  })();

  // Use collapse to show the nearest accordian matching the selector.
  (function() {
    $('a.accordion-toggle').removeAttr('href').click(function() {
      var selector = '.collapse'
      var $collapse = $(this).closest(':has(' + selector + ')').find(selector);
      $collapse.collapse('toggle');
    });
  })();

  // Use data-offset to change scrolling speed of parallax section.
  (function() {
    $(window).scroll(function () {
      var browsers = ['Android', 'webos', 'iPhone', 'iPad', 'iPod',
                      'BlackBerry', 'IEMobile', 'Opera Mini'];
      var browserReg = new RegExp(browsers.join('|'), 'i');
      if (!browserReg.test(navigator.userAgent)) {
        var top = $(window).scrollTop();
        $('.parallax').each(function() {
          var offset = $(this).data('offset');
          $(this).css({'background-position':'center '+(offset+(top*.5))+'px'});
        });
      } else {
        $('.parallax').each(function() {
          $(this).css({'background-size':'cover'});
        });
      }
    });
  })();

  // .dropdown-timepicker's should act like timepicker objects.
  (function() {
    $('.dropdown-timepicker').timepicker({
      minuteStep: 30,
      disableFocus: false
    });
  })();

  // .datepicker's should act like datepicker objects.
  (function() {
    $('.datepicker').datepicker({
      autoclose: true
    });
  })();

  // .nav-tabs should act as tabs.
  (function() {
    $('.nav-tabs a').click(function(e) {
      e.preventDefault();
      $(this).tab('show');
    });
  })();

  // Use rel=tooltip to designate that we want a tooltip.
  (function() {
    $(document).tooltip({
      selector: '[rel=tooltip]'
    });
  })();

  // #notification-bar should fade away after 10 seconds.
  (function() {
    setTimeout(function() {
      $('#notification-bar').fadeOut('slow');
    }, 10000);
  })();

  // .nav-tabs should automatically select the first tab if we provide
  // data-select-first in the definition.
  (function() {
    $('.nav-tabs[data-select-first] li:first a:first').click();
  })();

  (function() {
    $('a.tip').click(function() {
      var amount = $(this).parents('form').find('#amount').val();
      var percent = $(this).data('percent');
      var tip = amount * percent;
      $(this).parents('form').find('#tip_amount').val(tip.toFixed(2));
    });
  })();

  // Automatically update transaction page using AJAX polling.
  (function() {
    // Only run this method on the transaction receipt page if the transaction
    // is not in a completed state.
    var $table = $('table#transaction-table');
    if ($table.length === 0 ||
        $table.find('tr').is('.completed, .refunded, .cancelled')) {
      return;
    }

    var uuid = $table.data('uuid');
    (function poll() {
      $.ajax({
        url: '/transactions/refresh?uuid=' + uuid,
        type: 'GET',
        dataType: 'json',
        error: function(response) {
          // TODO: Make an error message display in the notification bar.
        },
        success: function (response) {
          // If the transaction is not processed, poll again in 5 seconds.
          var transaction_status = response.transaction_status;
          if (transaction_status !== 'completed' &&
              transaction_status !== 'refunded' &&
              transaction_status !== 'cancelled'
          ) {
            setTimeout(poll, 5000);
          }

          // Otherwise, the transaction has been processed;
          // stop polling and update the page.
          else {
            location.reload();
          }
        }
      });
    })();

  })();

});
