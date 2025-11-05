(function() {
  var datatableElement = $('#results');

  $(document).ready(function() {
    var resizeControl = new ResizeControl(datatableElement);
    datatableElement.dataTable({
      lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, 'All']],
      autoWidth: false,
      ordering: true,  // Explicitly enable sorting
      drawCallback: onTableRedrawn.bind(null, resizeControl),
      initComplete: onDatatablesInitialized,
      language: {
        lengthMenu: "Show _MENU_ entries"
      }
    });
  });

  function onDatatablesInitialized() {
    var statusColumn = this.api().column(4);
    var select = $('<select id="dt-status-0" class="form-control input-sm"><option value="">ALL</option></select>')
      .on('change', function () {
        statusColumn.search($(this).val().trim()).draw();
      });

    // Create a container for the controls
    var controlsContainer = $('<div class="dt-controls-container" style="display: flex; justify-content: space-between; width: 100%;"></div>');

    // Create a container for the entries section (left side)
    var entriesContainer = $('<div class="dt-entries-container" style="flex: 0 0 auto;"></div>');

    // Create a container for the status section (right side)
    var statusContainer = $('<div class="dt-status-container" style="flex: 0 0 auto; margin-left: auto; display: flex; align-items: center; padding-left: 30px;"></div>')
      .append(
        $('<label for="dt-status-0" style="margin-right: 0.5em; display: inline-block;">Status:</label>')
      )
      .append(select);

    // Get the parent element that contains the entries dropdown
    var parentElement = $('#dt-length-0').parent().parent();

    // Move the existing entries dropdown to the entries container
    entriesContainer.append($('#dt-length-0').parent());

    // Add both containers to the controls container
    controlsContainer.append(entriesContainer).append(statusContainer);

    // Replace the original parent content with our new container
    parentElement.empty().append(controlsContainer);

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
      table.find('th').each(function() {
        if ($(this).find('.resizer').length == 0) {
          // we only need one resizer per header cell
          $(this).append('<div class="resizer"></div>')
        }
        var resizerElement = $(this).find('.resizer');
        // the resizer must have the same size as the header cell to be detectable
        resizerElement.height(resizerElement.parent().outerHeight())
        // we detach and reattach each event to prevent them from being triggered
        // multiple times, as this function is called often
        resizerElement.off('click.resizer')
                      .on('click.resizer', onClick);

        // Don't attach click handler to the parent th element as it interferes with sorting
        // resizerElement.parent().off('click.resizer')
        //               .on('click.resizer', onClick);

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
        if ($(e.target).hasClass('resizer')) {
          e.stopImmediatePropagation();
          return false;
        }
      }
    }

    function onClick(e) {
      // prevent clicks on the resizer from triggering a datatables sort
      if ($(e.target).hasClass('resizer')) {
        e.stopImmediatePropagation();
        return false;
      }
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
      var newColumnWidth = this.resizeData.targetCellWidth + mouseOffset;

      // Ensure column width doesn't go below a minimum value (e.g., 50px)
      var minColumnWidth = 50;
      if (newColumnWidth < minColumnWidth) {
        newColumnWidth = minColumnWidth;
        // Recalculate mouseOffset based on the minimum column width
        mouseOffset = minColumnWidth - this.resizeData.targetCellWidth;
        newTableWidth = this.resizeData.tableWidth + mouseOffset;
      }

      if (newTableWidth <= this.originalTableWidth) {
        // If we're trying to make the table smaller than its original width,
        // keep the table at its minimum width but still allow column resizing
        table.width(this.originalTableWidth);
        // Apply the new column width even when the table is at minimum width
        this.resizeData.targetCell.width(newColumnWidth);
      } else {
        // Normal case: both table and column width can be increased
        table.width(newTableWidth);
        this.resizeData.targetCell.width(newColumnWidth);
      }
    };
  }
})();
