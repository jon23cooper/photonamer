#!/bin/bash
set -e

echo "=== Building PhotoNamer.app ==="

# Require Xcode Command Line Tools for clang
if ! command -v clang &>/dev/null; then
    echo "Error: Xcode Command Line Tools are required."
    echo "Install with:  xcode-select --install"
    exit 1
fi

APP="PhotoNamer.app"
CONTENTS="$APP/Contents"
MACOS="$CONTENTS/MacOS"
RESOURCES="$CONTENTS/Resources"

rm -rf "$APP"
mkdir -p "$MACOS" "$RESOURCES"

# Compile the launcher binary (no terminal window on launch)
echo "Compiling launcher..."
clang -O2 -o "$MACOS/PhotoNamer" launcher.c
echo "Done."

# Info.plist
cat > "$CONTENTS/Info.plist" << 'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleName</key>              <string>PhotoNamer</string>
  <key>CFBundleDisplayName</key>       <string>PhotoNamer</string>
  <key>CFBundleIdentifier</key>        <string>com.photonamer.app</string>
  <key>CFBundleVersion</key>           <string>1.0.0</string>
  <key>CFBundleShortVersionString</key><string>1.0.0</string>
  <key>CFBundleExecutable</key>        <string>PhotoNamer</string>
  <key>CFBundlePackageType</key>       <string>APPL</string>
  <key>NSHighResolutionCapable</key>          <true/>
  <key>NSRequiresAquaSystemAppearance</key>   <false/>
  <key>NSSupportsAutomaticGraphicsSwitching</key><true/>
  <key>LSMinimumSystemVersion</key>    <string>13.0</string>
</dict>
</plist>
PLIST

echo ""
echo "=== PhotoNamer.app is ready ==="
echo ""
echo "  • Double-click PhotoNamer.app in Finder to launch"
echo "  • Drag it to your Dock for quick access"
echo ""
echo "Important: PhotoNamer.app must stay in this project folder."
echo "If you move the project, run this script again to rebuild it."
