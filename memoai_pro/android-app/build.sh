#!/usr/bin/env bash
# Construit un APK signé sans Gradle, avec les outils du SDK Android déjà installés.
#
#   bash build.sh                                     → build/MemoAI.apk
#   bash build.sh ../android-encaissement Encaissement → build/Encaissement.apk (application du gérant)
#
# Prérequis : JDK 17+ (javac, keytool) et SDK Android (build-tools + une plateforme).
# La clé de signature est créée au premier lancement dans $KEYSTORE_DIR (hors du dépôt Git) :
# GARDEZ-LA PRÉCIEUSEMENT, elle est indispensable pour publier les mises à jour de l'application.
set -euo pipefail
cd "$(dirname "$0")/${1:-.}"
APK="build/${2:-MemoAI}.apk"

VERSION_CODE=$(sed -n 's/^code=//p' version.properties)
VERSION_NAME=$(sed -n 's/^name=//p' version.properties)
SDK="${ANDROID_HOME:-${LOCALAPPDATA:-$HOME/AppData/Local}/Android/Sdk}"
BT="$SDK/build-tools/$(ls "$SDK/build-tools" | sort -V | tail -1)"
PLATFORM="$SDK/platforms/$(ls "$SDK/platforms" | sort -V | tail -1)"
JAR="$PLATFORM/android.jar"
KEYSTORE_DIR="${KEYSTORE_DIR:-$HOME/MemoAI-signature-android}"
KEYSTORE="$KEYSTORE_DIR/memoai-release.jks"
PASSFILE="$KEYSTORE_DIR/mot-de-passe.txt"
PYTHON="${PYTHON:-../venv/Scripts/python.exe}"

echo "SDK : $BT | $PLATFORM"
# L'éditeur (VS Code) lit le SDK Android dans libs/ (voir .classpath) ; le fichier n'est pas versionné.
mkdir -p libs && cmp -s "$JAR" libs/android.jar || cp "$JAR" libs/android.jar
rm -rf build && mkdir -p build/compiled build/gen build/classes build/dex

# 1. Ressources (icônes, thème, textes) + manifeste
"$BT/aapt2.exe" compile --dir res -o build/compiled/res.zip
"$BT/aapt2.exe" link -I "$JAR" --manifest AndroidManifest.xml $([ -d assets ] && echo "-A assets") --java build/gen \
  --min-sdk-version 24 --target-sdk-version 36 \
  --version-code "$VERSION_CODE" --version-name "$VERSION_NAME" \
  -o build/base.apk build/compiled/res.zip

# 2. Code Java → classes → dex
javac -encoding UTF-8 --release 11 -nowarn -cp "$JAR" -d build/classes $(find src build/gen -name '*.java')
"$BT/d8.bat" --release --min-api 24 --lib "$JAR" --output build/dex $(find build/classes -name '*.class')
"$PYTHON" -c "import zipfile; z = zipfile.ZipFile('build/base.apk', 'a', zipfile.ZIP_DEFLATED); z.write('build/dex/classes.dex', 'classes.dex'); z.close()"

# 3. Clé de signature (créée une seule fois)
if [ ! -f "$KEYSTORE" ]; then
  mkdir -p "$KEYSTORE_DIR"
  "$PYTHON" -c "import secrets; print(secrets.token_urlsafe(24))" > "$PASSFILE"
  keytool -genkeypair -keystore "$KEYSTORE" -alias memoai -keyalg RSA -keysize 2048 -validity 10000 \
    -storepass "$(cat "$PASSFILE")" -keypass "$(cat "$PASSFILE")" -dname "CN=MemoAI, O=MemoAI Pro, C=ML" >/dev/null 2>&1
  echo "Clé de signature créée : $KEYSTORE (mot de passe dans $PASSFILE)"
fi

# 4. Alignement + signature (chemins au format Windows pour apksigner)
win() { cygpath -w "$1" 2>/dev/null || echo "$1"; }
"$BT/zipalign.exe" -p -f 4 build/base.apk build/aligned.apk
"$BT/apksigner.bat" sign --ks "$(win "$KEYSTORE")" --ks-key-alias memoai --ks-pass "file:$(win "$PASSFILE")" \
  --out "$APK" build/aligned.apk
"$BT/apksigner.bat" verify --print-certs "$APK" | head -3
echo "APK prêt : $(pwd)/$APK (version $VERSION_NAME, code $VERSION_CODE)"
