$(document).ready(function () {

	$("table").addClass("table table-striped table-sm")

	$("a.reference[name^=REF_]").each(function() {
		$(this).attr({
			'target': 'blank',
			'href': 'https://scholar.google.com/scholar?q=' + $(this).text()
		})
	})
});