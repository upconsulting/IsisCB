var widgets = {};
var attributeTypes = {};

var swapWidgets = function(event) {
    console.log(event);
    var inlineFormID = event.currentTarget.id.split('-')[4];   // e.g. 0
    var parentID = $('#'+event.currentTarget.id).parent().parent().parent().attr('id');

    var typeID = $('#'+event.currentTarget.id).val();
    var typeName = attributeTypes[typeID];

    var widget = $(widgets[typeName]).clone();

    var widgetParts = widget.attr('id').split('-');
    widgetParts[4] = inlineFormID;
    var widgetNewID = widgetParts.join('-');
    widget.attr('id', widgetNewID);
    widget.attr('name', widgetNewID.replace('id_', ''));
    widget.addClass('dynamicWidget');

    // Attempt to get the current value from the existing widget.
    var oldWidget = $('#'+parentID+' .dynamicWidget');
    var oldValue = oldWidget.attr('value'); // If ValueWidget
    console.log(oldValue);
    if (oldValue.length < 1) oldValue = oldWidget.val();
    if (oldValue.length > 0) widget.val(oldValue);

    oldWidget.replaceWith(widget);
}

var bindFields = function() {
    $('.attribute_type_controlled').change(swapWidgets);
    $('.attribute_type_controlled').bind('DOMNodeInserted', function(event) {
        updateTypes(function() {
            swapWidgets(event);
        });
    });
}

var updateTypes = function(callback) {
    $.get('/rest/attributetype/').done(function(data) {
        data.forEach(function(a) {
            attributeTypes[a.id] = a.value_content_type.model;
        });
        if (callback) callback();
    });
}

$('body').ready(function() {
    updateTypes(function() {
        // When the user selects an AttributeType, change the widget for the
        //  ``value`` form-field in the corresponding inline form.
        bindFields();

        $.each($('.attribute_type_controlled'), function(i, o) {
            if ($(o).val() > 0) {
                $(o).trigger('change');
            }
        });

        var tbody = $('.attribute_type_controlled').parent().parent().parent().parent();    // Yikes.
        tbody.bind('DOMNodeInserted', bindFields);

    });



});
