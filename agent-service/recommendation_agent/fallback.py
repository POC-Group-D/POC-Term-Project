"""v1 behaviour, used whenever the agent cannot answer in time or correctly."""

import random


def random_recommendations(catalog_ids, excluded, limit, rng=random):
    """Up to `limit` random catalog products not in `excluded` (same as v1)."""
    candidates = sorted(set(catalog_ids) - set(excluded))
    return rng.sample(candidates, min(limit, len(candidates)))
