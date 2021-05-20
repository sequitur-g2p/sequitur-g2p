#!/bin/bash
# Copyright (c) 2019, Johns Hopkins University ( Yenda Trmal <jtrmal@gmail.com> )
# License: Apache 2.0

# Begin configuration section.
# End configuration section
set -e -o pipefail
set -o nounset                              # Treat unset variables as an error
set -x

cd /io/swig-4.0.1
./configure --without-pcre && make && make install

cd /io

# Compile wheels
for PYBIN in /opt/python/cp3*/bin; do
    $PYBIN/pip install --upgrade pip
    $PYBIN/pip install -r requirements.txt
    $PYBIN/pip install -r /io/dev-requirements.txt
    $PYBIN/pip install .
    PYTHON=$PYBIN/python make travis-test
    $PYBIN/python -m build --sdist --wheel --outdir dist/ .
done

# Bundle external shared libraries into the wheels
for whl in dist/sequitur*.whl; do
    auditwheel repair "$whl" --plat $PLAT -w /io/dist/
done

# Install packages and test
#for PYBIN in /opt/python/*/bin/; do
#    "${PYBIN}/pip" install python-manylinux-demo --no-index -f /io/wheelhouse
#    (cd "$HOME"; "${PYBIN}/nosetests" pymanylinuxdemo)
#done
