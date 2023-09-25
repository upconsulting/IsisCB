class QuickSearch {

    constructor(url, tenantId, formField, useCustomCmp) {
      this.url = url;
      this.showInactive = "true";
      this.useCustomCmp = useCustomCmp;
      this.tenantId = tenantId;
      this.formField = formField;
      this.NON_PUBLIC_COLOR = "#e4d7ca";
    }

    search(query, searchTenant, maxResults, force, triggerSearch, link_text_formatter) {
        var url = this.url + "?show_inactive=" + this.showInactive 
        if (this.useCustomCmp) {
            url += "&use_custom_cmp=" + this.useCustomCmp; 
        }      
        url += "&max=" + maxResults + "&force=" + force; 
        if (searchTenant) {
            url += "&tenant_ids=" + this.tenantId;
        }
        url += "&q=" + query;
        var obj = this;
        $.ajax(url, {
            success: function(result) {
                var resultsContainer = $('#'+obj.formField + "_datalist");
                resultsContainer.empty();
                result.results.forEach(function(r) {

                    var newOption = $('<li class="list-group-item" data-record-id="' + r.id + '"></li>');
                    var linkText = link_text_formatter(r); 
                    var linkIcon = '';
                    var background_color = "#ffffff";
                    if (!r.public) {
                        linkIcon = '<i class="fas fa-eye-slash"></i> ';
                        newOption.css('background-color', obj.NON_PUBLIC_COLOR );
                        background_color = obj.NON_PUBLIC_COLOR ;
                    }

                    newOption.html('<a href="#">' + linkIcon + linkText + '</a>')
                    newOption.click(function() {
                        $("#id_" + obj.formField).val(r.id);
                        $("#"+obj.formField + "_search").val(linkText);
                        $('#'+obj.formField + "_search").css("background-color", background_color);
                        resultsContainer.empty();
                    })
                    resultsContainer.append(newOption);
                });

                if (result.results.length == 0 && ((force && query.length < 3) || (!force && query.length > 2))) {
                    var msg = $('<p>There are no results for "' + query +'".</p>');
                    resultsContainer.append(msg);
                } else if (result.results.length == 0 && !force && query.length < 3) {
                    var msg = $('<p>Your query was too short. </p>');
                    var forceLink = $('<a>Press <i class="fa fa-search" aria-hidden="true"></i></a>');
                    forceLink.click(function() {
                        triggerSearch(true, maxResults);
                    });
                    msg.append(forceLink);
                    msg.append(" to force the search.");
                    resultsContainer.append(msg);
                }

                if (result.results.length == maxResults) {
                    var load_more_li = $('<li class="list-group-item search-result"></li>');
                    var load_more_div = $('<div class="text-right" id="#' + obj.formField + '_load_more"><a>Load more...</a></div>');
                    load_more_li.append(load_more_div)
                    resultsContainer.append(load_more_li);
                    $(load_more_div).click(function() {
                        triggerSearch(force, maxResults+10);
                    });
                }
            }
        });
    }
}