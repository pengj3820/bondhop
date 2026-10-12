using UnityEngine;

/// <summary>Cheap physics-free particle used for breaking blocks and popping pigs.</summary>
public class Debris : MonoBehaviour
{
    Vector2 velocity;
    float spin;
    float life;
    float age;
    SpriteRenderer sr;

    public static void Burst(Vector3 pos, Color color, int count, float size)
    {
        size = Mathf.Clamp(size, 0.08f, 0.3f);
        for (int i = 0; i < count; i++)
        {
            var go = new GameObject("Debris");
            go.transform.position = pos + (Vector3)(Random.insideUnitCircle * 0.3f);
            go.transform.localScale = Vector3.one * size * Random.Range(0.6f, 1.4f);
            go.transform.rotation = Quaternion.Euler(0, 0, Random.Range(0f, 360f));
            var d = go.AddComponent<Debris>();
            d.sr = go.AddComponent<SpriteRenderer>();
            d.sr.sprite = Random.value < 0.5f ? Art.Square : Art.Circle;
            d.sr.color = color;
            d.sr.sortingOrder = 20;
            d.velocity = Random.insideUnitCircle * 4f + Vector2.up * 2f;
            d.spin = Random.Range(-540f, 540f);
            d.life = Random.Range(0.6f, 1.1f);
        }
    }

    void Update()
    {
        float dt = Time.deltaTime;
        age += dt;
        velocity += Physics2D.gravity * dt;
        transform.position += (Vector3)(velocity * dt);
        transform.Rotate(0, 0, spin * dt);
        var c = sr.color;
        c.a = 1f - age / life;
        sr.color = c;
        if (age >= life) Destroy(gameObject);
    }
}
