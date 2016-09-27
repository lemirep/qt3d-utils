#!/bin/bash -e
#base capture
lcov -c --base-directory ~/work/qt3d --directory src/ -o coverage.info --no-external
#remove moc
lcov --directory src/ -o coverage.info -r coverage.info "/usr/*" "*.moc" "test/*"
#genrate report
rm -rf coverage
genhtml -o coverage -t Qt3D-Coverage --ignore-errors source coverage.info
