$('.action-value-container').css('display', 'none');

// User selects an action.
$('select#id_action').change(function(e) {
    // Hide all action inputs.
    $('.action-value-container').css('display', 'none');

    // Clear the confirm list.
    $('#confirm-action-list').empty();

    // If the action widget is a multiselect, there may be several selected
    //  actions.
    var selected = $('select#id_action').val();
    var show = function(field_name) {    // Display the selected inputs.
        $('#container_' + field_name).css('display', 'block');
        $('[id^=container_' + field_name + ']').css('display', 'block');
        $('#confirm-action-list').append('<li class="list-group-item">' + field_name + ': <span class="text-warning" id="confirm-action-value-' + field_name + '"></span>');
        var field = $('#id_' + field_name);
        $('#confirm-action-value-' + field_name).append(field.val());
    }
    selected.forEach(show);

    $("[id^=jander]")

    // Update the confirm modal with action values.
    $('.action-value').change(function(e) {
        var field = $(e.target);
        var field_name = field.attr('id').replace('id_', '');
        $('#confirm-action-value-' + field_name).empty();
        $('#confirm-action-value-' + field_name).append(field.val());
    });
});
