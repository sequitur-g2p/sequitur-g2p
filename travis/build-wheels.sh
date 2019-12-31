#!/bin/bash                                                                        
# Copyright (c) 2019, Johns Hopkins University ( Yenda Trmal <jtrmal@gmail.com> )
# License: Apache 2.0

# Begin configuration section.  
# End configuration section
set -e -o pipefail 
set -o nounset                              # Treat unset variables as an error
set -x

#yum install -y curl
#yum install -y wget

#wget https://downloads.sourceforge.net/swig/swig-4.0.1.tar.gz
#tar xzf swig-4.0.1.tar.gz

(cd /io/swig-4.0.1; ./configure --without-pcre && make && make install) || exit 1

# Compile wheels
for PYBIN in /opt/python/*/bin; do
  (cd /io; make clean)
    "${PYBIN}/pip" install -r /io/dev-requirements.txt
    "${PYBIN}/pip" wheel /io/ -w wheelhouse/
done

# Bundle external shared libraries into the wheels
for whl in wheelhouse/sequitur*.whl; do
    auditwheel repair "$whl" --plat $PLAT -w /io/wheelhouse/
done

# Install packages and test
#for PYBIN in /opt/python/*/bin/; do
#    "${PYBIN}/pip" install python-manylinux-demo --no-index -f /io/wheelhouse
#    (cd "$HOME"; "${PYBIN}/nosetests" pymanylinuxdemo)
#done

