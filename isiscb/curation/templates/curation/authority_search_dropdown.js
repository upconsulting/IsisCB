result.results.forEach(function(suggestion) {
    var choice_elem = `
        <li class="list-group-item search-result">
            <div class="row">
                <div class="col-xs-2">
                    <span class="button-group button-group-md">
                        <a class="glyphicon glyphicon-ok btn btn-md select-authority"
                            data-type="`+ suggestion.type +`"
                            data-type-code="` + suggestion.type_code + `"
                            data-id="` + suggestion.id + `"
                            data-name="` + suggestion.name + `"
                            data-suggestion="` + suggestion.id + `">
                        </a>
                    </span>
                </div>
                <div class="col-xs-10">
                    <div class="h5">
                        <a href="/curation/authority/` + suggestion.id + `/?tab=acrelations"
                            class="search-authority-anchor"
                            target="_blank"
                            data-toggle="tooltip"
                            data-html="true"
                            data-placement="left"
                            data-title="` + format_citations(suggestion.related_citations) + `">` + suggestion.name + ` (` + suggestion.citation_count + `)</a>
                    </div>
                    <span class="label label-danger"
                        style="margin-left: 5px;">
                        ` + suggestion.type_controlled + `
                    </span>
                </div>
            </div>
        </li>`;

    results_container.append(choice_elem);
});
if (result.results.length == max_results) {
  var load_more = `
    <li class="list-group-item search-result">
      <div class="text-right" id="load-more"><a>Load more...</a></div>
    </li>
  `;
  results_container.append(load_more);
  $('#load-more').click(function() {
      max_results += 10;
      triggerSearch();
  });
}
$('.search-authority-anchor[data-toggle="tooltip"]').tooltip({
    template: '<div class="tooltip related-citations-tooltip" role="tooltip"><div class="tooltip-arrow"></div><div class="tooltip-inner"></div></div>'
});

/*
$('.select-authority').click(function() {
    var selected = $(this);
    var selected_id = selected.attr('data-id');
    var selected_name = selected.attr('data-name');
    var selected_type = selected.attr('data-type');
    var selected_type_code = selected.attr('data-type-code');

    $('#results-container').empty();
    subject_search_input.val(selected_name);
    id_result_container.val(selected_id);
    $('#subject_type_full').text(selected_type);
    $('#subject_type_full').attr('data-type-code', selected_type_code);
    $('#subject_name').text(selected_name);

    subject_search_input.attr('disabled', true);
});


function format_citations(related_citations) {
    var _doc = '';
    related_citations.forEach(function(rel_cit) {
        _doc += "<div class='related-citation'>" + rel_cit + "</div>";
    })
    return _doc;
}
*/
