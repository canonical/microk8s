#!/bin/bash

INSTALL="${1}"

[ ! -f ./configure ] && [ -f ./autogen.sh ] && env NOCONFIGURE=1 ./autogen.sh
[ ! -f ./configure ] && [ -f ./bootstrap ] && env NOCONFIGURE=1 ./bootstrap
[ ! -f ./configure ] && autoreconf --install

export CFLAGS="-DSQLITE_ENABLE_DBSTAT_VTAB=1" # for sqlite3.c
export RAFT_CFLAGS="-I${SNAPCRAFT_STAGE}/usr/include"
export RAFT_LIBS="-L${SNAPCRAFT_STAGE}/lib -lraft"

wget https://sqlite.org/2020/sqlite-amalgamation-3330000.zip
unzip sqlite-amalgamation-3330000.zip
cat >sqlite3.c <<EOF
#pragma GCC diagnostic ignored "-Wconversion"
#pragma GCC diagnostic ignored "-Wfloat-conversion"
#pragma GCC diagnostic ignored "-Wfloat-equal"
#pragma GCC diagnostic ignored "-Wimplicit-fallthrough"
#pragma GCC diagnostic ignored "-Wsign-conversion"
EOF
cat sqlite-amalgamation-3330000/sqlite3.c >>sqlite3.c
cp sqlite-amalgamation-3330000/sqlite3.h include/

./configure --enable-build-sqlite

mkdir -p build

make -j"${SNAPCRAFT_PARALLEL_BUILD_COUNT}"
make install DESTDIR="${PWD}/build"

mkdir -p "${INSTALL}/lib" "${INSTALL}/usr/include"

cp -r "build/usr/local/lib/libdqlite"*"so"* "${INSTALL}/lib/"
cp -r "build/usr/local/include/"* "${INSTALL}/usr/include/"
