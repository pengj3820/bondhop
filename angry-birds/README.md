# Angry Birds (Unity)

A small Angry Birds-style physics game in Unity 2022.3 LTS (2D physics, Android, landscape).

- 5 levels made of wood, glass and stone, with regular and helmeted pigs
- Drag the bird back to aim (a dotted trajectory preview is shown), then release to fire
- Red bird: standard; yellow bird: tap mid-air for a speed boost
- Scoring, 3-star rating, best-score record, sound effects
- All art and sound are generated from code, with no imported assets, so the project is easy to read and modify

## Getting the APK (GitHub Actions, one-time setup)

Building a Unity APK requires a Unity license (the free Personal license works), so CI needs your Unity account credentials once:

1. Install [Unity Hub](https://unity.com/download) on your own computer, sign in, and activate a free Personal license (Hub → Preferences → Licenses).
2. Find the license file `Unity_lic.ulf`:
   - Windows: `C:\ProgramData\Unity\Unity_lic.ulf`
   - macOS: `/Library/Application Support/Unity/Unity_lic.ulf`
   - Linux: `~/.local/share/unity3d/Unity/Unity_lic.ulf`
3. Open the GitHub repository → Settings → Secrets and variables → Actions, and add three secrets:
   - `UNITY_LICENSE`: the full contents of `Unity_lic.ulf`
   - `UNITY_EMAIL`: your Unity account email
   - `UNITY_PASSWORD`: your Unity account password
4. Open Actions → **Angry Birds APK** → **Run workflow** (pushing changes to `angry-birds/` also triggers it).
5. After about 20–40 minutes, open the repository's **Releases** page and download `AngryBirds.apk` directly on your phone. You'll need to allow installing apps from unknown sources.

## Building locally

1. Open the `angry-birds` folder in Unity Hub (editor version 2022.3.76f1, with **Android Build Support** installed).
2. Menu **Angry Birds → Build Android APK**; the output is `Builds/Android/AngryBirds.apk`.
3. To play in the editor: menu **Angry Birds → Create Main Scene**, open `Assets/Scenes/Main.unity`, then press Play.

Command line:

```
Unity -batchmode -quit -projectPath angry-birds -executeMethod BuildScript.BuildAndroid -customBuildPath out/AngryBirds.apk
```

## Code layout

| File | Purpose |
|---|---|
| `Assets/Scripts/Game.cs` | Bootstraps itself, builds the scene, level data, game flow, UI |
| `Assets/Scripts/Slingshot.cs` | Slingshot drawing, drag-to-aim, trajectory preview, launch |
| `Assets/Scripts/Bird.cs` | Birds (including the yellow bird's boost) |
| `Assets/Scripts/Destructible.cs` | Collision damage and destruction for blocks and pigs |
| `Assets/Scripts/Art.cs` | Procedurally generated sprites and sound effects |
| `Assets/Scripts/Debris.cs` | Debris particles |
| `Assets/Scripts/Editor/BuildScript.cs` | Android build settings and build entry point |

To add a level, add a `case` to `Game.BuildLevel` and increase `LevelCount`.
