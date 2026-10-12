using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Procedurally generated sprites and sounds, so the project needs no imported art assets.
/// Every sprite is 1x1 world unit; scale the transform to size it.
/// </summary>
public static class Art
{
    const int Res = 128;

    static readonly Dictionary<string, Sprite> cache = new Dictionary<string, Sprite>();
    static readonly Dictionary<string, AudioClip> sounds = new Dictionary<string, AudioClip>();

    public static Sprite Square => Get("square", () => Make((x, y) => Color.white));

    public static Sprite Circle => Get("circle", () => Make((x, y) => Disc(x, y, 0.5f, Color.white)));

    public static Sprite Block(BlockMaterial material)
    {
        return Get("block_" + material, () =>
        {
            Color fill, edge;
            switch (material)
            {
                case BlockMaterial.Glass: fill = new Color(0.68f, 0.88f, 1f, 0.75f); edge = new Color(0.85f, 0.97f, 1f, 0.95f); break;
                case BlockMaterial.Stone: fill = new Color(0.55f, 0.56f, 0.6f); edge = new Color(0.36f, 0.37f, 0.41f); break;
                default: fill = new Color(0.82f, 0.56f, 0.28f); edge = new Color(0.55f, 0.33f, 0.13f); break;
            }
            return Make((x, y) =>
            {
                float border = Mathf.Min(Mathf.Min(x, 1 - x), Mathf.Min(y, 1 - y));
                if (border < 0.07f) return edge;
                Color c = fill;
                if (material == BlockMaterial.Wood)
                    c *= 0.92f + 0.08f * Mathf.Sin(y * 40f + Mathf.Sin(x * 9f) * 2f);
                else if (material == BlockMaterial.Stone)
                    c *= 0.9f + 0.1f * Mathf.PerlinNoise(x * 12f, y * 12f);
                else if (Mathf.Abs(x - y) < 0.04f || Mathf.Abs(x - y + 0.25f) < 0.02f)
                    c = edge;
                c.a = fill.a;
                return c;
            });
        });
    }

    public static Sprite Bird(BirdKind kind)
    {
        return Get("bird_" + kind, () =>
        {
            Color body = kind == BirdKind.Yellow ? new Color(1f, 0.85f, 0.15f) : new Color(0.86f, 0.12f, 0.12f);
            Color belly = new Color(0.97f, 0.88f, 0.75f);
            return Make((x, y) =>
            {
                Color c = Disc(x, y, 0.48f, body);
                if (c.a <= 0) return c;
                c = Over(c, Disc(x, y, 0.26f, belly, 0.45f, 0.22f));
                // eyes
                c = Over(c, Disc(x, y, 0.1f, Color.white, 0.6f, 0.58f));
                c = Over(c, Disc(x, y, 0.1f, Color.white, 0.8f, 0.58f));
                c = Over(c, Disc(x, y, 0.045f, Color.black, 0.63f, 0.57f));
                c = Over(c, Disc(x, y, 0.045f, Color.black, 0.83f, 0.57f));
                // angry brows
                if (Mathf.Abs((y - 0.72f) + (x - 0.55f) * 0.45f) < 0.03f && x > 0.48f && x < 0.92f) c = Color.black;
                // beak
                if (x > 0.68f && x < 0.98f && y > 0.36f && y < 0.5f && (y - 0.43f) * (y - 0.43f) < (0.98f - x) * 0.025f)
                    c = new Color(1f, 0.65f, 0.1f);
                return c;
            });
        });
    }

    public static Sprite Pig(bool helmet)
    {
        return Get("pig_" + helmet, () =>
        {
            Color skin = new Color(0.45f, 0.8f, 0.25f);
            Color dark = new Color(0.25f, 0.55f, 0.12f);
            return Make((x, y) =>
            {
                Color c = Disc(x, y, 0.48f, skin);
                if (c.a <= 0) return c;
                c = Over(c, Disc(x, y, 0.15f, dark, 0.5f, 0.42f));
                c = Over(c, Disc(x, y, 0.13f, new Color(0.6f, 0.9f, 0.4f), 0.5f, 0.42f));
                c = Over(c, Disc(x, y, 0.035f, dark, 0.45f, 0.42f));
                c = Over(c, Disc(x, y, 0.035f, dark, 0.55f, 0.42f));
                c = Over(c, Disc(x, y, 0.085f, Color.white, 0.3f, 0.62f));
                c = Over(c, Disc(x, y, 0.085f, Color.white, 0.7f, 0.62f));
                c = Over(c, Disc(x, y, 0.04f, Color.black, 0.32f, 0.61f));
                c = Over(c, Disc(x, y, 0.04f, Color.black, 0.68f, 0.61f));
                if (helmet && y > 0.72f) c = new Color(0.6f, 0.6f, 0.65f) * (0.85f + 0.15f * y);
                return c;
            });
        });
    }

    public static Sprite Star => Get("star", () => Make((x, y) =>
    {
        // Point-in-polygon test against a 5-pointed star.
        bool inside = false;
        const int n = 10;
        for (int i = 0, j = n - 1; i < n; j = i++)
        {
            Vector2 a = StarVertex(i), b = StarVertex(j);
            if ((a.y > y) != (b.y > y) && x < (b.x - a.x) * (y - a.y) / (b.y - a.y) + a.x)
                inside = !inside;
        }
        return inside ? Color.white : Color.clear;
    }));

    static Vector2 StarVertex(int i)
    {
        float r = i % 2 == 0 ? 0.48f : 0.2f;
        float ang = Mathf.PI / 2f + i * Mathf.PI / 5f;
        return new Vector2(0.5f + r * Mathf.Cos(ang), 0.48f + r * Mathf.Sin(ang));
    }

    public static Sprite Cloud => Get("cloud", () => Make((x, y) =>
    {
        Color w = new Color(1, 1, 1, 0.9f);
        Color c = Disc(x, y, 0.22f, w, 0.3f, 0.4f);
        c = Over(c, Disc(x, y, 0.28f, w, 0.55f, 0.5f));
        c = Over(c, Disc(x, y, 0.2f, w, 0.78f, 0.38f));
        return c;
    }));

    // ---- helpers ----------------------------------------------------------

    static Sprite Get(string key, System.Func<Sprite> make)
    {
        if (!cache.TryGetValue(key, out var s) || s == null)
        {
            s = make();
            cache[key] = s;
        }
        return s;
    }

    static Sprite Make(System.Func<float, float, Color> shade)
    {
        var tex = new Texture2D(Res, Res, TextureFormat.RGBA32, false);
        tex.wrapMode = TextureWrapMode.Clamp;
        tex.filterMode = FilterMode.Bilinear;
        var px = new Color[Res * Res];
        for (int j = 0; j < Res; j++)
            for (int i = 0; i < Res; i++)
                px[j * Res + i] = shade((i + 0.5f) / Res, (j + 0.5f) / Res);
        tex.SetPixels(px);
        tex.Apply();
        return Sprite.Create(tex, new Rect(0, 0, Res, Res), new Vector2(0.5f, 0.5f), Res);
    }

    /// Anti-aliased disc of radius r centred on (cx, cy) in 0..1 texture space.
    static Color Disc(float x, float y, float r, Color col, float cx = 0.5f, float cy = 0.5f)
    {
        float d = Mathf.Sqrt((x - cx) * (x - cx) + (y - cy) * (y - cy));
        float a = Mathf.Clamp01((r - d) * Res);
        col.a *= a;
        return col;
    }

    static Color Over(Color under, Color over)
    {
        if (under.a <= 0) return under;
        float a = over.a;
        Color c = Color.Lerp(under, over, a);
        c.a = under.a;
        return c;
    }

    // ---- sounds -----------------------------------------------------------

    public static AudioClip Sound(string name)
    {
        if (sounds.TryGetValue(name, out var clip) && clip != null) return clip;
        const int rate = 22050;
        float len;
        System.Func<float, float> wave;
        var rng = new System.Random(name.GetHashCode());
        switch (name)
        {
            case "launch":
                len = 0.35f;
                wave = t => (float)(rng.NextDouble() * 2 - 1) * (1 - t / len) * 0.5f * Mathf.Sin(t * 30f);
                break;
            case "stretch":
                len = 0.15f;
                wave = t => Mathf.Sin(2 * Mathf.PI * (300 + 600 * t) * t) * (1 - t / len) * 0.3f;
                break;
            case "pig":
                len = 0.3f;
                wave = t => Mathf.Sin(2 * Mathf.PI * (520 - 900 * t) * t) * (1 - t / len) * 0.5f;
                break;
            case "win":
                len = 0.9f;
                wave = t => Mathf.Sin(2 * Mathf.PI * (t < 0.3f ? 523f : t < 0.6f ? 659f : 784f) * t) * 0.35f * (1 - t / len);
                break;
            case "lose":
                len = 0.9f;
                wave = t => Mathf.Sin(2 * Mathf.PI * (330f - 150f * t) * t) * 0.35f * (1 - t / len);
                break;
            default: // hit
                len = 0.12f;
                wave = t => (float)(rng.NextDouble() * 2 - 1) * Mathf.Exp(-t * 35f) * 0.6f;
                break;
        }
        int n = (int)(rate * len);
        var data = new float[n];
        for (int i = 0; i < n; i++) data[i] = wave(i / (float)rate);
        clip = AudioClip.Create(name, n, 1, rate, false);
        clip.SetData(data, 0);
        sounds[name] = clip;
        return clip;
    }
}

public enum BlockMaterial { Wood, Glass, Stone }

public enum BirdKind { Red, Yellow }
