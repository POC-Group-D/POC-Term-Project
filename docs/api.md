# Recommendation API, version 2

We redesigned the interface of `recommendationservice`. Google's version 1
returns a bare list of product IDs. Version 2 lets the caller choose how many
recommendations it wants, and returns a reason for each product. Both
implementations, v1 (random picks) and v2 (AI agent), implement version 2, so
the canary still compares two services with the same API.

**Why we changed the interface.** For Option B, the project description says
the AI agent version must keep the interface of the component it replaces
unchanged. After our D3 demo, the lecturer asked us to design the API
ourselves instead of reusing Google's as it is. We met both: the API changed
once, *before* the canary, for both versions at the same time. During the
canary v1 and v2 expose exactly the same contract, so a client cannot tell
which one served a request. The change only adds fields, so old clients keep
working (see [Backward compatibility](#backward-compatibility)).

The contract lives in
[`online-boutique/protos/demo.proto`](../online-boutique/protos/demo.proto)
(gRPC / Protocol Buffers).

## The interface

```protobuf
service RecommendationService {
  rpc ListRecommendations(ListRecommendationsRequest) returns (ListRecommendationsResponse){}
}

message ListRecommendationsRequest {
    string user_id = 1;
    repeated string product_ids = 2;   // viewed product + cart; never recommended back
    int32 max_results = 3;             // NEW: 1-10; 0 = default 5; above 10 = 10
}

message ListRecommendationsResponse {
    repeated string product_ids = 1;              // kept for version 1 clients
    repeated Recommendation recommendations = 2;  // NEW: same products, same order, with reasons
}

message Recommendation {                          // NEW
    string product_id = 1;
    string reason = 2;                            // one short sentence for the shopper
}
```

## Changes from version 1, and why

| Change | Why |
|---|---|
| `max_results` in the request | The caller knows how many fit its page. The frontend showed 4 and silently threw away the 5th; it now asks for 4. Other clients (an app, an email) can ask for more |
| `recommendations` with a `reason` per product | v2's model already explains its choice, and v1 threw that away. A reason under each product tells the shopper why it is suggested ("Perfect for brewing with your mug"), which makes the AI's work visible |
| `Recommendation` message instead of a parallel list | Product and reason travel together, and the message can grow later (for example a score) without another breaking change |

## Backward compatibility

The change is additive. Protocol Buffers skip fields they do not know, and an
unset field reads as its default value. So all four combinations work:

| Client | Server | Result |
|---|---|---|
| version 1 (Google's frontend) | version 2 (ours) | `max_results` = 0, so the default of 5 applies; the client reads `product_ids` and ignores `recommendations` |
| version 2 (our frontend) | version 1 (Google's) | The server ignores `max_results` and returns 5 IDs and no reasons; the frontend keeps the first 4 and shows no reason line |
| version 2 | version 2 | 4 products, each with a reason |
| version 1 | version 1 | Unchanged |

No field was renamed, renumbered or removed. Field numbers 1 and 2 keep their
meaning, so a mixed deployment during a rollout cannot misread messages.

## Behaviour both implementations guarantee

1. At most `max_results` products (default 5, at most 10), with fewer only if
   the catalog has fewer eligible products.
2. Every ID exists in the catalog. There are no duplicates, and none of the
   request's `product_ids` is included.
3. `recommendations` lists the same products as `product_ids`, in the same
   order, and every `reason` is non-empty.

How each version fills in the reasons:

| | Reasons |
|---|---|
| v1 (random) | A rule: the product's category, e.g. "From our kitchen collection" |
| v2 (AI agent) | The model writes one per product in its `recommend` tool call, e.g. "Perfect for brewing with your mug". Products the agent adds at random (fallback, or topping up to `max_results`) get v1's rule-based reason |

The canary's correctness check ([canary-criteria.md](canary-criteria.md))
tests rules 1-3 on every v2 response.

## Implementation

| Part | Files |
|---|---|
| Contract | `online-boutique/protos/demo.proto` |
| v2 (AI agent) | `agent-service/recommendation_agent/` (`server.py`, `agent.py`, `tools.py`); tests in `agent-service/tests/` |
| v1 (random) | `online-boutique/src/recommendationservice/recommendation_server.py`, built as `recommendationservice-v1` |
| Client (frontend) | `online-boutique/src/frontend/rpc.go` and `templates/recommendations.html`, built from source by `catalog/frontend/Dockerfile` |

The generated stubs are produced with each service's own tool version:
- v2: `agent-service/genproto.sh`
- v1: `grpcio-tools` 1.76, matching its protobuf 6 runtime
- frontend: `protoc-gen-go` v1.34.2 and `protoc-gen-go-grpc` v1.5.1
