# Extended product catalog (200 products)

Upstream Online Boutique sells 9 products, too few for recommendations to be
meaningful (for a mug, only two other kitchen items exist). This folder
extends the catalog to 200 products without changing any upstream code.

| | |
|---|---|
| Upstream products | 9, unchanged (same ids, names, pictures) |
| New products | 191 across 17 groups: cookware, coffee and tea, decor, bed and bath, tops, bottoms, outerwear, footwear, accessories, jewelry, bags, skincare, hair, fitness, outdoor and travel, stationery, tech accessories |
| Category tags | 24 (e.g. `kitchen`, `coffee`, `outerwear`, `fitness`) |
| Pictures | One generated SVG per new product (colour per group, name and category) |

## Files

| Path | Purpose |
|---|---|
| `generate_catalog.py` | Product table and generator; deterministic (ids derive from names) |
| `productcatalogservice/products.json` | Generated catalog (upstream 9 + 191 new) |
| `productcatalogservice/Dockerfile` | Upstream `productcatalogservice` image with this `products.json` |
| `frontend/static/img/products/generated/` | Generated pictures |
| `frontend/Dockerfile` | Upstream `frontend` image plus these pictures |

`infra/local/docker-compose.yml` builds both images automatically.

## Changing the catalog

Edit the `GROUPS` table in `generate_catalog.py`, then:

```bash
python generate_catalog.py
cd ../infra/local && docker compose up -d --build productcatalogservice frontend
```

The generator refuses duplicate names or ids and checks the total count.

## Notes

- The Locust load generator still browses the 9 upstream product ids, which
  all remain in the catalog.
- On Azure these two services will need the same thin images, pushed to a
  registry (Phase 5 CI/CD), instead of the plain upstream images.
