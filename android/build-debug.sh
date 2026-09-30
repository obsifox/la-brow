#!/usr/bin/env bash
set -euo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT/android"

failures=0

java_version="$(java -version 2>&1 | head -1 || true)"
if ! command -v java >/dev/null 2>&1; then
  echo "missing: java"
  failures=$((failures + 1))
fi

if command -v java >/dev/null 2>&1; then
  major="$(java -version 2>&1 | sed -n 's/.*version "\([0-9]*\).*/\1/p' | head -1)"
  if [ -z "$major" ] || [ "$major" -lt 17 ]; then
    echo "java 17 or newer is required, found: ${java_version}"
    failures=$((failures + 1))
  fi
fi

if [ -z "${ANDROID_HOME:-}" ] && [ -z "${ANDROID_SDK_ROOT:-}" ]; then
  echo "missing: ANDROID_HOME or ANDROID_SDK_ROOT pointing at the Android SDK"
  failures=$((failures + 1))
fi

if [ -x "./gradlew" ]; then
  GRADLE="./gradlew"
elif command -v gradle >/dev/null 2>&1; then
  GRADLE="gradle"
else
  echo "missing: gradle or a gradle wrapper in android/"
  failures=$((failures + 1))
  GRADLE=""
fi

echo "toolchain summary"
echo "  java     : ${java_version:-absent}"
echo "  android  : ${ANDROID_HOME:-${ANDROID_SDK_ROOT:-absent}}"
echo "  gradle   : ${GRADLE:-absent}"
echo "  product  : com.labrow.browser"

if [ "$failures" -ne 0 ]; then
  echo ""
  echo "build host is not ready, ${failures} requirement(s) missing"
  exit 1
fi

echo ""
echo "running a debug assembly"
"$GRADLE" --no-daemon assembleDebug
echo ""
echo "artifacts"
find app/build/outputs -name "*.apk" -type f
