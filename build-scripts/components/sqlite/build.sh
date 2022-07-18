#!/bin/bash

INSTALL="${1}"

export CFLAGS="-DSQLITE_ENABLE_DBSTAT_VTAB=1"

[ ! -f ./configure ] && [ -f ./autogen.sh ] && env NOCONFIGURE=1 ./autogen.sh
[ ! -f ./configure ] && [ -f ./bootstrap ] && env NOCONFIGURE=1 ./bootstrap
[ ! -f ./configure ] && autoreconf --install

./configure

mkdir -p build

make install DESTDIR="${PWD}/build"

mkdir -p "${INSTALL}/bin" "${INSTALL}/lib" "${INSTALL}/usr/include"

cp "build/usr/local/bin/sqlite3" "${INSTALL}/bin/sqlite3"
cp -r "build/usr/local/lib/libsqlite3"*"so"* "${INSTALL}/lib/"
cp -r "build/usr/local/include/"* "${INSTALL}/usr/include/"
