#!/bin/sh
# Build the GLPI plugin archive: dist/printlabel-<version>.zip
set -e
cd "$(dirname "$0")"
version=$(sed -n "s/.*PLUGIN_PRINTLABEL_VERSION', '\([^']*\)'.*/\1/p" printlabel/setup.php)
mkdir -p dist
rm -f "dist/printlabel-$version.zip"
zip -qr "dist/printlabel-$version.zip" printlabel
echo "dist/printlabel-$version.zip"
