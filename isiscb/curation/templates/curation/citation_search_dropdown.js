var TITLE_LENGTH = 50;
var AUTHOR_LENGTH = 40;
var JOURNAL_LENGTH = 15;

results_container.empty();
result.results.forEach(function(r) {
    var choice_elem = '<li class="list-group-item search-result';
    if (r.public != true) {
      choice_elem += ' record-notpublic';
    }
    choice_elem += '">';
    choice_elem += '<span class="button-group button-group-xs">';
    choice_elem += '<a class="glyphicon glyphicon-ok btn btn-xs select-citation" data-id="' + r.id + '" data-name="' + r.title + '" data-authors="' + r.authors + '" data-type="' + r.type + '" data-type_id="' + r.type_id + '"></a>';
    choice_elem += '<a href="'+ r.url + '" class="btn btn-xs glyphicon glyphicon-pencil" target="_blank"></a>';
    choice_elem += '</span>';
    title = r.title.slice(0,TITLE_LENGTH);
    if (r.title.length > TITLE_LENGTH) {
      title += "...";
    }
    authors = r.authors.slice(0, AUTHOR_LENGTH);
    if (r.authors.length > AUTHOR_LENGTH) {
      authors += "...";
    }
    choice_elem += ' <span class="label label-success">' + r.type + '</span> <i>' + title + '</i> by ' + authors ;

    if (r.journal != null && r.journal != "") {
      journal = r.journal.slice(0, JOURNAL_LENGTH);
      if (r.journal.length > JOURNAL_LENGTH) {
        journal += "...";
      }
      var in_string = " in ";
      if (r.type_id == 'AR') {
        in_string += 'journal ';
      } else if (r.type_id == 'BO') {
        in_string += 'book ';
      }
      choice_elem += in_string + ' <i>' + journal + '</i>';
    }

    if (r.book != null && r.book != "") {
      book = r.book.slice(0, JOURNAL_LENGTH);
      if (r.book.length > JOURNAL_LENGTH) {
        book += "...";
      }
      choice_elem += ' in book <i>' + book + '</i>';
    }

    choice_elem += ' <span class="label label-default">' + r.datestring + '</span>';

    if (r.public != true) {
      choice_elem += ' <i class="fa fa-eye-slash" title="The linked record is not public."></i>';
    }
    choice_elem += '</li>';

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
