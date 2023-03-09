#!/bin/bash

INSTALL="${1}"

[ ! -f ./configure ] && [ -f ./autogen.sh ] && env NOCONFIGURE=1 ./autogen.sh
[ ! -f ./configure ] && [ -f ./bootstrap ] && env NOCONFIGURE=1 ./bootstrap
[ ! -f ./configure ] && autoreconf --install

export SQLITE_CFLAGS="-I${SNAPCRAFT_STAGE}/usr/include"
export SQLITE_LIBS="-L${SNAPCRAFT_STAGE}/lib -lsqlite3"
export RAFT_CFLAGS="-I${SNAPCRAFT_STAGE}/usr/include"
export RAFT_LIBS="-L${SNAPCRAFT_STAGE}/lib -lraft"

./configure

mkdir -p build

make -j"${SNAPCRAFT_PARALLEL_BUILD_COUNT}"
make install DESTDIR="${PWD}/build"

mkdir -p "${INSTALL}/lib" "${INSTALL}/usr/include"

cp -r "build/usr/local/lib/libdqlite"*"so"* "${INSTALL}/lib/"
cp -r "build/usr/local/include/"* "${INSTALL}/usr/include/"
