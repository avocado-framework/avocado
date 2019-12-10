(function() {
  var datatableElement = $('#results');

  $(document).ready(function() {
    var resizeControl = new ResizeControl(datatableElement);
    datatableElement.dataTable({
      lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, 'All']],
      autoWidth: false,
      drawCallback: onTableRedrawn.bind(null, resizeControl),
      initComplete: onDatatablesInitialized
    });
  });

  function onDatatablesInitialized() {
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

  function onTableRedrawn(resizeControl) {
    resizeControl.setupResizers();

    $('[data-toggle="popover"]').each(function() {
      $(this).popover();
      $(this).on('show.bs.popover', function (e) {
        if (this.tagName != 'TD') {
          // it's the whiteboard popover, always show it
          return;
        }

        var wrapperWidth = $(this).width();
        // need to use getBoundingClientRect() as the width is decimal
        var innerWidth = $(this).children().first()[0].getBoundingClientRect().width;
        // don't show popover it text hasn't overflowed
        if (innerWidth <= wrapperWidth) {
          e.preventDefault();
        }
      });
    })
  }

  function ResizeControl(table) {
    var tableBorderSize = table.outerWidth() - table.innerWidth();
    this.resizeData = {
      isResizing: false,
      mouseDownFired: false
    };
    // initialize table width
    onWindowResize.call(this);

    table.find('th').click(onHeaderCellClick.bind(this));
    // need to attach these to document as they can happen anywhere
    $(document).on('mouseup.resizer', onMouseUp.bind(this));
    $(document).on('mousemove.resizer', onMouseMove.bind(this));
    // as the window is resized, the minimum width of the table must be updated
    $(window).on('resize.resizer', onWindowResize.bind(this));

    // this should be called each table we have a redrawn
    this.setupResizers = function() {
      var self = this;
      table.find('.resizer').each(function() {
        var resizerElement = $(this);
        // the resizer must have the same size as the header cell to be detectable
        resizerElement.height(resizerElement.parent().outerHeight())
        // we detach and reattach each event to prevent them from being triggered
        // multiple times, as this function is called often
        resizerElement.off('click.resizer')
                      .on('click.resizer', onClick);
        resizerElement.parent().off('click.resizer')
                      .on('click.resizer', onClick);
        resizerElement.off('mousedown.resizer')
                      .on('mousedown.resizer', onMouseDown.bind(self));
      });
    };

    function onWindowResize() {
      // use the table parent's since it has a bootstrap responsive class
      this.originalTableWidth = table.parent().width() - tableBorderSize;

      // when increasing the window size after having resized table columns,
      // we need to adjust the table width for it to be responsive
      if (table.width() < this.originalTableWidth) {
        table.width(this.originalTableWidth);
      }
    }

    function onHeaderCellClick(e) {
      if (this.resizeData.mouseDownFired) {
        // when we resize and drop the cursor at the same header cell,
        // it will cause datatables to sort if we don't stop propagation
        e.stopImmediatePropagation();
        return false;
      }
    }

    function onClick(e) {
      // prevent clicks on the resizer from triggering a datatables sort
      e.stopImmediatePropagation();
      return false;
    }

    function onMouseDown(e) {
      this.resizeData = {
        isResizing: true,
        initialX: e.pageX,
        targetCell: $(e.target.parentNode),
        targetCellWidth: $(e.target.parentNode).width(),
        tableWidth: table.width()
      };
    };

    function onMouseUp(e) {
      if (!this.resizeData.isResizing) {
        return true;
      }

      this.resizeData.isResizing = false;
      var self = this;
      // HACK: the click event is fired *after* mouseup, so if we resize
      // and let go of the mouse on top of the same header cell, it will sort the table
      // We use a mouseDownFired flag, disabled after 300s, to signal our click handler
      // that a click after a resize should not be propagated
      self.resizeData.mouseDownFired = true;
      setTimeout(function() {
        self.resizeData.mouseDownFired = false;
      }, 300);
      e.stopImmediatePropagation();
      return false;
    }

    function onMouseMove(e) {
      if (!this.resizeData.isResizing) {
        return;
      }

      var mouseOffset = (e.pageX - this.resizeData.initialX);
      var newTableWidth = this.resizeData.tableWidth + mouseOffset;

      if (newTableWidth <= this.originalTableWidth) {
        // make sure we don't set a width too small
        table.width(this.originalTableWidth);
        return;
      }

      var newWidth = this.resizeData.targetCellWidth + mouseOffset;
      table.width(newTableWidth);
      this.resizeData.targetCell.width(newWidth);
    };
  }
})();
