#!/bin/bash
# Copyright (c) 2019, Johns Hopkins University ( Yenda Trmal <jtrmal@gmail.com> )
# License: Apache 2.0

# Begin configuration section.
# End configuration section
set -e -o pipefail
set -o nounset                              # Treat unset variables as an error
set -x

yum -y install libffi-devel

cd /io/swig-4.2.1
./configure --without-pcre && make && make install

cd /io

# Compile all wheels
for PYBIN in /opt/python/cp3{9,10,11,12}*/bin; do
    echo $PYBIN
    tmp=$(basename $(dirname $PYBIN) )
    $PYBIN/python -m venv wheel-$tmp
    source wheel-$tmp/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    pip install -r /io/dev-requirements.txt
    pip install .
    PYTHON=python make travis-test
    python -m build --sdist --wheel --outdir dist/ .
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
