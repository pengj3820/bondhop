using System.Collections.Generic;
using UnityEngine;

/// <summary>
/// Game manager. Builds the whole scene in code (camera, ground, slingshot, levels), so the
/// project runs from an empty scene. Bootstraps itself on load.
/// </summary>
public class Game : MonoBehaviour
{
    public static Game Instance { get; private set; }

    enum State { Menu, Aiming, Flying, Won, Lost }

    // World layout: ground top is y = 0, slingshot at x = -8, structures around x = 4..12.
    const float ViewLeft = -11.5f, ViewRight = 13.5f, GroundShown = 1.4f;
    static readonly Vector2 SlingPos = new Vector2(-8f, 0f);

    State state = State.Menu;
    int level;
    int score;
    int levelStartScore;
    int bestTotal;
    float levelStartTime;
    float stateTime;
    float settleTime;

    Camera cam;
    AudioSource audioSource;
    Slingshot sling;
    Transform levelRoot;
    readonly List<Bird> queue = new List<Bird>();
    Bird current;
    readonly List<Destructible> pigs = new List<Destructible>();
    readonly List<Popup> popups = new List<Popup>();

    struct Popup { public Vector3 pos; public string text; public float time; public Color color; }

    public bool DamageEnabled => state != State.Menu && Time.time - levelStartTime > 1.0f;

    [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
    static void Bootstrap()
    {
        if (Instance == null) new GameObject("Game").AddComponent<Game>();
    }

    void Awake()
    {
        Instance = this;
        Application.targetFrameRate = 60;
        Screen.sleepTimeout = SleepTimeout.NeverSleep;
        Physics2D.velocityIterations = 12;
        Physics2D.positionIterations = 6;
        bestTotal = PlayerPrefs.GetInt("best", 0);

        SetupCamera();
        audioSource = gameObject.AddComponent<AudioSource>();
        BuildWorld();
        sling = Slingshot.Create(SlingPos);
        LoadLevel(0);
        state = State.Menu;
    }

    // ---- setup ------------------------------------------------------------

    void SetupCamera()
    {
        cam = Camera.main;
        if (cam == null)
        {
            var go = new GameObject("Main Camera");
            go.tag = "MainCamera";
            cam = go.AddComponent<Camera>();
            go.AddComponent<AudioListener>();
        }
        cam.orthographic = true;
        cam.clearFlags = CameraClearFlags.SolidColor;
        cam.backgroundColor = new Color(0.53f, 0.8f, 0.96f);
        FitCamera();
    }

    void FitCamera()
    {
        float aspect = (float)Screen.width / Mathf.Max(1, Screen.height);
        float halfWidth = (ViewRight - ViewLeft) * 0.5f;
        cam.orthographicSize = Mathf.Max(halfWidth / aspect, 5.5f);
        cam.transform.position = new Vector3((ViewLeft + ViewRight) * 0.5f, cam.orthographicSize - GroundShown, -10f);
    }

    void BuildWorld()
    {
        var world = new GameObject("World").transform;

        // Distant hills and clouds (decor only).
        for (int i = 0; i < 6; i++)
        {
            float x = -14f + i * 6.5f;
            Decor(world, Art.Circle, new Vector2(x, -2.5f), new Vector2(9f, 7f), new Color(0.47f, 0.75f, 0.4f), -20);
        }
        for (int i = 0; i < 5; i++)
            Decor(world, Art.Cloud, new Vector2(-10f + i * 6f + (i % 2) * 2f, 7.5f + (i % 3) * 1.2f), new Vector2(4f, 2.5f), Color.white, -25);

        // Ground.
        var ground = Decor(world, Art.Square, new Vector2(5f, -5f), new Vector2(90f, 10f), new Color(0.42f, 0.29f, 0.16f), 0);
        ground.AddComponent<BoxCollider2D>();
        var rb = ground.AddComponent<Rigidbody2D>();
        rb.bodyType = RigidbodyType2D.Static;
        ground.name = "Ground";
        Decor(world, Art.Square, new Vector2(5f, -0.15f), new Vector2(90f, 0.3f), new Color(0.35f, 0.7f, 0.2f), 1);

        var mat = new PhysicsMaterial2D("Ground") { friction = 0.8f, bounciness = 0.05f };
        ground.GetComponent<BoxCollider2D>().sharedMaterial = mat;
    }

    static GameObject Decor(Transform parent, Sprite sprite, Vector2 pos, Vector2 size, Color color, int order)
    {
        var go = new GameObject(sprite.name);
        go.transform.SetParent(parent);
        go.transform.position = pos;
        go.transform.localScale = new Vector3(size.x, size.y, 1f);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = sprite;
        sr.color = color;
        sr.sortingOrder = order;
        return go;
    }

    // ---- levels -----------------------------------------------------------

    PhysicsMaterial2D blockMat;
    PhysicsMaterial2D BlockMat => blockMat ? blockMat : (blockMat = new PhysicsMaterial2D("Block") { friction = 0.7f, bounciness = 0.02f });

    Destructible Block(BlockMaterial m, float x, float y, float w, float h, float angle = 0f)
    {
        var go = new GameObject(m + " Block");
        go.transform.SetParent(levelRoot);
        go.transform.position = new Vector2(x, y);
        go.transform.rotation = Quaternion.Euler(0, 0, angle);
        go.transform.localScale = new Vector3(w, h, 1f);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = Art.Block(m);
        sr.sortingOrder = 3;
        var rb = go.AddComponent<Rigidbody2D>();
        float density = m == BlockMaterial.Stone ? 2.4f : m == BlockMaterial.Glass ? 0.8f : 0.7f;
        rb.mass = Mathf.Max(0.15f, w * h * density);
        rb.interpolation = RigidbodyInterpolation2D.Interpolate;
        var col = go.AddComponent<BoxCollider2D>();
        col.sharedMaterial = BlockMat;
        var d = go.AddComponent<Destructible>();
        switch (m)
        {
            case BlockMaterial.Glass: d.maxHealth = 2.5f; d.score = 300; d.debrisColor = new Color(0.75f, 0.92f, 1f); break;
            case BlockMaterial.Stone: d.maxHealth = 22f; d.score = 800; d.debrisColor = new Color(0.5f, 0.5f, 0.55f); break;
            default: d.maxHealth = 7f; d.score = 500; d.debrisColor = new Color(0.75f, 0.5f, 0.25f); break;
        }
        d.maxHealth *= Mathf.Clamp(w * h * 2f, 0.6f, 2f);
        return d;
    }

    void Pig(float x, float y, float radius = 0.38f, bool helmet = false)
    {
        var go = new GameObject("Pig");
        go.transform.SetParent(levelRoot);
        go.transform.position = new Vector2(x, y + radius);
        go.transform.localScale = Vector3.one * radius * 2f;
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = Art.Pig(helmet);
        sr.sortingOrder = 4;
        var rb = go.AddComponent<Rigidbody2D>();
        rb.mass = 0.6f + radius;
        rb.angularDrag = 2f;
        rb.interpolation = RigidbodyInterpolation2D.Interpolate;
        var col = go.AddComponent<CircleCollider2D>();
        col.radius = 0.5f;
        col.sharedMaterial = BlockMat;
        var d = go.AddComponent<Destructible>();
        d.isPig = true;
        d.maxHealth = (helmet ? 7f : 3f) * (radius / 0.38f);
        d.score = 5000;
        d.debrisColor = new Color(0.45f, 0.8f, 0.25f);
        pigs.Add(d);
    }

    /// Two posts and a roof plank. Returns the height of the roof top.
    float Frame(BlockMaterial m, float cx, float baseY, float width, float height, BlockMaterial? roof = null)
    {
        const float t = 0.3f;
        Block(m, cx - width * 0.5f + t * 0.5f, baseY + height * 0.5f, t, height);
        Block(m, cx + width * 0.5f - t * 0.5f, baseY + height * 0.5f, t, height);
        Block(roof ?? m, cx, baseY + height + t * 0.5f, width + 0.1f, t);
        return baseY + height + t;
    }

    public const int LevelCount = 5;

    void BuildLevel(int index)
    {
        const BlockMaterial W = BlockMaterial.Wood, G = BlockMaterial.Glass, S = BlockMaterial.Stone;
        switch (index)
        {
            case 0: // A simple hut.
            {
                float top = Frame(W, 6f, 0f, 2.4f, 2f);
                Pig(6f, 0f);
                Pig(6f, top);
                SetBirds(BirdKind.Red, BirdKind.Red, BirdKind.Red);
                break;
            }
            case 1: // Two-storey tower with glass.
            {
                float y1 = Frame(W, 7f, 0f, 2.6f, 1.8f);
                float y2 = Frame(G, 7f, y1, 2.0f, 1.5f, W);
                Pig(7f, 0f);
                Pig(7f, y1);
                Pig(7f, y2, 0.32f);
                Block(G, 4.5f, 0.6f, 0.6f, 1.2f);
                SetBirds(BirdKind.Red, BirdKind.Yellow, BirdKind.Red);
                break;
            }
            case 2: // Twin towers joined by a bridge.
            {
                float a = Frame(S, 4.5f, 0f, 1.8f, 1.6f);
                float b = Frame(S, 9.5f, 0f, 1.8f, 1.6f);
                a = Frame(W, 4.5f, a, 1.6f, 1.4f);
                b = Frame(W, 9.5f, b, 1.6f, 1.4f);
                Block(W, 7f, a + 0.15f, 5.4f, 0.3f);
                Pig(4.5f, 0f);
                Pig(9.5f, 0f, 0.38f, true);
                Pig(7f, 0f, 0.5f);
                Pig(7f, a + 0.3f, 0.32f);
                SetBirds(BirdKind.Red, BirdKind.Yellow, BirdKind.Red, BirdKind.Yellow);
                break;
            }
            case 3: // Pyramid of frames.
            {
                Frame(W, 4.6f, 0f, 1.8f, 1.4f);
                Frame(G, 6.6f, 0f, 1.8f, 1.4f);
                Frame(W, 8.6f, 0f, 1.8f, 1.4f);
                float top1 = 1.7f;
                Frame(W, 5.6f, top1, 1.8f, 1.3f, S);
                Frame(W, 7.6f, top1, 1.8f, 1.3f, S);
                float top2 = top1 + 1.6f;
                Frame(G, 6.6f, top2, 1.8f, 1.2f, W);
                Pig(4.6f, 0f, 0.32f);
                Pig(6.6f, 0f, 0.32f);
                Pig(8.6f, 0f, 0.32f);
                Pig(6.6f, top2, 0.36f, true);
                Pig(6.6f, top2 + 1.5f, 0.4f);
                SetBirds(BirdKind.Yellow, BirdKind.Red, BirdKind.Yellow, BirdKind.Red);
                break;
            }
            default: // Fortress on a stone hill.
            {
                Block(S, 8f, 0.5f, 6f, 1f);
                float y = 1f;
                Frame(S, 6f, y, 1.6f, 1.6f, W);
                Frame(S, 10f, y, 1.6f, 1.6f, W);
                float mid = Frame(W, 8f, y, 1.8f, 2.2f, S);
                Frame(G, 8f, mid, 1.4f, 1.2f, W);
                Block(G, 4.2f, 0.9f, 0.5f, 1.8f);
                Block(W, 12.2f, 1.1f, 0.4f, 2.2f);
                Pig(6f, y, 0.34f);
                Pig(10f, y, 0.34f, true);
                Pig(8f, y, 0.42f, true);
                Pig(8f, mid, 0.3f);
                Pig(8f, mid + 1.5f, 0.5f);
                SetBirds(BirdKind.Red, BirdKind.Yellow, BirdKind.Red, BirdKind.Yellow, BirdKind.Red);
                break;
            }
        }
    }

    void SetBirds(params BirdKind[] kinds)
    {
        for (int i = 0; i < kinds.Length; i++)
        {
            var b = Bird.Create(kinds[i], Vector2.zero);
            b.transform.SetParent(levelRoot, true);
            queue.Add(b);
        }
        LayoutQueue();
    }

    void LayoutQueue()
    {
        for (int i = 0; i < queue.Count; i++)
            queue[i].transform.position = new Vector2(SlingPos.x - 0.9f - i * 0.75f, Bird.Radius);
    }

    void LoadLevel(int index)
    {
        if (levelRoot != null)
        {
            levelRoot.gameObject.SetActive(false); // Destroy is deferred; keep old bodies out of this frame's physics.
            Destroy(levelRoot.gameObject);
        }
        queue.Clear();
        pigs.Clear();
        popups.Clear();
        current = null;
        sling.Clear();

        level = index;
        levelRoot = new GameObject("Level " + (index + 1)).transform;
        if (index == 0) score = 0;
        levelStartScore = score;
        BuildLevel(index);
        levelStartTime = Time.time;
        NextBird();
    }

    void NextBird()
    {
        if (current != null) Debris.Burst(current.transform.position, Color.white, 6, 0.2f);
        if (current != null) Destroy(current.gameObject);
        current = null;
        if (queue.Count == 0) return;
        current = queue[0];
        queue.RemoveAt(0);
        sling.Load(current);
        LayoutQueue();
        SetState(State.Aiming);
    }

    void SetState(State s)
    {
        state = s;
        stateTime = Time.time;
        settleTime = 0f;
        if (s == State.Won) PlaySound("win");
        if (s == State.Lost) PlaySound("lose");
    }

    // ---- events -----------------------------------------------------------

    public void OnDestroyed(Destructible d)
    {
        AddScore(d.score, d.transform.position, d.isPig ? new Color(0.3f, 0.9f, 0.2f) : Color.white);
        if (d.isPig)
        {
            pigs.Remove(d);
            PlaySound("pig");
        }
        else
        {
            PlaySound("hit", 0.6f);
        }
    }

    void AddScore(int amount, Vector3 pos, Color color)
    {
        score += amount;
        popups.Add(new Popup { pos = pos, text = amount.ToString(), time = Time.time, color = color });
    }

    public void PlaySound(string name, float volume = 1f)
    {
        if (audioSource != null) audioSource.PlayOneShot(Art.Sound(name), volume);
    }

    // ---- loop -------------------------------------------------------------

    int lastW, lastH;

    void Update()
    {
        if (Screen.width != lastW || Screen.height != lastH)
        {
            lastW = Screen.width;
            lastH = Screen.height;
            FitCamera();
        }

        if (Input.GetKeyDown(KeyCode.Escape))
        {
            if (state == State.Menu) Application.Quit();
            else SetState(State.Menu);
        }

        bool down = Input.GetMouseButtonDown(0);
        bool held = Input.GetMouseButton(0);
        bool up = Input.GetMouseButtonUp(0);
        Vector2 world = cam.ScreenToWorldPoint(Input.mousePosition);
        // Ignore presses that land on the on-screen buttons (top strip of the screen).
        if (down && Input.mousePosition.y > Screen.height - Scale * 80f) down = false;

        switch (state)
        {
            case State.Aiming:
                if (sling.HandleInput(down, held, up, world))
                {
                    PlaySound("launch");
                    SetState(State.Flying);
                }
                break;

            case State.Flying:
                if (down && current != null && current.TryAbility()) PlaySound("launch", 0.7f);
                UpdateFlying();
                break;
        }
    }

    void UpdateFlying()
    {
        bool birdDone = current == null || current.Done;
        bool allSlow = birdDone && WorldAtRest();
        if (pigs.Count == 0 || allSlow) settleTime += Time.deltaTime;
        else settleTime = 0f;

        // Give the world a moment to settle (or hard cap) before deciding.
        bool timeout = birdDone && Time.time - stateTime > 14f;
        if (settleTime < 1.0f && !timeout) return;

        if (pigs.Count == 0)
        {
            int bonus = queue.Count * 10000;
            if (bonus > 0) AddScore(bonus, sling.RestPoint + Vector2.up, new Color(1f, 0.85f, 0.2f));
            if (score > bestTotal && level == LevelCount - 1)
            {
                bestTotal = score;
                PlayerPrefs.SetInt("best", bestTotal);
                PlayerPrefs.Save();
            }
            SetState(State.Won);
        }
        else if (queue.Count > 0)
        {
            NextBird();
        }
        else
        {
            SetState(State.Lost);
        }
    }

    bool WorldAtRest()
    {
        foreach (var rb in levelRoot.GetComponentsInChildren<Rigidbody2D>())
            if (rb.bodyType == RigidbodyType2D.Dynamic && rb.velocity.sqrMagnitude > 0.04f)
                return false;
        return true;
    }

    // ---- UI ---------------------------------------------------------------

    static float Scale => Screen.height / 720f;

    GUIStyle label, big, button, popup;

    void EnsureStyles()
    {
        if (label != null) return;
        label = new GUIStyle(GUI.skin.label) { fontSize = 30, fontStyle = FontStyle.Bold };
        label.normal.textColor = Color.white;
        big = new GUIStyle(label) { fontSize = 64, alignment = TextAnchor.MiddleCenter };
        popup = new GUIStyle(label) { alignment = TextAnchor.MiddleCenter };
        button = new GUIStyle(GUI.skin.button) { fontSize = 32, fontStyle = FontStyle.Bold };
    }

    void Shadowed(Rect r, string text, GUIStyle style, Color color)
    {
        var old = style.normal.textColor;
        style.normal.textColor = new Color(0, 0, 0, 0.6f);
        GUI.Label(new Rect(r.x + 3, r.y + 3, r.width, r.height), text, style);
        style.normal.textColor = color;
        GUI.Label(r, text, style);
        style.normal.textColor = old;
    }

    void OnGUI()
    {
        EnsureStyles();
        float s = Scale;
        GUI.matrix = Matrix4x4.Scale(new Vector3(s, s, 1f));
        float w = Screen.width / s, h = 720f;

        // Score popups (in world space).
        GUI.matrix = Matrix4x4.identity;
        for (int i = popups.Count - 1; i >= 0; i--)
        {
            float age = Time.time - popups[i].time;
            if (age > 1.2f) { popups.RemoveAt(i); continue; }
            Vector3 sp = cam.WorldToScreenPoint(popups[i].pos + Vector3.up * age);
            var c = popups[i].color;
            c.a = 1f - age / 1.2f;
            popup.fontSize = Mathf.RoundToInt(30 * s);
            Shadowed(new Rect(sp.x - 100 * s, Screen.height - sp.y - 20 * s, 200 * s, 44 * s), popups[i].text, popup, c);
        }
        GUI.matrix = Matrix4x4.Scale(new Vector3(s, s, 1f));

        if (state == State.Menu)
        {
            GUI.color = new Color(0, 0, 0, 0.35f);
            GUI.DrawTexture(new Rect(0, 0, w, h), Texture2D.whiteTexture);
            GUI.color = Color.white;
            Shadowed(new Rect(0, 140, w, 100), "ANGRY BIRDS", big, new Color(1f, 0.3f, 0.2f));
            Shadowed(new Rect(0, 230, w, 50), "Drag the bird back and release to fire.  Yellow birds: tap mid-air to boost!",
                new GUIStyle(label) { alignment = TextAnchor.MiddleCenter, fontSize = 24 }, Color.white);
            if (bestTotal > 0)
                Shadowed(new Rect(0, 280, w, 50), "Best total: " + bestTotal, new GUIStyle(label) { alignment = TextAnchor.MiddleCenter }, Color.yellow);
            if (GUI.Button(new Rect(w / 2 - 160, 360, 320, 90), "PLAY", button))
                LoadLevel(0);
            if (level > 0 && GUI.Button(new Rect(w / 2 - 160, 470, 320, 80), "CONTINUE  (Level " + (level + 1) + ")", new GUIStyle(button) { fontSize = 24 }))
                LoadLevel(level);
            return;
        }

        Shadowed(new Rect(24, 16, 400, 44), "Level " + (level + 1) + " / " + LevelCount, label, Color.white);
        Shadowed(new Rect(24, 56, 400, 44), "Score " + score, label, Color.white);
        Shadowed(new Rect(24, 96, 400, 44), "Pigs " + pigs.Count, label, new Color(0.7f, 1f, 0.5f));

        if (GUI.Button(new Rect(w - 160, 16, 140, 60), "RETRY", new GUIStyle(button) { fontSize = 22 })) LoadLevel(level);
        if (GUI.Button(new Rect(w - 290, 16, 120, 60), "MENU", new GUIStyle(button) { fontSize = 22 })) SetState(State.Menu);

        if (state == State.Won || state == State.Lost)
        {
            GUI.color = new Color(0, 0, 0, 0.45f);
            GUI.DrawTexture(new Rect(0, 0, w, h), Texture2D.whiteTexture);
            GUI.color = Color.white;
            bool won = state == State.Won;
            bool last = level == LevelCount - 1;
            string title = won ? (last ? "YOU BEAT THEM ALL!" : "LEVEL CLEARED!") : "LEVEL FAILED";
            Shadowed(new Rect(0, 150, w, 100), title, big, won ? new Color(1f, 0.85f, 0.2f) : new Color(1f, 0.4f, 0.3f));
            if (won)
            {
                int stars = 1 + (queue.Count >= 1 ? 1 : 0) + (queue.Count >= 2 ? 1 : 0);
                for (int i = 0; i < 3; i++)
                {
                    GUI.color = i < stars ? new Color(1f, 0.85f, 0.15f) : new Color(1f, 1f, 1f, 0.3f);
                    GUI.DrawTexture(new Rect(w / 2 - 130 + i * 90, 245, 80, 80), Art.Star.texture);
                }
                GUI.color = Color.white;
                Shadowed(new Rect(0, 320, w, 50), "Level score " + (score - levelStartScore) + "     Total " + score,
                    new GUIStyle(label) { alignment = TextAnchor.MiddleCenter }, Color.white);
            }
            if (Time.time - stateTime < 0.6f) return;
            if (GUI.Button(new Rect(w / 2 - 330, 420, 300, 90), "RETRY", button)) LoadLevel(level);
            if (won && GUI.Button(new Rect(w / 2 + 30, 420, 300, 90), last ? "PLAY AGAIN" : "NEXT", button))
                LoadLevel(last ? 0 : level + 1);
            if (!won && GUI.Button(new Rect(w / 2 + 30, 420, 300, 90), "MENU", button)) SetState(State.Menu);
        }
    }
}
