
/*
This function creates a new ACRelation for the selected citation and authority.
*/
function addConceptToList(event, citation_id, acr_creation_url, authority_list_url, authority_url, tenant_id, can_update) {
  var link = event.target.closest('a');
  var authority_id = $(link).data('id');

  var payload = {
      'citation_id': citation_id,
      'authority_id': authority_id,
      'type_controlled': 'SU',    // subject.
      'type_broad_controlled': 'SC',    // subject content.
  };

  $.post(acr_creation_url, payload, function(result) {
    var newId = result.acrelation.id;
    var newType = result.acrelation.authority.type_controlled;
 
    var url = authority_list_url + result.acrelation.authority.id

    var ul = $('#subject-list-group');
    if (["TI", "GE"].includes(newType)) {
      ul = $('#time-place-subject-list-group');
    } else if (["PE", "IN"].includes(newType)) {
      ul = $('#person-institution-subject-list-group');
    }
    
    var linkText = result.acrelation.authority.name;
    if (result.acrelation.authority.owning_tenant != tenant_id) {
      linkText = '<i class="fas fa-share-alt"></i> ' + linkText;
      url = authority_url + result.acrelation.authority.id;
    }
    var li = $('<li id="subject-entry-' + newId + '" class="list-group-item"><a href="' + url + '">' + linkText + '</a></li>');
    ul.append(li);
    
    // if the user has permissions to update this citation, give them a delete button
    if (["True", "true"].includes(can_update.toLowerCase())) {
        var span = $('<span class="button-group button-group-xs"></span>');
        li.append(span);

        var a = $('<a class="btn btn-xs glyphicon glyphicon-remove delete delete-category pull-right" acrelation-id="' + newId + '" data-acrelation-type="subject" acrelation-title="' + result.acrelation.authority.name + '"></a>');
        span.append(a);
        a.click(delete_handler);
    }
  });
}