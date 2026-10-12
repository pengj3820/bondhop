# Angry Birds (Android, buildable without Unity)

The same game as the Unity version in [`../angry-birds`](../angry-birds) (same 5 levels, tuning and rules), with physics from [planck.js](https://github.com/piqnt/planck.js) (a JavaScript port of Box2D, the same 2D physics engine Unity uses). The APK is a full-screen WebView, so **it can be built without a Unity license**.

## Download

The built APK is at [`release/AngryBirds.apk`](release/AngryBirds.apk). Open it on an Android phone to install (allow "install unknown apps"). Requires Android 7.0 or later.

## Playing
- Drag the bird on the slingshot backwards; a dotted trajectory preview appears. Release to fire.
- Yellow bird: tap the screen mid-air to boost.
- Clear a level by destroying every pig. Each bird left over earns a 10,000-point bonus and extra stars.
- The phone's Back button returns to the menu; pressing Back again on the menu exits.

## Building
Requires JDK 17+ and the Android SDK (`platforms;android-34`, `build-tools;34.0.0`):

```
ANDROID_HOME=/path/to/sdk ./build.sh      # outputs build/AngryBirds.apk
```

To try it on a computer, just open `app/src/main/assets/index.html` in a browser (mouse supported).

| File | Purpose |
|---|---|
| `app/src/main/assets/game.js` | All of the game: levels, physics, slingshot, damage, rendering, UI, sound |
| `app/src/main/assets/planck.min.js` | planck.js 1.5.0 (MIT) |
| `app/src/main/java/.../MainActivity.java` | Full-screen WebView host, Back-button handling |
| `build.sh` | Builds and signs the APK with aapt2/javac/d8/apksigner (no Gradle needed) |
| `keystore/release.keystore` | Signing key (password `angrybirds`); keep it so new versions install over old ones |
