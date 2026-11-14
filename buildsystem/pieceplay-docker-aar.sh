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
# Output: libvlc/build/outputs/aar/libvlc-release.aar
# When ./vlc is missing (a fresh checkout, as in the Actions package job),
# get-vlc.sh clones it first: the AAR takes assets/hrtfs/ from it and
# records its commit as build_vlc_revision.
set -e

SRC_DIR="$(cd "$(dirname "$0")/.."; pwd -P)"
IMAGE=registry.videolan.org/vlc-debian-android:20260611225331

for abi in arm64-v8a armeabi-v7a x86 x86_64; do
    for so in libvlc.so libvlcjni.so libc++_shared.so; do
        [ -f "$SRC_DIR/libvlc/jni/libs/$abi/$so" ] || { echo "missing libvlc/jni/libs/$abi/$so"; exit 1; }
    done
done
[ -d "$SRC_DIR/libvlc/assets/lua" ] && { echo "libvlc/assets/lua must not exist"; exit 1; }

# Same pinned date and identity as pieceplay-docker-build.sh, so a checkout
# made here gets the same VLC hash as the ABI builds.
SOURCE_DATE_EPOCH=${SOURCE_DATE_EPOCH:-1783181575}

echo "start: $(date -u +%Y-%m-%dT%H:%M:%SZ) image=$IMAGE"
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
    -e GRADLE_ABI=all \
    -e GIT_CONFIG_COUNT=1 \
    -e GIT_CONFIG_KEY_0=safe.directory \
    -e GIT_CONFIG_VALUE_0='*' \
    -v "$SRC_DIR":/work -w /work \
    "$IMAGE" \
    sh -c 'set -e
        # The VLC checkout provides assets/hrtfs and build_vlc_revision.
        [ -d vlc ] || ./buildsystem/get-vlc.sh
        mkdir -p /tmp/sdk
        for d in build-tools licenses platform-tools platforms; do cp -a /sdk/android-sdk-linux/$d /tmp/sdk/; done
        ln -s /sdk/android-sdk-linux/ndk /tmp/sdk/ndk
        export ANDROID_HOME=/tmp/sdk ANDROID_SDK_ROOT=/tmp/sdk
        export PATH=/opt/tools/gradle/bin:$PATH
        gradle --no-daemon :libvlc:assembleRelease'
echo "end: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
ls -l "$SRC_DIR"/libvlc/build/outputs/aar/
