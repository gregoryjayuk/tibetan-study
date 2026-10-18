#!/bin/zsh
# Build the phone app (debug APK) and copy it to APK_DIR.
#   TIBETAN_TOOLING  a folder holding jdk/ and android-sdk/ (and the Gradle zip the wrapper points at); used, offline, when it exists
#   TIBETAN_APK_DIR  where the APK is copied
# Without the tooling folder, your own JAVA_HOME (JDK 17) and ANDROID_SDK_ROOT / ANDROID_HOME are used.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
TOOLING="${TIBETAN_TOOLING:-}"
APK_DIR="${TIBETAN_APK_DIR:-$HERE/dist}"
OFFLINE=()
if [[ -n "$TOOLING" && -d "$TOOLING" ]]; then
  export JAVA_HOME="$TOOLING/jdk/Contents/Home"
  export ANDROID_SDK_ROOT="$TOOLING/android-sdk"
  OFFLINE=(--offline)
fi
cp "$HERE/../app/web/index.html" "$HERE/app/src/main/assets/index.html"   # fallback if the folder copy is missing
cd "$HERE"
./gradlew $OFFLINE -q assembleDebug
V=$(grep -o 'versionCode = [0-9]*' app/build.gradle.kts | grep -o '[0-9]*$')
mkdir -p "$APK_DIR"
cp app/build/outputs/apk/debug/app-debug.apk "$APK_DIR/Tibetan-$V.apk"
echo "APK: $APK_DIR/Tibetan-$V.apk"
