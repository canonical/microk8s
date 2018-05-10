#!/bin/sh
set -eu

mkdir -p meta/hooks

cat << 'EOF' > meta/hooks/install
#!/bin/bash
set -eu

cp -r ${SNAP}/default-args ${SNAP_DATA}/args

EOF

chmod +x meta/hooks/install
