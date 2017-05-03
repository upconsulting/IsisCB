$('.action-value-container').css('display', 'none');

// User selects an action.
$('select#id_action').change(function(e) {
    // Hide all action inputs.
    $('.action-value-container').css('display', 'none');

    // Clear the confirm list.
    $('#confirm-action-list').empty();

    var updateField = function(field) {
        var field_name = field.attr('id').replace('id_', '');
        var field_extra = window[field_name.toLowerCase() + '_extra'];
        var field_label = window[field_name.toLowerCase() + '_label'];

        var value = field.val();
        var value_display;
        if (field_label) {
            value_display = field_label(value);
        } else {
            value_display = value;
        }

        $('#confirm-action-value-' + field_name).empty();
        $('#confirm-action-value-' + field_name).append(value_display);
        if (field_extra) {
            $('#confirm-extra-' + field_name).empty();
            $('#confirm-extra-' + field_name).append(field_extra(value));
        }
    }

    // If the action widget is a multiselect, there may be several selected
    //  actions.
    var selected = $('select#id_action').val();
    var show = function(field_name) {    // Display the selected inputs.
        $('#container_' + field_name).css('display', 'block');
        $('[id^=container_' + field_name + ']').css('display', 'block');
        var field = $('#id_' + field_name);
        $('[id^=container_' + field_name + '] .action-value').addClass('form-control');

        field.addClass('form-control');

        var elem = '<li class="list-group-item">' + field_name + ': <span class="text-warning" id="confirm-action-value-' + field_name + '"></span><div id="confirm-extra-'+ field_name+'" class="field-extra"></li>';
        $('#confirm-action-list').append(elem);
        updateField(field);
    }
    selected.forEach(show);

    // Update the confirm modal with action values.
    $('.action-value').change(function(e) {
        updateField($(e.target));
    });
});
