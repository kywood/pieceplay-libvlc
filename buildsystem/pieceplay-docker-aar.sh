#!/bin/sh
# Package the PiecePlay LGPL LibVLC AAR inside the official VideoLAN Android
# build image, after the shared libraries of every wanted ABI are present in
# libvlc/jni/libs/<abi>/ (from buildsystem/pieceplay-docker-build.sh, one
# checkout per ABI, then copied into this checkout).
#
# usage: buildsystem/pieceplay-docker-aar.sh
#
# The image's SDK is read-only and only has android-37.0, while the project
# compiles against 36 (settings.gradle). The SDK (without the NDK) is copied
# to a writable directory inside the container so Gradle can install the
# platform itself, as the upstream CI does when it runs as root.
# Output: libvlc/build/outputs/aar/libvlc-all-<version>.aar
set -e

SRC_DIR="$(cd "$(dirname "$0")/.."; pwd -P)"
IMAGE=registry.videolan.org/vlc-debian-android:20260611225331

for abi in arm64-v8a armeabi-v7a x86 x86_64; do
    for so in libvlc.so libvlcjni.so libc++_shared.so; do
        [ -f "$SRC_DIR/libvlc/jni/libs/$abi/$so" ] || { echo "missing libvlc/jni/libs/$abi/$so"; exit 1; }
    done
done
[ -d "$SRC_DIR/libvlc/assets/lua" ] && { echo "libvlc/assets/lua must not exist"; exit 1; }

echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ) image=$IMAGE"
docker run --rm \
    --user "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    -e GRADLE_ABI=all \
    -e GIT_CONFIG_COUNT=1 \
    -e GIT_CONFIG_KEY_0=safe.directory \
    -e GIT_CONFIG_VALUE_0='*' \
    -v "$SRC_DIR":/work -w /work \
    "$IMAGE" \
    sh -c 'set -e
        mkdir -p /tmp/sdk
        for d in build-tools licenses platform-tools platforms; do cp -a /sdk/android-sdk-linux/$d /tmp/sdk/; done
        ln -s /sdk/android-sdk-linux/ndk /tmp/sdk/ndk
        export ANDROID_HOME=/tmp/sdk ANDROID_SDK_ROOT=/tmp/sdk
        export PATH=/opt/tools/gradle/bin:$PATH
        gradle --no-daemon :libvlc:assembleRelease'
echo "end: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
ls -l "$SRC_DIR"/libvlc/build/outputs/aar/
