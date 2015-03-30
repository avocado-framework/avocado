#!/bin/sh -e
PATH=$(avocado "exec-path"):$PATH

avocado_debug "Debug message"
avocado_info "Info message"
avocado_warn "Warning message (should cause this test to finish with warning)"
avocado_error "Error message (ordinary message not changing the results)"
echo "Simple output without log-level specification"
exit 0  # no error reported
