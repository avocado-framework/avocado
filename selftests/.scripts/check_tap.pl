#!/bin/env perl

use TAP::Parser;

my $parser = TAP::Parser->new( { exec => ['./scripts/avocado', 'run', 'passtest.py', 'errortest.py', 'warntest.py', '--tap', '-'] } );

while ( my $result = $parser->next ) {
        $result->is_unknown && die "Unknown line \\"" . $result->as_string . "\\" in the TAP output!\n";
}
$parser->parse_errors == 0 || die "Parser errors!\n";
$parser->is_good_plan || die "Plan is not a good plan!\n";
$parser->plan eq '1..3' || die "Plan does not match what was expected!\n";

