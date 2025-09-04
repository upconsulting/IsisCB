var settrackingstatus_extra = function(value) {
    var to_transition = settrackingstatus_data.allowable_states[value];
    var labels = settrackingstatus_data.transition_labels

    return Object.keys(settrackingstatus_data.transition_counts).map(function(state) {
        var count = settrackingstatus_data.transition_counts[state];
        if (count == 0) {
            return '';
        }
        var elem = '<div class="bulk-action-detail">';
        elem += '<span class="text-success">' + String(count) + ' <strong>' + labels[state] + '</strong> records will be transitioned to <strong>' + labels[value] + '</strong></span>';
        elem += '</div>';
        return elem;
    }).join('');
}

var settrackingstatus_label = function(value) {
    return settrackingstatus_data.transition_labels[value];
}
