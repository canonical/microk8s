#!/bin/bash

INSTALL="${1}"

[ ! -f ./configure ] && [ -f ./autogen.sh ] && env NOCONFIGURE=1 ./autogen.sh
[ ! -f ./configure ] && [ -f ./bootstrap ] && env NOCONFIGURE=1 ./bootstrap
[ ! -f ./configure ] && autoreconf --install

./configure

mkdir -p build

make install DESTDIR="${PWD}/build"

mkdir -p "${INSTALL}/lib" "${INSTALL}/usr/include"

cp -r "build/usr/local/lib/libraft"*"so"* "${INSTALL}/lib/"
cp -r "build/usr/local/include/"* "${INSTALL}/usr/include/"
