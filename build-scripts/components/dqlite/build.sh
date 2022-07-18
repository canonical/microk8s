#!/bin/bash

INSTALL="${1}"

[ ! -f ./configure ] && [ -f ./autogen.sh ] && env NOCONFIGURE=1 ./autogen.sh
[ ! -f ./configure ] && [ -f ./bootstrap ] && env NOCONFIGURE=1 ./bootstrap
[ ! -f ./configure ] && autoreconf --install

export SQLITE_CFLAGS="-I${INSTALL}/usr/include"
export SQLITE_LIBS="-L${INSTALL}/lib -lsqlite3"
export RAFT_CFLAGS="-I${INSTALL}/usr/include"
export RAFT_LIBS="-L${INSTALL}/lib -lraft"
./configure

mkdir -p build

make install DESTDIR="${PWD}/build"

mkdir -p "${INSTALL}/lib" "${INSTALL}/usr/include"

cp -r "build/usr/local/lib/libdqlite"*"so"* "${INSTALL}/lib/"
cp -r "build/usr/local/lib/pkgconfig/"*".pc" "${INSTALL}/lib/"
cp -r "build/usr/local/include/"* "${INSTALL}/usr/include/"
