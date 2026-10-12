using UnityEngine;

/// <summary>A block or pig that takes damage from collision impulses and breaks apart.</summary>
[RequireComponent(typeof(Rigidbody2D))]
public class Destructible : MonoBehaviour
{
    public float maxHealth = 5f;
    public int score = 500;
    public bool isPig;
    public Color debrisColor = Color.white;

    float health;
    SpriteRenderer sr;
    Color baseColor;
    bool dead;

    void Start()
    {
        // Start, not Awake: the spawner configures maxHealth right after AddComponent.
        health = maxHealth;
        sr = GetComponent<SpriteRenderer>();
        baseColor = sr.color;
    }

    void OnCollisionEnter2D(Collision2D col)
    {
        if (dead || sr == null || Game.Instance == null || !Game.Instance.DamageEnabled) return;

        float impulse = 0f;
        for (int i = 0; i < col.contactCount; i++)
            impulse += col.GetContact(i).normalImpulse;
        // Contacts from a fast, light object can report small impulses; relative speed keeps hits meaningful.
        impulse = Mathf.Max(impulse, col.relativeVelocity.magnitude * 0.25f);

        if (col.collider.GetComponent<Bird>() != null) impulse *= 1.5f;
        if (impulse < 0.8f) return;

        Damage(impulse);
        if (impulse > 2f) Game.Instance.PlaySound("hit", Mathf.Clamp01(impulse / 10f));
    }

    public void Damage(float amount)
    {
        if (dead || sr == null) return;
        health -= amount;
        if (health <= 0f)
        {
            Break();
            return;
        }
        float t = health / maxHealth;
        sr.color = Color.Lerp(baseColor * new Color(0.55f, 0.55f, 0.55f, 1f), baseColor, t);
    }

    public void Break()
    {
        if (dead) return;
        dead = true;
        if (Game.Instance != null) Game.Instance.OnDestroyed(this);
        Debris.Burst(transform.position, debrisColor, isPig ? 14 : 8, transform.localScale.magnitude * 0.12f);
        Destroy(gameObject);
    }

    void Update()
    {
        // Knocked out of the world.
        if (!dead && (transform.position.y < -6f || Mathf.Abs(transform.position.x) > 40f))
            Break();
    }
}
