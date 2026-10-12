using UnityEngine;

/// <summary>The slingshot: draws itself, handles drag-and-release input and the aiming preview.</summary>
public class Slingshot : MonoBehaviour
{
    public const float MaxDrag = 1.6f;
    public const float MaxSpeed = 15f;
    const int Dots = 18;

    public Vector2 RestPoint => (Vector2)transform.position + new Vector2(0f, 2.35f);

    public Bird Loaded { get; private set; }
    public bool Dragging { get; private set; }

    Vector2 backTip, frontTip;
    Transform backBand, frontBand;
    readonly Transform[] dots = new Transform[Dots];
    float lastStretchSound;

    public static Slingshot Create(Vector2 basePos)
    {
        var go = new GameObject("Slingshot");
        go.transform.position = basePos;
        var s = go.AddComponent<Slingshot>();
        s.Build();
        return s;
    }

    void Build()
    {
        Color wood = new Color(0.45f, 0.26f, 0.1f);
        Vector2 b = transform.position;
        Part("Post", b + new Vector2(0f, 0.85f), new Vector2(0.28f, 1.7f), 0f, wood, 2);
        Part("ArmBack", b + new Vector2(-0.2f, 2.05f), new Vector2(0.2f, 0.8f), 18f, wood * 0.85f, 1);
        Part("ArmFront", b + new Vector2(0.2f, 2.05f), new Vector2(0.2f, 0.8f), -18f, wood, 7);
        backTip = b + new Vector2(-0.31f, 2.42f);
        frontTip = b + new Vector2(0.31f, 2.42f);

        Color band = new Color(0.3f, 0.15f, 0.05f);
        backBand = Part("BandBack", backTip, Vector2.one * 0.1f, 0f, band, 4).transform;
        frontBand = Part("BandFront", frontTip, Vector2.one * 0.1f, 0f, band, 6).transform;

        for (int i = 0; i < Dots; i++)
        {
            var d = Part("Dot", Vector2.zero, Vector2.one * 0.12f, 0f, new Color(1, 1, 1, 0.8f), 8, Art.Circle);
            d.SetActive(false);
            dots[i] = d.transform;
        }
        SetBands(RestPoint);
    }

    GameObject Part(string name, Vector2 pos, Vector2 size, float angle, Color color, int order, Sprite sprite = null)
    {
        var go = new GameObject(name);
        go.transform.SetParent(transform, true);
        go.transform.position = pos;
        go.transform.rotation = Quaternion.Euler(0, 0, angle);
        go.transform.localScale = new Vector3(size.x, size.y, 1f);
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = sprite ? sprite : Art.Square;
        sr.color = color;
        sr.sortingOrder = order;
        return go;
    }

    public void Load(Bird bird)
    {
        Loaded = bird;
        Dragging = false;
        bird.transform.position = RestPoint;
        bird.transform.rotation = Quaternion.identity;
        SetBands(RestPoint);
    }

    public void Clear()
    {
        Loaded = null;
        Dragging = false;
        SetBands(RestPoint);
        ShowDots(false, Vector2.zero, Vector2.zero);
    }

    /// Handles a pointer (mouse or first touch). Returns true if a bird was launched this frame.
    public bool HandleInput(bool down, bool held, bool up, Vector2 worldPos)
    {
        if (Loaded == null) return false;

        if (down && Vector2.Distance(worldPos, Loaded.transform.position) < 1.3f)
            Dragging = true;

        if (!Dragging) return false;

        Vector2 offset = Vector2.ClampMagnitude(worldPos - RestPoint, MaxDrag);
        Vector2 pos = RestPoint + offset;
        pos.y = Mathf.Max(pos.y, Bird.Radius + 0.05f);
        offset = pos - RestPoint;

        if (held || down)
        {
            Loaded.transform.position = pos;
            SetBands(pos);
            Vector2 v = LaunchVelocity(offset);
            ShowDots(offset.magnitude > 0.25f, pos, v);
            if (offset.magnitude > 0.6f && Time.time - lastStretchSound > 0.6f && Game.Instance != null)
            {
                lastStretchSound = Time.time;
                Game.Instance.PlaySound("stretch", 0.5f);
            }
        }

        if (up)
        {
            Dragging = false;
            ShowDots(false, Vector2.zero, Vector2.zero);
            if (offset.magnitude < 0.3f)
            {
                Loaded.transform.position = RestPoint;
                SetBands(RestPoint);
                return false;
            }
            Loaded.Launch(LaunchVelocity(offset));
            Loaded = null;
            SetBands(RestPoint);
            return true;
        }
        return false;
    }

    static Vector2 LaunchVelocity(Vector2 offset) => -offset / MaxDrag * MaxSpeed;

    void ShowDots(bool show, Vector2 start, Vector2 v)
    {
        for (int i = 0; i < Dots; i++)
        {
            dots[i].gameObject.SetActive(show);
            if (!show) continue;
            float t = (i + 1) * 0.07f;
            dots[i].position = start + v * t + 0.5f * Physics2D.gravity * t * t;
            float s = Mathf.Lerp(0.16f, 0.06f, i / (float)Dots);
            dots[i].localScale = new Vector3(s, s, 1f);
        }
    }

    void SetBands(Vector2 pouch)
    {
        Stretch(backBand, backTip, pouch);
        Stretch(frontBand, frontTip, pouch);
    }

    static void Stretch(Transform band, Vector2 from, Vector2 to)
    {
        Vector2 d = to - from;
        band.position = (from + to) * 0.5f;
        band.rotation = Quaternion.Euler(0, 0, Mathf.Atan2(d.y, d.x) * Mathf.Rad2Deg);
        band.localScale = new Vector3(Mathf.Max(d.magnitude, 0.05f), 0.11f, 1f);
    }
}
