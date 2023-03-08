#!/bin/bash

INSTALL="${1}"

[ ! -f ./configure ] && [ -f ./autogen.sh ] && env NOCONFIGURE=1 ./autogen.sh
[ ! -f ./configure ] && [ -f ./bootstrap ] && env NOCONFIGURE=1 ./bootstrap
[ ! -f ./configure ] && autoreconf --install

export CFLAGS="-DSQLITE_ENABLE_DBSTAT_VTAB=1 -DSQLITE_ENABLE_NORMALIZE=1"
export RAFT_CFLAGS="-I${SNAPCRAFT_STAGE}/usr/include"
export RAFT_LIBS="-L${SNAPCRAFT_STAGE}/lib -lraft"

wget https://sqlite.org/2020/sqlite-amalgamation-3330000.zip
unzip sqlite-amalgamation-3330000.zip
cp sqlite-amalgamation-3330000/sqlite3.{c,h} .

./configure --enable-debug --enable-build-sqlite

mkdir -p build

make -j"${SNAPCRAFT_PARALLEL_BUILD_COUNT}"
make install DESTDIR="${PWD}/build"

mkdir -p "${INSTALL}/lib" "${INSTALL}/usr/include"

cp -r "build/usr/local/lib/libdqlite"*"so"* "${INSTALL}/lib/"
cp -r "build/usr/local/include/"* "${INSTALL}/usr/include/"
