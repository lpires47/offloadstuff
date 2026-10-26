# Pile / scene photo → itemized listings: tech scope (2026-10-26)

Tags: **[V]** verified against the primary source in this session · **[S]** secondary or vendor-reported · **[U]** unverified, or my own estimate.

## Summary

- **No single model solves piles.** Generic VLM boxes collapse in dense scenes (Qwen2.5-VL-7B: Dense200 F1 1.1; duplicates and boxes swallowing neighbours) ([Rex-Omni](https://arxiv.org/pdf/2510.12798)) [V]. SAM 3 masks are clean and fast but over-segment and miss occluded items ([2512.11884](https://arxiv.org/html/2512.11884v1)) [V]. The robust pattern (GarmentPile++, SAM 3 Agent) is **propose, then verify**.
- **Fix our current bug first.** Our detector asks Claude for boxes on a 0–1000 grid. Anthropic's docs say *"Claude works poorly with normalized coordinates (for example, 0–1000 ranges)"*. Ask for absolute pixels on a pre-resized image instead ([Claude coordinates docs](https://platform.claude.com/docs/en/build-with-claude/vision-coordinates)) [V]. Half-day fix; likely our biggest cheap win [U].
- **v0 (~2 weeks, APIs):** SAM 3 on fal ($0.005/request, [fal](https://fal.ai/models/fal-ai/sam-3/image)) [V] for masks over a fixed vocabulary, in parallel with a Claude pixel-coordinate inventory; fuse by IoU, box-prompt SAM 3 for misses, verify orphans; stream per-item ID from **full-resolution** crops; rule-based "needs photo".
- **v1, own models:** self-hosted SAM 3 or Moondream 3.1 (COCO F1 81.5, Dense200 F1 74.6) ([Moondream](https://moondream.ai/blog/moondream-3-1-beyond-benchmarks)) [S]. Add a fine-tuned Qwen VLM for verify and identify, and DINOv3 embeddings for cross-photo dedupe.
- **Precedent:** Amazon and Pinterest Shop the Look detect → classify → embed per object (§6) [V]. No resale app checked (eBay, Depop, Meta Seller, Minimist, SellRaze, Preloved AI) documents **one photo → many listings**; "bulk" means many uploads. Open ground.
- **UX carries much of the accuracy:** spread-out coaching, tap to split/merge/add, per-item photo requests.

---

## 1. Detection and segmentation options

| Model | Key numbers | Pile relevance | License / access |
|---|---|---|---|
| **SAM 3** (Meta, Nov 2025; **SAM 3.1** Mar 2026) | SA-Co/Gold cgF1 54.1 (human 72.8); LVIS mask AP 48.5; COCO box AP 56.4; 848M params ([repo](https://github.com/facebookresearch/sam3)) [V]. ~30 ms/image at 100+ objects on H200; CountBench 95.6% ([Ultralytics](https://docs.ultralytics.com/models/sam-3)) [S]. | Best masks; short noun phrases only [S]. Dense clutter: **52% of predictions false positives, 79% of misses occluded** ([2512.11884](https://arxiv.org/html/2512.11884v1)) [V]. Alta runs it on 20M+ closet photos; hard cases are white-on-white, blue-on-blue ([Meta/Alta](https://ai.meta.com/blog/alta-daily-fashion-app-segment-anything/)) [V]. | "SAM License": commercial, royalty-free, no MAU cap; bans military/ITAR and reverse engineering; Meta may amend ([LICENSE](https://raw.githubusercontent.com/facebookresearch/sam3/main/LICENSE)) [V]. fal: $0.005/request, ≤32 masks, text+box prompts [V]. |
| **Qwen3-VL** (Apache-2.0) | 8B-Instruct: RefCOCO-avg 89.1, ODinW-13 44.7, CountBench 80.5. 235B: 91.9 / 48.6 / 93.0. Gemini 2.5 Pro: 74.6 / 33.7 / 91.0. Native 0–1000 coordinates ([tech report](https://arxiv.org/pdf/2511.21631)) [V]. | Strong at referring to one thing. ODinW at about 45 shows exhaustive multi-class detection is much weaker. No masks. | Apache-2.0 ([Roboflow catalog](https://playground.roboflow.com/models/feature/foundation-vision)) [S]. |
| **Qwen2.5-VL vs Rex-Omni** | Qwen2.5-VL-7B: COCO F1@0.5 64.0, **Dense200 1.1**. Rex-Omni: 72.0 / 78.4 ([paper](https://arxiv.org/pdf/2510.12798)) [V] | Generic VLMs collapse on dense scenes. Training for dense detection plus GRPO fixes duplicate and oversized boxes [V]. | Research |
| **Moondream 3.1** (9B total, 2B active) | F1@0.5: COCO 81.5 (SAM 3: 77.1), LVIS 67.4, Dense200 74.6, SKU-110K 52.8; detect call about 160 ms; 34 requests/s on one H100 ([blog](https://moondream.ai/blog/moondream-3-1-beyond-benchmarks)) [S, vendor] | Best published dense-scene number from a VLM. Strong candidate for the v1 detector. | Commercial use and self-hosting allowed. You may not resell Moondream as a hosted service [S]. |
| **DINO-X Pro / Grounding DINO 1.5–1.6 Pro** | DINO-X Pro: COCO 56.0, LVIS-minival 59.8, LVIS-val rare 56.5 ([paper](https://arxiv.org/html/2411.14347v2)) [V] | Highest LVIS numbers in this list. | API only [S]. Grounded-SAM-2 wraps it and supports SAHI tiling ([summary](https://www.sourcepulse.org/projects/1854743)) [S]. |
| **YOLOE** | LVIS zero-shot box AP 27.5–35.9; 64 FPS on iPhone 12 ([paper](https://arxiv.org/pdf/2503.07465)) [V] | The only real-time on-phone option. Good for viewfinder hints only. | Not checked; likely AGPL [U] |
| **OWLv2 / Florence-2-L** | OWLv2: LVIS rare AP 44.6 ([NeurIPS](https://proceedings.neurips.cc/paper_files/paper/2023/hash/e6d58fc68c0f3c36ae6e0e64478a69c0-Abstract.html)) [V]. Florence-2-L: COCO 37.5, RefCOCO val 56.3 ([paper](https://ar5iv.labs.arxiv.org/html/2311.06242)) [V]. | Both superseded by SAM 3 here. | Apache-2.0 / MIT [S] |
| **Gemini 3.x / 4** | Returns `box_2d` as [ymin,xmin,ymax,xmax] on a 0–1000 grid, plus polygon masks; set thinking to "minimal" for segmentation ([docs](https://ai.google.dev/gemini-api/docs/image-understanding)) [V]. On Roboflow's evals, Gemini 4 Argon leads detection: mAP@50 82.5, $0.0058 per sample, about 13 s ([evals](https://playground.roboflow.com/evals)) [S]. | The only frontier API that returns both boxes and masks in one call. | API |
| **Claude** | Roboflow evals, mAP@50: Opus 5.5 74.5 and Sonnet 5.5 74.3; counting 80.6 and 79.3; about 8 s and $0.007–0.015 per sample [S]. Anthropic: localization is "approximate". The high-resolution tier (Claude 4.7+) allows 2,576 px and 4,784 tokens ([vision docs](https://platform.claude.com/docs/en/build-with-claude/vision)) [V]. | Good at inventory and reasoning: what is for sale, pairs, background. Not pixel-precise. | API |

**Benchmark gaps.** No public garment-heap instance benchmark found. Robotics pile work (GarmentPile++) reports SAM2 **merging same-colour garments, fragmenting one garment, ragged boundaries**, fixed by VLM-guided mask adjustment ([2603.04158](https://arxiv.org/html/2603.04158)) [V]. DeepFashion2 (491K images, 13 categories) is worn/street photos, not heaps ([paper](https://ar5iv.arxiv.org/html/1901.07973)) [V]. No ADE20K furniture numbers collected; proxy is Amazon STL home localization, 85–91% recall [V]. **Our own eval set decides** (§5).

## 2. Failure modes specific to piles, and mitigations

| Failure | Evidence | Mitigation |
|---|---|---|
| Same-colour garments **merged** into one instance | GarmentPile++ [V]; VLMs draw one large box over several neighbours: 20.5% of SFT predictions on Dense200 ([Rex-Omni](https://arxiv.org/pdf/2510.12798)) [V] | (a) Run SAM 3 per concept ("t-shirt", "jeans", ...) instead of "clothes". (b) VLM verify step: "how many distinct garments are in this crop?" If more than one, re-prompt SAM 3 with points. (c) UX: tap to split. |
| One garment **split** into several masks (a sleeve sticking out, two-tone dresses) | GarmentPile++ [V]; Amazon STL lists two-tone dresses split into two garments [V] | Merge masks of the same colour and texture whose union forms one plausible garment (VLM judges a crop of the union). UX: drag to merge. |
| Items **hidden underneath** | 79% of SAM 3's misses were occluded ([2512.11884](https://arxiv.org/html/2512.11884v1)) [V] | Treat a single heap photo as a *partial* inventory. Prompt the user: "We found 9. Spread them out or take another angle." Mark low-visibility items "needs photo". |
| **Pairs** (shoes, earrings, gloves) | Detectors count each shoe; Amazon STL notes small footwear fails [V] | Post-process: group same-category instances by embedding similarity, proximity and left/right mirroring. Confirm with one VLM yes/no. List as one item with "pair: yes / single?" |
| **Background** (bed, duvet, hangers, rug, wall art in room shots) | Alta names hangers and the person in frame [V] | The VLM inventory labels `is_for_sale_candidate` (our schema already has this). In room scenes, ask "selling the furniture too?" once. Apply a negative concept list. |
| **Tiny items** (jewelry, sunglasses, belts) | VLM box accuracy on small COCO objects is about 42% vs 76% for YOLO ([2510.11302](https://arxiv.org/pdf/2510.11302)) [S]; SAHI tiling with 25% overlap and NMS adds +5–7 AP on small objects ([SAHI](https://ar5iv.arxiv.org/html/2202.06934)) [V] | Run a second detection pass on 2×2 tiles of the full-resolution image (on a crowded flat surface or when an item's box is under 3% of the frame). The Claude zoom-tool pattern took chart-reading accuracy from 29% to 73% ([cookbook](https://platform.claude.com/cookbook/multimodal-crop-tool)) [V]. |
| **Duplicates** across passes or tiles | MLLM duplicate boxes ([Rex-Omni](https://arxiv.org/pdf/2510.12798)) [V] | Mask-IoU NMS at 0.5, plus suppression by box containment, which works better than plain IoU for nested items. |
| **Same item in two photos** | — | Embedding match (§3). |

## 3. Per-item identification from a crop

- **Crop from the original.** We load at max_edge 2048 (`images.py:load_photo`) and crop that; a 12 MP frame (~4032×3024) gives ~2× linear pixels per crop.
- **Input budgets:** Claude high-res tier 2,576 px / 4,784 tokens; <200 px images degrade ([docs](https://platform.claude.com/docs/en/build-with-claude/vision)) [V]. Gemini 3 `media_resolution` ≤1,120 tokens, 2,240 ULTRA_HIGH per part ([docs](https://ai.google.dev/gemini-api/docs/generate-content/media-resolution)) [V].
- **Tag legibility:** Tesseract wants **x-height ≥ 20 px** ([iDigBio](https://www.idigbio.org/node/106)) [S]; assume similar for VLMs [U]. Size/wash tags are unreadable in whole-pile shots. Upscaling (`min_edge=512`) helps patching but adds no information [U].
- **Ask for a close-up when:** crop long edge in the original < ~400 px; label reported unreadable; required field (brand/model/size) below its floor (`pipeline.py` has these); item < 40% visible; value category needing authenticity; brand guess contradicts visible text.
- **Cross-photo association:** embed mask crops, Hungarian-match above a threshold, VLM-confirm borderline pairs. DINOv3 leads instance retrieval (Met GAP 55.4 vs DINOv2 44.6, SigLIP2 13.9) ([DINOv3](https://arxiv.org/pdf/2508.10104)) [V]; see also `docs/research/vision.md`.

## 4. Latency and cost

| Step | Time | Cost |
|---|---|---|
| Phone downscale to about 2,560 px and upload | 0.5–2 s on LTE [U] | — |
| SAM 3, self-hosted | ~30 ms per image at 100+ objects on H200 [S]. Each extra concept prompt reuses the image embedding [U]. On an L4 or A10G, expect a few hundred ms [U]. | GPU at about $1–2/h [U] |
| SAM 3 on fal | ~1–3 s including queueing [U] | $0.005 per request [V]. Up to 32 masks per request, so large piles need several prompts. |
| Claude Sonnet 5.5 inventory pass (one image, about 4k tokens in, 1–2k out) | ~5–8 s [S: about 8 s average per sample on Roboflow] | about $0.02 [U, from $2/$10 per M tokens via Roboflow] |
| Gemini Flash-class detection | ~11–13 s on Roboflow's harness (thinking included) [S]. With minimal thinking: ~2–4 s [U]. | $0.003–0.006 [S] |
| Moondream 3.1, self-hosted | ~160 ms per detect [S] | — |
| Qwen3-VL-8B, self-hosted | About 3.8 images/s on H100 and 2.1 on A100 at batch with 1,024 px images; 17 GB in FP16 ([Spheron](https://www.spheron.network/blog/deploy-vision-language-models-gpu-cloud)) [S]. One request emitting 30 boxes (~600 tokens) takes ~4–5 s [U]. | — |
| Per-item identification (Claude, crop plus overview) | 3–8 s each, run in parallel [U] | ~$0.01 each [U] |
| On device: YOLOE-S | 64–73 FPS on iPhone 12 [V] | free |

**Streaming:** t≈1–3 s SAM 3 outlines with generic labels → t≈5–8 s VLM inventory fills labels, greys background, adds misses → t≈8–15 s identity cards one by one. Replace `pool.map` in `analyze_photo` (blocks until all items finish) with `as_completed` over SSE; largest/clearest items first.

**On-device** only for viewfinder hints (YOLOE). EfficientSAM3 (0.7–21M params) has **no results yet** ([2511.15833](https://arxiv.org/html/2511.15833v1)) [V].

## 5. Evaluation

**Metrics:** item recall (mask IoU ≥ 0.5; 0.3 relaxed for occluded) · precision on sellable items · **merge rate** (prediction covers ≥2 GT items >50% each) · **split rate** (GT covered by ≥2 predictions) · pair accuracy · background FP rate · per-item exact match on category/brand/size, judged model/style, listable-without-edit rate · "needs photo" flag precision/recall vs actual ID errors · time to first box / full list / last identity (p50, p90) · cost per photo.

**Eval set:**

- **100 photos**, 5 strata × 20: bed heap, folded stack/shelf, shoes and accessories on floor, hanging rail, room corner. ~8 items each ≈ 800 items → recall 95% CI ≈ ±3% overall, ±6–7% per stratum (binomial, p≈0.8) [U].
- Plus 20 spread-vs-heaped pairs of the same items (measures UX value) and 15 two-photo sets (dedupe).
- Label with SAM 3 assist plus human correction, done in-house. Pinterest measured expert labelers at 89.5% accuracy vs 32.5% on MTurk ([STL](https://arxiv.org/pdf/2006.10866)) [V]. Budget 2–3 labeler-days [U].
- Use real closets, not stock photos. Extend `evals/labels.example.yaml` and `evals.py` with masks and per-item matching.

## 6. Production precedent

- **Amazon Shop the Look** ([paper](https://cdn.amazon.science/2a/43/43c7dd6b4bffbfe72de627456a76/amazon-shop-the-look-a-visual-search-system-for-fashion-and-home.pdf)) [V]: separate fashion and home YOLOv3 detectors, then a fine-category classifier, an embedding, and per-category ANN search. Localization takes 127 ms. Training on out-of-distribution negatives cut false positives from 77.7% to 4.8%. Failures: small shoes and bags, occlusion, two-tone dresses.
- **Pinterest STL** ([paper](https://arxiv.org/pdf/2006.10866)) [V]: detect, show tappable dots, embed. Scene recall rose only from 0.31 to 0.53, so production systems still miss many items in scenes.
- **One item per photo only:** eBay bulk listing, where the seller sets "photos per draft" ([eBay](https://ebay.co.uk/sellercentre/news/2025-january/ai-bulk-listings)) [V]. Also Depop ([TNW](https://thenextweb.com/news/depop-ai-generates-listings-from-one-photo)), Meta Seller ([AH](https://www.androidheadlines.com/2026/07/meta-ai-powered-seller-app-facebook-marketplace.html)), Minimist ([App Store](https://apps.apple.com/app/id6633428597)), SellRaze ([YC](https://www.ycombinator.com/launches/OhK-sellraze-sell-your-stuff-in-seconds)) and Preloved AI ([App Store](https://apps.apple.com/app/id6749449859)) [S].
- **ThredUp:** $400M+ invested in automation, but no public technical detail ([LDS](https://letsdatascience.com/news/ai-turns-thrift-into-profitable-fashion-marketplace-81e30183)) [S]. **Google Lens** multi-object: no paper found [U].

---

## 7. Scope

### v0: APIs, about 2 weeks

1. **Capture:** the phone uploads a ~2,560 px JPEG immediately, then the full-resolution original in the background.
2. **Pass A, masks:** SAM 3 on fal, called in parallel for a garment vocabulary (top, shirt, sweater, jacket, dress, skirt, pants, jeans, shorts, shoe, boot, sneaker, bag, hat, scarf, belt, jewelry) and a room vocabulary (chair, table, lamp, sofa, shelf, mirror, vase, rug, frame). Stream the outlines.
3. **Pass B, inventory:** Claude with **pixel coordinates on the exact resized image we send** (use the `resized_size` helper). Returns label, is_for_sale, pair_of, visibility, and a pixel box.
4. **Fuse:**
   - Match pass A and pass B by IoU and containment.
   - B boxes with no mask → SAM 3 box prompt.
   - A masks with no B match → Claude yes/no verify on the crop.
   - Then mask NMS and pair grouping.
5. **Tiling (conditional):** 2×2 tiles with 25% overlap when the scene is a flat lay or shelf, or when any item covers under 3% of the frame.
6. **Identify:** run existing `identify_item` on crops of the **original** plus the outlined overview. Stream results with `as_completed`.
7. **Readiness:** the existing `assess()` rules, plus the crop-pixel rule and the visibility rule, produce photo requests.
8. **Cross-photo:** in v0, use the VLM pairwise check on same-category candidates. Defer embeddings to v1.

Fallback if SAM 3 or fal is down: Gemini boxes plus masks in one call.

### v1: own models, about 2–3 months

- **Detector:** self-hosted SAM 3 or 3.1, or Moondream 3.1, fine-tuned on our labelled piles. Both allow commercial use [V/S]. Benchmark both on our eval set.
- **Verify and identify:** fine-tuned Qwen3-VL-8B. Also check newer Qwen3.5/3.8 small models, which Moondream cites as Qwen3.5 9B, and confirm their license [U].
- **Dedupe:** DINOv3 embeddings (check the license [U]) plus pgvector.
- **Viewfinder:** YOLOE on device for live "spread out" and "move closer" hints.

### Components

Capture client · original-keeping upload · SAM 3 client · pixel-coordinate inventory schema · fusion (IoU/containment, NMS, pairs) · tiler · original-resolution crop service · identifier (exists) · readiness rules (exists, extend) · SSE stream · cross-photo matcher · correction-event logging · mask eval harness.

### Requirements (proposed targets) [U]

| Requirement | v0 target | v1 target |
|---|---|---|
| Item recall, spread-out scenes | ≥ 90% | ≥ 95% |
| Item recall, heaps (visible items) | ≥ 75% | ≥ 85% |
| Precision (sellable items) | ≥ 85% | ≥ 92% |
| Merge rate / split rate | ≤ 10% / ≤ 10% | ≤ 5% / ≤ 5% |
| Pair grouping accuracy | ≥ 90% | ≥ 97% |
| Category correct | ≥ 95% | ≥ 97% |
| Brand correct when visible | ≥ 85% | ≥ 92% |
| "Needs photo" flag recall on wrong identifications | ≥ 80% | ≥ 90% |
| Time to first box, p50 / p90 | ≤ 3 s / ≤ 5 s | ≤ 1.5 s / ≤ 3 s |
| Full item list, p50 / p90 | ≤ 8 s / ≤ 15 s | ≤ 5 s / ≤ 10 s |
| Last identity, 10 items, p90 | ≤ 25 s | ≤ 15 s |
| Cost per pile photo (10 items) | ≤ $0.20 | ≤ $0.03 |

### Data and eval needs

- The 100-photo stratified set (§5), labelled within week 1. It gates v0 launch.
- Log every user split, merge, add and delete as weak labels for v1 fine-tuning.
- Collect about 2k labelled pile images before fine-tuning a detector [U].

### Risks

1. **Hidden items in heaps can't be found.** Promise "visible items" and lean on re-shoot UX.
2. **Same-colour merging** is the likely top error. Needs the verify pass and split UX.
3. **Latency stacking** across two API passes and N identifications. Parallelize, stream, and time-budget each call.
4. **Coordinate drift** from resize or padding mismatches. Use pixels on a pre-resized image [V].
5. **License drift:** Meta can modify the SAM License [V]; Moondream bars hosted resale [S].
6. **Vendor benchmarks** may not transfer. Our eval decides.
7. **Cost on 30+ item rooms.** Identify the top N and the rest when tapped.

### UX the product must provide

- **Coaching:** "Spread out, no overlap, contrasting surface, good light, shoot from above"; live YOLOE hint where available.
- **Overlay:** numbered outlines; tap to deselect; **tap-hold to split** (SAM 3 point re-prompt); **drag to merge**; **tap empty space to add**.
- **Pair chip** (shoes, earrings): "Pair ✓ / Single".
- **Per-item photo requests** with reason and target ("Tag inside collar: size and brand"); new shots auto-associate.
- **"Found 9 visible items. Anything underneath?"** one-tap re-shoot, merged via dedupe.
- **Progressive disclosure** so the screen is never blank for more than ~3 s.

*Blocked during research: docs.claude.com vision page (the platform.claude.com mirror was used instead), arxiv abs pages for Florence-2 and OWLv2 (alternate mirrors used), and the GitHub page for Grounded-SAM-2 (a secondary summary was used).*
