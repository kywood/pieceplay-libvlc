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

echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ) abi=$ABI license=$LICENSE image=$IMAGE"
docker run --rm \
    --user "$(id -u):$(id -g)" \
    -e HOME=/tmp \
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
