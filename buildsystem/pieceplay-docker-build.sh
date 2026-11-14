#!/bin/sh
# Build the PiecePlay LGPL LibVLC for one ABI inside the official VideoLAN
# Android build image (same images as buildsystem/gitlab/.gitlab-ci.yml).
#
# usage: buildsystem/pieceplay-docker-build.sh <arm64|arm|x86_64|x86> [license]
#
# license defaults to "a" (LGPLv2.1 + ad-clauses). The checkout is mounted at
# /work; VLC is cloned into ./vlc by get-vlc.sh and the shared libraries end
# up in libvlc/jni/libs/<abi>/.
set -e

ABI=${1:?usage: $0 <arm64|arm|x86_64|x86> [license]}
LICENSE=${2:-a}
SRC_DIR="$(cd "$(dirname "$0")/.."; pwd -P)"

IMAGE_64=registry.videolan.org/vlc-debian-android:20260611225331
IMAGE_32=registry.videolan.org/vlc-debian-android-3.0:20260701183656
case $ABI in
    arm64|arm64-v8a|x86_64) IMAGE=$IMAGE_64 ;;
    arm|armeabi-v7a|x86)    IMAGE=$IMAGE_32 ;;
    *) echo "unknown ABI: $ABI"; exit 1 ;;
esac

# Reproducibility: get-vlc.sh applies the VLC patches with `git am`, which
# stamps each commit with the current time, and VLC's configure records the
# build host name (VLC_COMPILE_HOST). Pin both so the same sources always give
# the same VLC hash and byte-identical shared libraries. The date is the commit
# time of the VLC base (3.0.x ac6c2a40, 2026-07-04T16:12:55Z), so commits in
# this repository that do not touch the build inputs do not change it.
SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-1783181575}

echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ) abi=$ABI license=$LICENSE image=$IMAGE source_date_epoch=$SOURCE_DATE_EPOCH"
docker run --rm \
    --user "$(id -u):$(id -g)" \
    --hostname pieceplay-build \
    -e HOME=/tmp \
    -e SOURCE_DATE_EPOCH="$SOURCE_DATE_EPOCH" \
    -e GIT_COMMITTER_DATE="@$SOURCE_DATE_EPOCH +0000" \
    -e GIT_AUTHOR_NAME="PiecePlay LibVLC build" \
    -e GIT_AUTHOR_EMAIL="build@localhost" \
    -e GIT_COMMITTER_NAME="PiecePlay LibVLC build" \
    -e GIT_COMMITTER_EMAIL="build@localhost" \
    -e GIT_CONFIG_COUNT=1 \
    -e GIT_CONFIG_KEY_0=safe.directory \
    -e GIT_CONFIG_VALUE_0='*' \
    -v "$SRC_DIR":/work -w /work \
    "$IMAGE" \
    sh -c "./buildsystem/get-vlc.sh && ./buildsystem/compile-libvlc.sh -a $ABI --release --license $LICENSE"
echo "end: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
