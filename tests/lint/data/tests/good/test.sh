#!/bin/sh -eux

tmp=$(mktemp)
tmt --help > $tmp
grep -C3 'Test Management Tool' $tmp
rm $tmp
