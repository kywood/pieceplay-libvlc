이 빌드는 PiecePlay 앱의 LGPL 준수용이다. (This build exists for the PiecePlay app's LGPL compliance.)

# pieceplay-libvlc

GPL 구성요소를 뺀 LibVLC for Android 빌드와 그 소스다. PiecePlay 앱이 쓰는 `libvlc.so`를
누구나 같은 소스와 스크립트로 다시 만들 수 있게 하려고 공개한다.

## 원본 출처

| 구성요소 | 출처 | 기준 |
|---|---|---|
| libvlcjni (Java/JNI 바인딩, 빌드 스크립트) | https://code.videolan.org/videolan/libvlcjni | 브랜치 `libvlcjni-3.x`, 커밋 `81bb02b` ("Bump vlc 3 version", Maven `org.videolan.android:libvlc-all:3.7.5`에 해당) |
| VLC | https://code.videolan.org/videolan/vlc | 브랜치 `3.0.x`, 커밋 `ac6c2a405d652b5576128ceb9fec2c342f0e83ec` |
| VLC 패치 | 이 저장소 `libvlc/patches/0001`~`0020` | libvlcjni 원본 그대로. `buildsystem/get-vlc.sh`가 `git am`으로 적용한다 |
| contrib(외부 라이브러리) | VLC `contrib/src/*` 규칙이 받는 각 프로젝트의 원본 tarball | `make fetch`가 받는다. 체크섬은 VLC `contrib/src/*/SHA512SUMS` |

이 저장소의 `main`은 libvlcjni 원본 이력 위에 아래 패치 커밋만 더한 것이다(`git log 81bb02b..main`).
원본 libvlcjni README는 [README.libvlcjni.md](README.libvlcjni.md)에 그대로 두었다.

## 라이선스

- libvlcjni: LGPL-2.1 ([LICENSE](LICENSE), [libvlc/COPYING.LIB](libvlc/COPYING.LIB)).
- VLC(libvlc, libvlccore, 이 빌드에 남는 모듈): LGPL-2.1-or-later.
- contrib: 각 프로젝트 라이선스(LGPL-2.1, BSD, MIT, ISC, zlib, FreeType License 등). `--license a`이므로
  VLC contrib 규칙상 GPL 또는 (L)GPLv3가 필요한 패키지는 빌드되지 않는다.
- 이 저장소에서 더한 변경도 LGPL-2.1로 배포한다.

## 원본과 다른 점(패치)

| 커밋 | 내용 |
|---|---|
| `compile-libvlc: do not force build realrtsp` | GPL인 Real RTSP 접근 모듈을 강제로 켜던 `--enable-realrtsp` 제거(상위 `ddde54f`와 같은 수정) |
| `Disable Lua and stop shipping the Lua scripts` | contrib·configure에 `--disable-lua`, Gradle의 Lua 스크립트 복사 작업 제거(AAR에 `assets/lua`가 들어가지 않음) |
| `compile-libvlc: explicitly disable GPL modules for LGPL licenses` | `--license l` 또는 `a`일 때 x264·x26410b·x265·postproc·dvdnav·dvdread·a52·faad·mad·realrtsp·lua를 configure에서 명시적으로 끔. `a`는 gnutls·live555도 끔 |
| `compile-libvlc: blacklist GPL VLC modules` | GPL 소스(또는 GPL 헤더 포함) 모듈을 정적 모듈 목록에서 제외: dummy(control), access_realrtsp, lua, dolby_surround_decoder, headphone_channel_mixer, mono, rotate, deinterlace, hqdn3d, file_logger, syslog, stream_out_rtp, stream_out_cycle, vod_rtsp, audioscrobbler, x264·x265·postproc·dvdnav·dvdread |
| `compile-libvlc: add a GPL scan gate for LGPL builds` | GPL contrib 라이브러리가 남았거나, 링크 전 `lib*_plugin.a` 또는 링크된 `.so`에 GPL 흔적이 있거나, 64비트 `.so`의 LOAD 정렬이 16 KB 미만이면 빌드를 실패시킴(`buildsystem/libvlc_gpl_scan.py`) |
| `Add PiecePlay README and Docker build script` | 이 문서, `buildsystem/pieceplay-docker-build.sh` |

빠지는 기능: Lua 플레이리스트 파서(유튜브 등), TLS(https)·RTSP 스트리밍, DVD, 일부 오디오·비디오 필터
(회전, 디인터레이스, 노이즈 제거, 채널 다운믹스 필터), RTP 송출. PiecePlay는 `http://127.0.0.1` 스트림과
파일만 VLC에 넘기므로 재생 경로에는 영향이 없는 것으로 본다.

## 빌드 방법

Linux(또는 WSL2)와 Docker가 필요하다. 도구와 NDK는 VideoLAN 공식 빌드 이미지 안에 있다.

```sh
git clone https://github.com/kywood/pieceplay-libvlc.git
cd pieceplay-libvlc
# 64비트: registry.videolan.org/vlc-debian-android:20260611225331 (NDK r29)
# 32비트: registry.videolan.org/vlc-debian-android-3.0:20260701183656 (NDK r21)
./buildsystem/pieceplay-docker-build.sh arm64      # arm | x86_64 | x86
```

- 스크립트는 `buildsystem/get-vlc.sh`(VLC clone + 패치 20개)와
  `buildsystem/compile-libvlc.sh -a <abi> --release --license a`를 컨테이너 안에서 실행한다.
- 결과: `libvlc/jni/libs/<abi>/libvlc.so`, `libc++_shared.so`.
- contrib를 소스부터 빌드하므로(공식 prebuilt contrib는 GPL 구성이라 쓰지 않는다) ABI마다 수 시간이 걸린다.

## 검사

```sh
python3 -I buildsystem/libvlc_gpl_scan.py libvlc/jni/libs/arm64-v8a
```

GPL 구성요소 흔적이 하나라도 있거나 64비트 `.so`의 LOAD 정렬이 16 KB보다 작으면 종료 코드 1로 끝난다.
빌드 중에도 같은 검사가 contrib 설치 디렉터리, 정적 모듈 목록, 링크된 `.so`에 대해 자동으로 돈다.
