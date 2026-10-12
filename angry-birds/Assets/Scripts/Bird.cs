using UnityEngine;

public class Bird : MonoBehaviour
{
    public const float Radius = 0.32f;

    public BirdKind kind;
    public Rigidbody2D Body { get; private set; }
    public bool Launched { get; private set; }
    public bool AbilityUsed { get; private set; }

    float launchTime;
    float slowTime;
    bool hitSomething;

    public static Bird Create(BirdKind kind, Vector2 pos)
    {
        var go = new GameObject(kind + " Bird");
        go.transform.position = pos;
        go.transform.localScale = Vector3.one * Radius * 2f;
        var sr = go.AddComponent<SpriteRenderer>();
        sr.sprite = Art.Bird(kind);
        sr.sortingOrder = 5;
        var rb = go.AddComponent<Rigidbody2D>();
        rb.bodyType = RigidbodyType2D.Kinematic;
        rb.mass = kind == BirdKind.Yellow ? 1.2f : 1.6f;
        rb.collisionDetectionMode = CollisionDetectionMode2D.Continuous;
        rb.interpolation = RigidbodyInterpolation2D.Interpolate;
        rb.angularDrag = 1.5f;
        var col = go.AddComponent<CircleCollider2D>();
        col.radius = 0.5f;
        col.enabled = false;
        var bird = go.AddComponent<Bird>();
        bird.kind = kind;
        bird.Body = rb;
        return bird;
    }

    public void Launch(Vector2 velocity)
    {
        Launched = true;
        launchTime = Time.time;
        GetComponent<CircleCollider2D>().enabled = true;
        Body.bodyType = RigidbodyType2D.Dynamic;
        Body.velocity = velocity;
        Body.angularVelocity = -velocity.x * 40f;
    }

    /// Yellow bird: tap mid-flight for a speed burst.
    public bool TryAbility()
    {
        if (!Launched || AbilityUsed || hitSomething || kind != BirdKind.Yellow) return false;
        AbilityUsed = true;
        Vector2 dir = Body.velocity.sqrMagnitude > 0.01f ? Body.velocity.normalized : Vector2.right;
        Body.velocity = dir * 24f;
        Debris.Burst(transform.position, new Color(1f, 0.9f, 0.4f), 6, 0.15f);
        return true;
    }

    void OnCollisionEnter2D(Collision2D col) => hitSomething = true;

    /// True once the bird has stopped mattering: at rest, gone off-screen, or flying too long.
    public bool Done
    {
        get
        {
            if (!Launched) return false;
            float since = Time.time - launchTime;
            if (since > 9f) return true;
            Vector3 p = transform.position;
            if (p.y < -5f || p.x > 16f || p.x < -20f) return true; // off-screen
            return since > 0.5f && slowTime > 1.2f;
        }
    }

    void FixedUpdate()
    {
        if (!Launched) return;
        if (Body.velocity.magnitude < 0.25f) slowTime += Time.fixedDeltaTime;
        else slowTime = 0f;
    }
}
