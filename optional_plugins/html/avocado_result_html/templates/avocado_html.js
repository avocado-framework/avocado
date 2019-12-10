$(document).ready(function() {
  $('#results').dataTable({
    lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, 'All']],
    drawCallback: function() {
      $('[data-toggle="popover"]').each(function() {
        var isIconPopover = this.getElementsByClassName('icon').length;
        // only add a popover if the text has overflowed
        if (isIconPopover || (this.scrollWidth > $(this).innerWidth())) {
          $(this).popover();
        }
      })
    },
    initComplete: function() {
      var statusColumn = this.api().column(4);
      var select = $('<select class="form-control input-sm"><option value=""></option></select>')
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
});
