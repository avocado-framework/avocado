$(document).ready(function() {
  $('#results').dataTable({
    "lengthMenu": [[10, 25, 50, 100, -1], [10, 25, 50, 100, "All"]],
    initComplete: function() {
      var statusColumn = this.api().column(4);
      var select = $('<select class="form-control"><option value=""></option></select>')
        .on('change', function () {
          var val = $(this).val()
          statusColumn.search(val ? '^' + val + '$' : '', true, false).draw();
        });

      $('#results_length').wrap('<div class="row"><div class="col-sm-4"></div></div>');
      $('#results_length').parent().parent()
        .append(
          $('<div class="col-sm-8"></div>')
          .append(
            $('<label class="font-weight-normal">Status </label>').append(select)
          )
        );

      // Add all possible status to the select
      statusColumn.data().unique().sort().each(
        function (element) {
          // Remove status text from its enclosing tag
          element = $(element).text();
          select.append('<option value="' + element + '">' + element + '</option>');
        }
      );
    }
  });

  $(function () {$('[data-toggle="popover"]').popover()})

  $('#results')
    .removeClass( 'display' )
    .addClass('table table-striped table-bordered');
} );

$(".hiddenText").hover(function(){
    var x = $(this).position();
    $(this).parent().next(".spnTooltip").css({'display': 'block', "top": x.top + 30, "left": x.left -50});
  }, function(){
    $(this).parent().next(".spnTooltip").css('display', 'none');
});
