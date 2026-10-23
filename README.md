# Offload engine

Photo in, money out. This repo is the engine behind the app: it identifies what's in a photo,
drafts an honest listing, negotiates inside the seller's hidden minimum, and operates the user's own
marketplace accounts to post and sell.

Status: first build (Oct 2026). Everything runs and is tested offline with recorded model responses.
Real runs need an Anthropic API key. Platform adapters have not been run against live sites yet.

## What's here

| Area | Code | What it does |
| --- | --- | --- |
| Image understanding | `src/offload/vision/` | One photo of an item or a pile. A cheap model finds the items; the best vision model identifies each (brand, model, size, gender, colors, material, condition, flaws, dimensions, authenticity risk), with a confidence and the visual evidence per field. Code, not the model, decides what's ready to list and which single extra shot to ask for. |
| Listing | `src/offload/listing/` | Builds title and description only from confident fields; shipping tier from estimated size and weight. The hidden minimum never leaves the draft (`public_view()` omits it). |
| Pricing | `src/offload/pricing/` | Price from matched *sold* comps (quantiles by speed: get the most / balanced / gone this week), condition-adjusted. Falls back to retail × condition when comps are thin. Comp sources plug in later. |
| Negotiation | `src/offload/negotiation/` | Deterministic policy: accept, counter (conceding toward the offer, never below the minimum, never back up), ask the seller (just under the minimum), or decline (lowballs, scams). Cross-platform arbiter ranks offers by what the seller takes home after fees. Price-drop schedule sized to trigger platforms' buyer notifications. Scam guard on buyer messages; the model only phrases replies, and every reply is checked. |
| Acting as the user | `src/offload/posting/browser/` | Claude computer use (`computer_toolset_20260801`) drives a browser logged in as the user (their cookies, never their password). Tasks: create listing, update price, delist, read inbox, respond to offer, buy. Guardrails in code: domain allowlist, step and time budgets, `ask_user` approval for consequential steps, screenshot trimming, page content treated as untrusted. |
| eBay | `src/offload/posting/ebay.py` | Official Sell APIs where they exist: Inventory (create, price, withdraw), Best Offer thresholds at listing time, Trading API to read and answer offers, Negotiation API for offers to watchers. Written from eBay docs; **not yet run against the sandbox**. |
| Orchestration | `src/offload/orchestrator.py` | One item across platforms: post, negotiate, confirm sale with the seller, delist everywhere else. |
| Evals | `src/offload/evals.py`, `evals/` | Per-field accuracy and calibration of identification on labeled photos. |

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
playwright install chromium        # skip if Chromium is already provided
cp .env.example .env               # add ANTHROPIC_API_KEY
export $(grep -v '^#' .env | xargs)
pytest                             # runs offline
```

## Try it

```bash
offload simulate                                   # multi-platform negotiation, no network
offload identify photo.jpg                         # identify one item or a pile
offload identify hoody.jpg --extra tag.jpg --retail 250   # + extra shot, + a draft listing
offload label-draft evals/photos --out evals/labels.yaml  # pre-fill labels, then correct them
offload eval evals/labels.yaml                     # accuracy report
offload login --user liselle --platform depop      # sign in once; the session is saved locally
```

## Labeling photos (the next step)

1. Put 20 to 50 photos in `evals/photos/`: single items of different kinds, a few piles, a few hard
   ones (no visible logo, similar models from one brand, worn items).
2. `offload label-draft evals/photos --out evals/labels.yaml`.
3. Correct every field in `evals/labels.yaml` against the real item (tags in hand). Leave unknowns out.
4. `offload eval evals/labels.yaml` and read `evals/runs/<time>/report.md`.

Photos and labels are git-ignored by default. Commit them deliberately if you want them shared.

## Known gaps

- Comp sources (eBay sold data, platform search) aren't connected; prices use the retail fallback.
- Browser task start URLs and flows per platform need checking against the live sites.
- eBay adapter needs a sandbox run, business policies, and hosted image URLs.
- Platform terms: eBay bans unapproved buying agents and "end-to-end flows... without human review";
  most platforms ban automation in general. Keep the user's sign-off on listing, sale and purchase,
  and get legal review before launch.
