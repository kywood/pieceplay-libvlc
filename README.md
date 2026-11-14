이 빌드는 PiecePlay 앱의 LGPL 준수용이다. (This build exists for the PiecePlay app's LGPL compliance.)

# pieceplay-libvlc

GPL 구성요소를 뺀 LibVLC for Android 빌드와 그 소스다. PiecePlay 앱이 쓰는 `libvlc.so`를
누구나 같은 소스와 스크립트로 다시 만들 수 있게 하려고 공개한다.

## 원본 출처

| 구성요소 | 출처 | 기준 |
|---|---|---|
| libvlcjni (Java/JNI 바인딩, 빌드 스크립트) | https://code.videolan.org/videolan/libvlcjni | 브랜치 `libvlcjni-3.x`, 커밋 `81bb02b` ("Bump vlc 3 version", Maven `org.videolan.android:libvlc-all:3.7.5`에 해당) |
| VLC | https://code.videolan.org/videolan/vlc | 브랜치 `3.0.x`, 커밋 `ac6c2a405d652b5576128ceb9fec2c342f0e83ec` |
| VLC 패치 | 이 저장소 `libvlc/patches/0001`~`0022` | `0001`~`0020`은 libvlcjni 원본 그대로, `0021`(재현 빌드)·`0022`(FFmpeg aarch64 GPL 파일 제외)는 이 저장소에서 더한 것. `buildsystem/get-vlc.sh`가 `git am`으로 적용한다 |
| contrib(외부 라이브러리) | VLC `contrib/src/*` 규칙이 받는 각 프로젝트의 원본 tarball | `make fetch`가 받는다. 체크섬은 VLC `contrib/src/*/SHA512SUMS` |

이 저장소의 `main`은 libvlcjni 원본 이력 위에 아래 패치 커밋만 더한 것이다(`git log 81bb02b..main`).
원본 libvlcjni README는 [README.libvlcjni.md](README.libvlcjni.md)에 그대로 두었다.

## 라이선스

- libvlcjni: LGPL-2.1 ([LICENSE](LICENSE), [libvlc/COPYING.LIB](libvlc/COPYING.LIB)).
- VLC(libvlc, libvlccore, 이 빌드에 남는 모듈): LGPL-2.1-or-later.
- contrib: 각 프로젝트 라이선스(LGPL-2.1, BSD, MIT, ISC, zlib, FreeType License 등). `--license a`이면 VLC contrib
  규칙이 GPL 또는 (L)GPLv3로 표시한 패키지(x264, dvdnav, gnutls 등)는 빌드되지 않는다. **그러나 이 표시는 패키지
  단위라, GPL 조건 없이 들어가는 패키지 안에 GPL 파일이 섞인 경우는 막지 못한다.** 실제로 `3.7.5-lgpl.1`과
  `3.7.5-lgpl.2`에는 zvbi 0.2.44의 GPL-2 파일 `src/packet-830.c`가 링크되어 있었다(arm64는 FFmpeg의 GPL-2+
  aarch64 파일 3개도). `3.7.5-lgpl.3`부터 zvbi·librist를 끄고 FFmpeg 파일을 빼며(패치 0022), 링크된 소스 파일을
  하나씩 검사하는 `buildsystem/pieceplay-gpl-sources.py`로 빌드를 멈춘다.
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
| `Add a Docker script that packages the 4-ABI AAR` | `buildsystem/pieceplay-docker-aar.sh` |
| `pieceplay-docker-build: pin ...` | 재현 빌드를 위해 `git am` 커밋 시각과 컨테이너 호스트 이름 고정 |
| `Add a GitHub Actions workflow ...` | `.github/workflows/reproduce.yml`, `buildsystem/pieceplay-compare-aar.py` |
| `compile-libvlc: sort the static module list ...` | 정적 모듈 목록을 정렬해 링크 순서가 파일 시스템 순서에 따라 바뀌지 않게 함 |
| `pieceplay-docker-aar: clone VLC when missing ...` | VLC 체크아웃이 없으면 `get-vlc.sh`부터 실행(`assets/hrtfs`, `build_vlc_revision`) |
| `Add VLC patch 0021 ...` | `libvlc/patches/0021`: `vlc --version` 안내문의 `__DATE__`·`__TIME__` 제거(NDK r21 clang은 `SOURCE_DATE_EPOCH`를 따르지 않아 32비트 빌드가 매번 달라짐) |
| `Add VLC patch 0022 ...` | `libvlc/patches/0022`: FFmpeg contrib에 패치를 더해 `libavcodec/aarch64/ac3dsp_init_aarch64.c`, `ac3dsp_neon.S`, `libavutil/aarch64/crc.S`를 빌드하지 않는다. 세 파일은 GPL-2.0-or-later인데 FFmpeg는 `--enable-gpl` 없이도 빌드한다. arm64는 다른 ABI처럼 C 구현을 쓴다 |
| `compile-libvlc: disable zvbi and librist ...` | contrib와 configure에서 zvbi·librist를 끈다. zvbi 0.2.44는 `src/packet-830.c`·`src/pdc.c`가 GPL-2이고 LGPL인 `packet.c`가 그 함수를 부른다. librist는 Mbed TLS(Apache-2.0 OR GPL-2.0-or-later)를 묶어 넣고, RIST는 쓰지 않는다. 텔레텍스트는 LGPL `telx` 모듈이 맡는다 |
| `Add a link-time check for GPL-only source files ...` | `buildsystem/pieceplay-gpl-sources.py`: strip 전 `libvlc.so`의 DWARF에서 링크된 소스 파일을 모두 뽑아 헤더가 GPL 전용이면 빌드를 실패시킨다(이중 라이선스·Bison 예외는 따로 표시). `libvlc_gpl_scan.py`에 zvbi·librist 표식 추가 |

빠지는 기능: Lua 플레이리스트 파서(유튜브 등), TLS(https)·RTSP·RIST 스트리밍, DVD, zvbi(텔레텍스트는 `telx`가 대신함), 일부 오디오·비디오 필터
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
- 결과: `libvlc/jni/libs/<abi>/libvlc.so`, `libvlcjni.so`, `libc++_shared.so`.
- contrib를 소스부터 빌드한다(공식 prebuilt contrib는 GPL 구성이라 쓰지 않는다). 12코어 기준 ABI당 약 12~15분, 빌드 트리는 ABI당 약 6 GB다.
- 32비트와 64비트는 이미지가 다르다. 한 체크아웃에서 여러 ABI를 연달아 빌드하지 말고 **ABI마다 따로 clone한 폴더에서** 빌드한다(`vlc/extras/tools`를 다른 이미지에서 만든 것을 다시 쓰게 된다).

### AAR 만들기

4 ABI를 모두 빌드한 뒤, 한 체크아웃(예: arm64 폴더)의 `libvlc/jni/libs/`에 나머지 ABI 폴더를 복사하고 실행한다.

```sh
cp -r ../x86_64/libvlc/jni/libs/x86_64 ../arm/libvlc/jni/libs/armeabi-v7a ../x86/libvlc/jni/libs/x86 libvlc/jni/libs/
./buildsystem/pieceplay-docker-aar.sh
```

- 64비트 이미지 안에서 `GRADLE_ABI=all gradle :libvlc:assembleRelease`를 실행한다. 결과는 `libvlc/build/outputs/aar/libvlc-release.aar`다.
- 구조는 공식 `libvlc-all` AAR과 같다(`classes.jar`, `jni/<abi>/*.so`, `AndroidManifest.xml`, `res/`, `R.txt`, `assets/hrtfs/`). `assets/lua/`는 없다.
- 이미지의 SDK는 읽기 전용이고 `android-37.0`만 있어, 스크립트가 컨테이너 안에서 SDK를 쓰기 가능한 곳에 복사한 뒤 Gradle이 `android-36`을 받게 한다(네트워크 필요).
- 재현 빌드: `pieceplay-docker-build.sh`가 `git am`의 커밋 시각(`GIT_COMMITTER_DATE`, `SOURCE_DATE_EPOCH`)을 VLC 기준 커밋 시각(2026-07-04T16:12:55Z)으로, 컨테이너 호스트 이름을 `pieceplay-build`로 고정한다. 그래서 같은 소스면 VLC 커밋 해시와 `.so`가 바이트 단위로 같다(같은 커밋을 이 저장소 개발 PC의 WSL과 GitHub Actions에서 따로 빌드해 `.so`의 SHA-256을 대조한다). AAR은 `res/values/values.xml`의 `build_libvlc_revision`(이 저장소의 커밋)만 달라질 수 있다. 예외: armeabi-v7a `libvlc.so`는 `.note.gnu.build-id`(20바이트)만 달라질 수 있다. 링크할 때 strip 전 바이너리로 계산하는 값이라 배포되는 코드·데이터와는 관계없고, 비교 스크립트는 이 경우를 "build ID only"로 따로 표시한다.
- `3.7.5-lgpl.1`은 이 고정을 넣기 전에 빌드했다. 그래서 그 Release의 `libvlc.so`는 다시 빌드한 것과 바이트가 다르다(VLC 커밋 해시 문자열 차이). 구조·Java API·GPL 검사로 비교한다.

## 재현 빌드(GitHub Actions)

`.github/workflows/reproduce.yml`이 위와 같은 스크립트와 이미지(digest 고정)로 4 ABI를 따로 빌드하고 AAR로 묶은 뒤 검사한다.
`buildsystem/`·`libvlc/`·워크플로를 바꾸는 PR과 수동 실행(`workflow_dispatch`)에서 돈다.

1. ABI별 job: `pieceplay-docker-build.sh <abi>`(빌드 안 GPL 게이트 포함). `.so`, 빌드 로그, VLC HEAD, contrib tarball 목록과 SHA-256을 아티팩트로 올린다. arm64 job은 contrib 원본 tarball 묶음(`contrib-tarballs`)도 올린다.
2. package job: `pieceplay-docker-aar.sh`로 AAR을 만들고 `libvlc_gpl_scan.py`로 검사한 뒤, Release AAR(Release의 `SHA256SUMS`로 확인)과 `buildsystem/pieceplay-compare-aar.py`로 비교한다. 결과는 실행 요약(Summary)과 `aar` 아티팩트(AAR, `SHA256SUMS`, `compare.md`, `gpl-scan.txt`)에 남는다.

비교 기준: 파일 목록이 같고 `assets/lua/`가 없을 것, `.so`·`classes.jar`·`values.xml` 밖의 파일이 바이트 단위로 같을 것, `values.xml`은 리비전 문자열만 다를 것, `classes.jar`는 클래스마다 `javap -p` 출력이 같을 것. `.so`는 크기와 SHA-256을 표로 남기고, 수동 실행에서 `require_identical_native`를 켜면 바이트가 다를 때 실패한다.

로컬에서 같은 비교를 하려면:

```sh
python3 -I buildsystem/pieceplay-compare-aar.py <release.aar> <rebuilt.aar>
```

## 검사

```sh
python3 -I buildsystem/libvlc_gpl_scan.py libvlc/jni/libs/arm64-v8a
```

GPL 구성요소 흔적이 하나라도 있거나 64비트 `.so`의 LOAD 정렬이 16 KB보다 작으면 종료 코드 1로 끝난다.
빌드 중에도 같은 검사가 contrib 설치 디렉터리, 정적 모듈 목록, 링크된 `.so`에 대해 자동으로 돈다.
그 뒤 `buildsystem/pieceplay-gpl-sources.py`가 strip 전 `libvlc/jni/obj/local/<abi>/libvlc.so`에 링크된 소스 파일(DWARF 컴파일 단위, ABI마다 약 4,100개)의 헤더를 읽어 GPL 전용 파일이 하나라도 있으면 빌드를 실패시킨다. 디버그 정보 없이 빌드되는 contrib와 NDK 런타임은 이 검사에서 "디스크에 없음"으로 따로 센다.
