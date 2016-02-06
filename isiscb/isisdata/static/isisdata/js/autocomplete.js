var bindAutocomplete = function(selector) {

    $(function() {
        function split( val ) {
            return val.split( /,\s*/ );
        }
        function extractLast( term ) {
            return split( term ).pop();
        }

        $(selector)
            // don't navigate away from the field on tab when selecting an item
            .bind( "keydown", function( event ) {
                if ( event.keyCode === $.ui.keyCode.TAB &&
                    $( this ).autocomplete( "instance" ).menu.active ) {
                        event.preventDefault();
                    }
                })
                .autocomplete({
                    source: function( request, response ) {
                        $.getJSON("/rest/authority/", {
                            name__contains: extractLast( request.term ),
                        }, response );
                    },
                    search: function() {
                        $('#' + this.id + '_container').find('.autocomplete-status').html('<span class="glyphicon glyphicon-hourglass"></span>');
                        // custom minLength
                        var term = extractLast( this.value );
                        if ( term.length < 3 ) {
                            return false;
                        }
                    },
                    focus: function() {
                        return false;
                    },
                    select: function( event, ui ) {
                        this.value = ui.item.name;
                        $('#' + this.id + '_container').find('.autocomplete-status').html('<span class="glyphicon glyphicon-ok"></span>');
                        var target = $(this).attr('datatarget');

                        var target_parts = this.id.split('-');
                        target_parts[target_parts.length - 1] = target;
                        console.log(target_parts.join('-'));
                        if (target) {
                            $('#' + target_parts.join('-')).val(ui.item.id);
                        }


                        return false;
                    }
                })
                .autocomplete( "instance" )._renderItem = function( ul, item ) {
                    ul.addClass('list-group');
                    console.log(item);
                    return $( "<a class='list-group-item'>" )
                        .append( "" + item.name + "<br><span class='text-muted'>" + item.description + "</span>" )
                        .appendTo( ul );
                };
            });
}

//
// $('body').ready(function() {
//     $('.autocomplete').each(function() {
//         bindAutocomplete('#' + this.id);
//     });
// })
