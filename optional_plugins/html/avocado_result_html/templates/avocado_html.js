$(document).ready(function() {
  $('#results').dataTable();

  $(function () {$('[data-toggle="popover"]').popover()})

  $('#results')
    .removeClass( 'display' )
    .addClass('table table-striped table-bordered');
} );
