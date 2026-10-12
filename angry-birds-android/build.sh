#!/usr/bin/env bash
# Builds AngryBirds.apk with the plain Android SDK tools (no Gradle needed).
# Requires: JDK 17+, ANDROID_HOME with platforms;android-34 and build-tools;34.0.0.
set -euo pipefail
cd "$(dirname "$0")"

SDK="${ANDROID_HOME:-${ANDROID_SDK_ROOT:-/opt/android/sdk}}"
BT="$SDK/build-tools/34.0.0"
JAR="$SDK/platforms/android-34/android.jar"
SRC=app/src/main
OUT=build
rm -rf "$OUT" && mkdir -p "$OUT/res" "$OUT/classes" "$OUT/dex"

# Signing key: keep the same keystore so new builds install as updates.
KS=keystore/release.keystore
if [ ! -f "$KS" ]; then
  mkdir -p keystore
  keytool -genkeypair -keystore "$KS" -storepass angrybirds -keypass angrybirds -alias angrybirds \
    -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Angry Birds, O=Bondhop" >/dev/null
fi

"$BT/aapt2" compile --dir "$SRC/res" -o "$OUT/res/res.zip"
"$BT/aapt2" link -o "$OUT/unsigned.apk" -I "$JAR" --manifest "$SRC/AndroidManifest.xml" \
  -A "$SRC/assets" "$OUT/res/res.zip" --java "$OUT/gen"

javac --release 8 -nowarn -Xlint:-options -classpath "$JAR" -d "$OUT/classes" \
  $(find "$SRC/java" "$OUT/gen" -name '*.java')
(cd "$OUT/classes" && jar cf ../classes.jar .)
"$BT/d8" --release --min-api 24 --lib "$JAR" --output "$OUT/dex" "$OUT/classes.jar"

cp "$OUT/unsigned.apk" "$OUT/with-dex.apk"
(cd "$OUT/dex" && zip -q ../with-dex.apk classes.dex)
"$BT/zipalign" -f -p 4 "$OUT/with-dex.apk" "$OUT/aligned.apk"
"$BT/apksigner" sign --ks "$KS" --ks-pass pass:angrybirds --key-pass pass:angrybirds \
  --out "$OUT/AngryBirds.apk" "$OUT/aligned.apk"
"$BT/apksigner" verify "$OUT/AngryBirds.apk"
echo "Built $(pwd)/$OUT/AngryBirds.apk ($(du -h "$OUT/AngryBirds.apk" | cut -f1))"
