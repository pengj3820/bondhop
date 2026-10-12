using System;
using System.IO;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

/// <summary>
/// Command-line / menu build entry point.
///   Unity -batchmode -quit -projectPath angry-birds -executeMethod BuildScript.BuildAndroid [-customBuildPath out.apk]
/// The game builds itself at runtime, so the only scene is an empty one created here if missing.
/// </summary>
public static class BuildScript
{
    const string ScenePath = "Assets/Scenes/Main.unity";

    [MenuItem("Angry Birds/Build Android APK")]
    public static void BuildAndroid()
    {
        EnsureScene();
        ConfigurePlayer();

        string output = Arg("-customBuildPath") ?? "Builds/Android/AngryBirds.apk";
        if (!output.EndsWith(".apk", StringComparison.OrdinalIgnoreCase))
            output = Path.Combine(output, "AngryBirds.apk");
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(output)));

        EditorUserBuildSettings.buildAppBundle = false;
        EditorUserBuildSettings.SwitchActiveBuildTarget(BuildTargetGroup.Android, BuildTarget.Android);

        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
        {
            scenes = new[] { ScenePath },
            locationPathName = output,
            target = BuildTarget.Android,
            targetGroup = BuildTargetGroup.Android,
            options = BuildOptions.None,
        });

        Debug.Log($"[BuildScript] {report.summary.result}: {output} ({report.summary.totalSize} bytes, {report.summary.totalErrors} errors)");
        if (report.summary.result != BuildResult.Succeeded && Application.isBatchMode)
            EditorApplication.Exit(1);
    }

    [MenuItem("Angry Birds/Create Main Scene")]
    public static void EnsureScene()
    {
        if (!File.Exists(ScenePath))
        {
            Directory.CreateDirectory(Path.GetDirectoryName(ScenePath));
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.Refresh();
        }
        EditorBuildSettings.scenes = new[] { new EditorBuildSettingsScene(ScenePath, true) };
    }

    static void ConfigurePlayer()
    {
        PlayerSettings.companyName = "Bondhop";
        PlayerSettings.productName = "Angry Birds";
        PlayerSettings.bundleVersion = "1.0.0";
        PlayerSettings.SetApplicationIdentifier(BuildTargetGroup.Android, "com.bondhop.angrybirds");

        string code = Arg("-androidVersionCode");
        PlayerSettings.Android.bundleVersionCode = int.TryParse(code, out int c) && c > 0 ? c : 1;

        // IL2CPP + ARM64 so it installs on 64-bit-only phones; ARMv7 for older devices.
        PlayerSettings.SetScriptingBackend(BuildTargetGroup.Android, ScriptingImplementation.IL2CPP);
        PlayerSettings.Android.targetArchitectures = AndroidArchitecture.ARM64 | AndroidArchitecture.ARMv7;
        PlayerSettings.Android.minSdkVersion = AndroidSdkVersions.AndroidApiLevel23;
        PlayerSettings.Android.targetSdkVersion = AndroidSdkVersions.AndroidApiLevelAuto;

        PlayerSettings.defaultInterfaceOrientation = UIOrientation.AutoRotation;
        PlayerSettings.allowedAutorotateToLandscapeLeft = true;
        PlayerSettings.allowedAutorotateToLandscapeRight = true;
        PlayerSettings.allowedAutorotateToPortrait = false;
        PlayerSettings.allowedAutorotateToPortraitUpsideDown = false;

        PlayerSettings.SplashScreen.showUnityLogo = false; // ignored on Personal licenses
        PlayerSettings.Android.useCustomKeystore = false;  // signed with the debug key; fine for sideloading

        // Everything is created from code at runtime, so keep engine modules and the sprite shader
        // even though the scene itself references nothing.
        PlayerSettings.stripEngineCode = false;
        AlwaysInclude("Sprites/Default");
    }

    static void AlwaysInclude(string shaderName)
    {
        var shader = Shader.Find(shaderName);
        var settings = AssetDatabase.LoadAssetAtPath<UnityEngine.Object>("ProjectSettings/GraphicsSettings.asset");
        if (shader == null || settings == null) return;
        var so = new SerializedObject(settings);
        var list = so.FindProperty("m_AlwaysIncludedShaders");
        for (int i = 0; i < list.arraySize; i++)
            if (list.GetArrayElementAtIndex(i).objectReferenceValue == shader) return;
        list.InsertArrayElementAtIndex(list.arraySize);
        list.GetArrayElementAtIndex(list.arraySize - 1).objectReferenceValue = shader;
        so.ApplyModifiedProperties();
    }

    static string Arg(string name)
    {
        var args = Environment.GetCommandLineArgs();
        for (int i = 0; i < args.Length - 1; i++)
            if (args[i] == name) return args[i + 1];
        return null;
    }
}
