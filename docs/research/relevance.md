# Search relevance for cross-platform secondhand search: research + recommended stack

Prepared 2026-10-23. Scope: retrieval architecture, relevance evaluation, taste/personalization, learning from behavior, LLM reranking latency and cost, and a recommended stack and eval program for a startup indexing secondhand listings from every platform. It covers text queries ("90s Prada nylon shoulder bag, black, under $300") and photo queries (a picture of a chair).

**How to read the evidence.** Numbers come from papers and engineering posts read through WebFetch summaries. Most come from the primary source. Items marked **[unverified]** came from a secondary aggregator, a vendor's own benchmark, a figure not in the text, or my own calculation, and should be checked before you quote them externally. Items marked **[estimate]** are my back-of-envelope numbers.

---

## TL;DR

1. **Everyone serious runs a hybrid cascade.** The pattern is lexical plus dense (and image) retrieval, a cheap first-pass ranker, then a cross-encoder or distilled relevance model. LLMs and VLMs are almost never in the online hot path at scale. They label offline, teach smaller models, and cache answers for head queries. Etsy, Pinterest, Walmart, Instacart, Alibaba and Amazon all follow the pattern "frontier LLM → fine-tuned mid-size teacher → small student online."
2. **For product identity, image beats text.** Zalando's cross-seller product matcher: image-only CLIP plus a projection reached 57.2 AUCPR, text-only about 0.6, and the fused model 66.1 AUCPR with R@1 84%. Generic image encoders do poorly on fashion "exact item" retrieval: CLIP-L about 40% fine R@1 on LookBench, fashion-tuned SigLIP about 63%, and the best proprietary model 67%. Street photos are the hardest case.
3. **LLM judges are good enough to scale evaluation but not to replace a human gold set.** System-ranking correlation with humans is high (Kendall τ about 0.9). Per-label agreement is moderate: κ about 0.3–0.6 on TREC, quadratic κ 0.52–0.73 at Allegro. In fashion, Zalando's multimodal judge agreed with humans (65%) more often than humans agreed with each other (60%). The risks are circularity and self-preference, when the judge resembles the ranker.
4. **Distilling LLM labels into small rerankers gives consistent, modest online gains.** Reported lifts are roughly +1–4% on relevance or fulfillment metrics and +2–4% AUC offline, with students running in under 10 ms. Behavior-only training is noisy. Walmart downgraded about 33% of engagement "positives", and Baidu found click-trained ULTR models failed to beat BM25 on expert labels.
5. **For us, the moat is the product-identity layer and the eval set.** Nobody publishes cross-platform resale entity resolution, era or authenticity attributes, or aesthetic-intent judging. The stack below is built around (a) canonical-product matching for exact intent and (b) style embeddings plus pairwise judgments for aesthetic intent, with separate metrics for each.

---

## 1. Retrieval architecture: best practice and published systems

### 1.1 Hybrid lexical + dense retrieval

- **Amazon, Semantic Product Search (KDD 2019).** A Siamese model with average-pooled word unigrams, bigrams and character trigrams, using a 3-part hinge loss over purchased, impressed-not-purchased and random items. Recall@100 0.735 vs DSSM 0.702, MAP 0.664 vs 0.580. It was deployed to augment the lexical match set, not replace it, and Amazon notes that precision required extra heuristics and ranking filters. Target: under 20 ms at thousands of QPS. https://ar5iv.labs.arxiv.org/html/1907.00937
- **Etsy, Unified Embedding Personalized Retrieval (KDD 2023).** A two-tower model. The product tower combines a T5 encoder pretrained to generate purchased queries from listing text, a query-product bipartite-graph embedding, n-gram, category and attribute token embeddings, and location. The query tower adds user history through a 1-layer transformer (+2% recall). Results:
  - Purchase Recall@100: BM25 0.55, base two-tower 0.33, UEPPR 0.674, UEPPR with quality boost 0.708.
  - Removing hard negatives cost about 7% of recall@100.
  - Online: **+2.63% site conversion, +5.58% organic search purchase rate.**
  - Serving: p99 18 ms. HNSW lost more than 10% recall at K=1000. A 4-bit IVFPQ index with 5×K re-ranking kept recall loss under 4% at p99 under 20 ms.
  - https://arxiv.org/html/2306.04833v2
- **Walmart, Enhancing Relevance of EBR (2024).** EBR runs alongside lexical retrieval. A BERT cross-encoder "relevance reward model" (exact / substitute / irrelevant) revises engagement labels: about 3% of pairs were downgraded to 0.1 and about 30% to 0.01. Other changes: typo injection, hard negatives filtered by product type and token overlap, and a multi-objective loss.
  - Offline: EM Precision@20 +14.65%, EM Recall@20 +16.49%.
  - Online: NDCG@5 +1.64% (label revision), revenue +0.31% then +0.43% for later stages.
  - https://arxiv.org/html/2408.04884v2
- **Fusion method.** On BEIR, OpenSearch found score-normalized hybrid beats BM25 on 5 of 6 datasets, and RRF scored about 3.9% lower than normalized-score fusion. Neither dense nor BM25 dominates everywhere. No e-commerce benchmark was included. https://opensearch.org/blog/introducing-reciprocal-rank-fusion-hybrid-search/
- **Takeaway.** Keep BM25 over *normalized* fields (brand, model, material, era, color) plus raw titles. Brand and model tokens ("Re-Edition 2000", "Cesca", "Tessuto") are where lexical retrieval wins. Fuse with dense and image ANN. Tune the fusion on our own judged set rather than assuming RRF.

### 1.2 Multimodal / image embeddings

- **Pinterest, OmniSearchSage (WWW 2024).** One query embedding shared across pins, products and queries. Training pairs: 1.5B query-pin, 136M query-product, and 2.5M offsite add-to-cart/checkout pairs. Product-side text was enriched with:
  - BLIP captions for the about 30% of pins with no usable text (88% judged high quality). Captions raised save recall@10 on text-less pins from 0.51 to 0.66.
  - Board titles (+17% save recall).
  - Engaged queries (+7%).
  - Results: product save recall@10 went from 0.57 to 0.73. Online: **+7.4% search fulfillment, +3.5% relevance.** Serving: 300k rps at p50 3 ms, with a 30-day cache TTL that cuts inference to about 500 QPS.
  - Lesson for us: our vision normalization (captions and attributes) is exactly the "content enrichment" that drove most of the gains.
  - https://arxiv.org/pdf/2404.16260
- **Pinterest, Shop The Look.** Detect objects in a scene, crop, embed, then nearest-neighbor search *within the predicted category*. Per-category indexes cut "Bad" top-5 results by 17.1%. Cumulative results: more than 160% improvement in human-judged end-to-end relevance and more than 80% in engagement. In-house labelers reached 89.5% accuracy vs 32.5% for MTurk, which argues for trained labelers over crowd. https://ar5iv.labs.arxiv.org/html/2006.10866
- **Etsy visual search (2024).** Multitask training on top-level taxonomy, 1,000 leaf categories, primary color, and **buyer review photos** (to bridge the studio-to-real-photo gap). EfficientFormer-l3 beat EfficientNetB0: Recall@5 on review-photo queries about +17%. Online: +8% click-recall@100 in ads retrieval. https://www.etsy.com/codeascraft/efficient-visual-representation-learning-and-evaluation
- **eBay multimodal item embeddings (2023).** BERT text plus ResNet-50 image embeddings in a co-click Siamese model, aligned with triplet loss and TransH, plus an image-title *mismatch* detector. Online: up to **+15.9% CTR, +31.5% purchase-through rate**. The mismatch module is directly relevant to messy resale listings. https://innovation.ebayinc.com/stories/beyond-words-how-multimodal-embeddings-elevate-ebays-product-recommendations/
- **Zalando fashionID (2024), cross-seller product matching.** Frozen CLIP image and text encoders plus numeric features feed a 192-dimensional contrastive projection, followed by ANN restricted to similar brands and a distance threshold.
  - AUCPR 66.1, R@1 84.2%, R@3 95.2%. Image-only scored 57.2 AUCPR and text-only about 0.6.
  - CLIP beat DINOv2 (57.2 vs 38.1).
  - With expert validators in the loop, output precision reached 93.7%. Crowd workers could not reach the 90% precision target.
  - https://arxiv.org/pdf/2403.11593
- **Encoder choices (2025–2026).**
  - SigLIP 2, B/16: COCO text→image R@1 53.2 vs SigLIP 47.4; CLIP L/14 36.5. https://arxiv.org/pdf/2502.14786
  - Marqo-FashionSigLIP: text→image avg recall 0.231 vs FashionCLIP2.0 0.163, across 7 fashion datasets. https://github.com/marqo-ai/marqo-FashionCLIP
  - Qwen3-VL-Embedding and Reranker (2B and 8B; text, image and video; Matryoshka embeddings; 77.8 on MMEB-V2). https://arxiv.org/abs/2601.04720v1
- **LookBench (2026), live fashion image-retrieval benchmark.** Fine Recall@1 requires category *and all attributes* to match:

  | Model | Overall | RealStreetLook | RealStudioFlat |
  |---|---|---|---|
  | GR-Pro (best, proprietary) | 67.4% | 62.4% | — |
  | Marqo-FashionSigLIP | 62.8% | — | — |
  | SigLIP2-B | 59.4% | — | — |
  | DINOv2-G | 41.5% | — | — |
  | CLIP-L/14 | 39.8% | — | — |

  Gains plateau beyond about 6.5M training images, and moving the backbone from 0.3B to 0.8B parameters adds almost nothing. Domain data matters more than model size. https://arxiv.org/pdf/2601.14706
- **Fine-grained verification.** PRISM (SigLIP top-35, then segmentation, then LightGlue keypoint matching) raised Top-1 from 38.6% to 42.8%, at 725 ms vs 21.7 ms per query. Expensive identity verification is affordable only on a short list. https://arxiv.org/pdf/2509.14985
- **Alibaba Pailitao-MMSearch (2026).** A Qwen-based native multimodal search model with hybrid semantic IDs, deployed on Taobao photo search. Online: +13.61% GMV on one floor, +1.02% GMV across Pailitao from retrieval alone. It names a failure mode we will face: the system matches the dress in the photo but ignores the text "I want a jumpsuit." https://www.alphaxiv.org/abs/2607.17499
- **Google.** The Shopping Graph holds more than 50B listings, with about 2B refreshed every hour. AI Mode "visual search fan-out" runs multiple background queries over the main and secondary objects in an image. https://blog.google/products/search/search-ai-updates-september-2025/
- **Shopify.** Streaming text and image embeddings on Dataflow with T4 GPUs, about 2,500 embeddings per second (about 216M per day), for near-real-time freshness. Model names are not disclosed. https://shopify.engineering/how-shopify-improved-consumer-search-intent-with-real-time-ml
- **ThredUp (resale).** Launched image search, natural-language search and an outfit "Style Chat" over more than 4M items in August 2024. No technical details are published. https://www.mannpublications.com/fashionmannuscript/2024/08/05/thredup-launches-suite-of-ai-shopping-features/
- **No technical publications found** for Faire, Lyst, Vinted, Depop, Poshmark or The RealReal search. That is a gap and a chance to publish first.

### 1.3 Query understanding (attribute extraction, spelling, taxonomy, rewriting)

- **Instacart Intent Engine (2025).** Covers category classification, three rewrite types (substitute, broader, synonym) and semantic role labeling (product, brand, attributes).
  - Head queries: an offline frontier-LLM teacher with RAG over conversion history, written to a cache.
  - Tail queries: a real-time Llama-3-8B LoRA student, about 300 ms after merging adapters and moving to H100s (700 ms out of the box). FP8 quantization was rejected because it cost recall.
  - Only about 2% of queries need real-time inference.
  - Student quality matched the large model (precision 96.4%, recall 95%).
  - Rewrite coverage rose from 50% to more than 95% of traffic at 90%+ precision.
  - Online: −6% scroll depth and −50% complaints about tail-query results.
  - https://tech.instacart.com/building-the-intent-engine-how-instacart-is-revamping-query-understanding-with-llms-3ac8051ae7ac
- **Taobao BEQUE (2023/24).** LLM long-tail query rewriting: multi-instruction SFT, then offline feedback from the retrieval system, then contrastive alignment. Significant online GMV, transaction and UV gains on long-tail queries; deployed since October 2023. https://astro.paperswithcode.com/paper/large-language-model-based-long-tail-query
- **Amazon hint-augmented reranking (2025).** For superlative queries ("best X"), Claude 3.5 Sonnet generates offline "hints" (brands, features, rewrites). These feed BM25 and a small 0.5B or 3B pointwise reranker. The 3B model with hints reached P@1 64.4, vs 44.4 for DeepSeek-R1 listwise and 35.3 for Qwen2.5-72B listwise, at about 14× less compute. **Offline LLM enrichment plus a small online model beat online large-LLM listwise reranking.** https://arxiv.org/pdf/2511.13994
- **RL-based rewriting with a distilled LLM (UIUC, 2025).** Simulated-user reward gives modest gains. Academic only. https://arxiv.org/pdf/2501.18056
- **Attribute extraction quality.** ExtractGPT: few-shot GPT-4 averages 84.9 F1 vs 79.8 for the best fine-tuned PLM, and does much better on unseen values (72.6 vs 53.2). Llama-3-70B is close to GPT-4. Zero-shot is much worse (about 62–69 F1). Supply in-domain examples. https://arxiv.org/abs/2310.12537
- **Zalando's judge pipeline.** The LLM first turns each query into a **requirement list with importance levels** (e.g., `must_have`) and a **specificity rating**. This is effectively query parsing plus intent classification, reused for evaluation. https://arxiv.org/html/2409.11860v1

### 1.4 Two-stage retrieve → rerank

- Standard depth is about 1,000 candidates, then a light ranker down to about 200, then a cross-encoder down to 20–50, then an optional LLM/VLM stage.
- **Cross-encoder baseline.** On ESCI Task 1, a fine-tuned cross-encoder reached nDCG 0.852 vs 0.563 for BM25 with default settings. https://ar5iv.arxiv.org/html/2206.06588
- **LLM listwise rerankers** (RankZephyr, FIRST): BEIR nDCG@10 about 54. FIRST decodes only the first token, which cuts latency about 50% at equal or better quality. https://arxiv.org/html/2406.15657v1 , https://arxiv.org/html/2411.05508v2
- **VLM rerankers.** Qwen3-VL-Reranker (2B, 8B) is an off-the-shelf multimodal cross-encoder. Etsy fine-tuned Qwen3-VL-4B as its relevance teacher (see §4).

### 1.5 Constraint filtering

- Treat price, size, condition, category, and "ships to / currency" as **hard filters applied before ranking**, using the *normalized* values.
  - Walmart and Pinterest both found that restricting by predicted product type or category in retrieval sharply cuts bad results (Shop The Look: −17.1% Bad@5).
  - Zalando's LLM judge most often hallucinated on **size** queries.
- For resale specifically: keep both the "claimed" and the "observed" value. A listing titled "M" whose measurements say "L" should match "L" queries, with a lower confidence score. Expose a confidence score per normalized attribute so ranking can soften hard filters when confidence is low.

### 1.6 "Exact item" vs "similar style" intents

- ESCI's label scheme encodes the distinction: Exact / Substitute / Complement / Irrelevant, with nDCG gains of 1.0 / 0.1 / 0.01 / 0. Human agreement was 91% on the 4 classes and 96% on Exact vs not-Exact. Graders were lenient on Substitute. https://ar5iv.arxiv.org/html/2206.06588
- Allegro's 5-class extension (Exact, Highly substitutable, Substitutable, Complementary, Irrelevant): judge F1 0.94 on Exact but only 0.33–0.51 on the substitute classes. The "similar" end is the hard part to judge. https://blog.allegro.tech/2026/08/automating-search-relevance-llm-as-a-judge.html
- Pinterest Shop The Look rates results "Extremely Similar / Similar / Bad", separating exact visual matches from style matches.
- **Implication.** Classify intent up front, with an explicit specificity score in the query parse, as Zalando does:
  - **Exact model**: a named model, or a photo of an identifiable item.
  - **Spec**: attribute-constrained ("90s Prada nylon shoulder bag black <$300").
  - **Aesthetic or vibe**: "quiet-luxury camel coat", "Memphis-style lamp".
  
  Each intent uses different retrieval weights, metrics, and UI sections: "Exact matches" vs "Similar style".

---

## 2. Relevance evaluation

### 2.1 Building judgment sets

- **Graded scales in use:**
  - ESCI: 4-class, at least 3 annotators, majority vote.
  - Etsy: 3-class (Relevant / Partially / Irrelevant). Two internal admins per pair, tie-break review, guidelines updated as intent drifts (e.g., "face masks" after 2020). https://www.etsy.com/codeascraft/how-etsy-uses-llms-to-improve-search-relevance
  - Pinterest: 5-point scale, 3 raters, soft labels, 281k training pairs. https://arxiv.org/html/2410.17152v1
  - Allegro: 5 classes plus "Hard to say". Two blind annotators plus an expert arbitrator, about 30 experts, more than 380k pairs.
  - Walmart: 3-point (exact / substitute / irrelevant), judged from the full product page *including the image*.
- **Sampling.** Etsy uses random stratified sampling plus targeted hard cases. Zalando uses 500 queries per language × 20 products = 10k pairs per language, stratified by NER-tag segment.
- **Expert labelers over crowd.** Pinterest in-house labelers reached 89.5% accuracy vs 32.5% for MTurk. Zalando fashionID found crowd workers could not reach 90% precision even with 5 votes.
- **Human cost [unverified].** Walmart estimates $0.50–1.00 per pair and 2–3 minutes per pair for humans, vs $0.001–0.002 and 1–5 seconds for an LLM. https://www.alphaxiv.org/overview/2502.15990

### 2.2 LLM-as-judge: agreement and cost

| Study | Setting | Agreement |
|---|---|---|
| Thomas et al., Bing (2023) | TREC-Robust | κ rose from 0.38 (basic prompt) to **0.60** when the prompt asked for aspect sub-scores (topicality, trust) first. Asking the model to "simulate multiple judges" *hurt* (κ 0.22). The paper claims LLMs beat several crowd populations against first-party truth. https://arxiv.org/html/2309.10621v3 |
| UMBRELA (GPT-4o) | TREC DL 2019–23 | System-ranking Kendall τ about 0.8–0.9 [abstract-level]. Binary κ 0.418 on DL23 vs GPT-4o; Llama-3.3-70B τ 0.946, κ 0.391; Llama-3-8B κ 0.315. Rank correlation stays high for small models while per-label agreement drops. https://arxiv.org/html/2507.09483v1 |
| Critique of LLM judging | TREC 2024 RAG | Overall τ 0.89, but the top systems reshuffle: the best automatic run is 5th by humans. A run built to exploit the LLM judge ranked **5th automatically and 28th manually**. Risks: circularity, self-preference, prompt injection inside documents. https://arxiv.org/html/2412.17156v1 |
| Rerankers as judges (2026) | TREC DL | Rank1-7B to 32B reach κ about 0.38–0.48, close to UMBRELA. Each judge ranks its own reranker highest (self-preference). https://arxiv.org/html/2601.04455v1 |
| **Zalando multimodal judge** (GPT-4o plus image descriptions) | Fashion, 20k pairs | LLM vs human majority 65.6% (EN) and 64.7% (DE), vs **human-human 60.2% / 60.5%**. About 100–1000× cheaper; 20k labels in about 20 minutes vs about 3 weeks. LLM errors: mostly "too strict", hallucination on size queries. Human errors: brand and category mistakes from fatigue. https://arxiv.org/html/2409.11860v1 |
| Zalando production QA (2026) | Pre-launch market QA | GPT-4o judge on a 0–4 scale with product images. About **$250 per full run** over 3 markets × 1,500 query segments × 25 results, taking 3–5 hours, with judgments cached. https://engineering.zalando.com/posts/2026/03/search-quality-assurance-with-llm-judge.html |
| Allegro (2026) | Polish, Czech, Slovak, Hungarian | Quadratic κ 0.52–0.73. Gemini 3.1 Flash Lite was chosen for cost. A local Gemma-4-26B (4-bit) matched it on Polish at about 60% lower cost and about 16 pairs per second. Removing few-shot examples *helped*; removing the "critical rules" hurt badly. "No-thinking" mode beat "thinking". https://blog.allegro.tech/2026/08/automating-search-relevance-llm-as-a-judge.html |
| Walmart fine-tuned 7B judges | 6M training pairs | Micro-F1 0.896 vs humans 0.937. Re-running 718 past launch decisions, they agreed with human-label decisions 85–89% of the time and **reversed no significant launch**. https://arxiv.org/pdf/2406.00247 |
| Etsy (2026) | Production | o3 with few-shot chain of thought, multimodal inputs and self-consistency. Validated on a human golden set, then used to train the teacher (agreement numbers only in a figure [unverified]). |

### 2.3 Metrics

- **Amazon, 36 offline metrics vs 114 online interleaving comparisons.** NDCG@10 with *discretized binary or quantity labels* agreed with online purchased units on 97% of significant pairs (94% overall). Purchase-probability labels agreed only 62–75% of the time. k=10 beat k=20. https://cdn.amazon.science/ed/07/7766149e4f8d80e4572af86c353b/how-well-do-offline-metrics-predict-online-performance-of-product-ranking-models.pdf
- **Metrics by intent:**
  - Exact intent: Precision@1 and "exact-found@k", the recall of all exact listings within the top k.
  - Spec intent: graded nDCG@10.
  - Aesthetic intent: nDCG@10 plus pairwise preference win-rate.
  - All intents: constraint-violation rate in the top 10.
- Recall@k (100 or 1000) for candidate generation, as Etsy and Walmart do.

### 2.4 Offline-to-online, interleaving, A/B tests

- **Airbnb (2025).** Interleaving gives about **50× traffic efficiency** over A/B testing; Amazon's figure is 60×. Interleaving and A/B results agreed directionally 82% of the time across 29 pairs (r = 0.6). Counterfactual evaluation correlated 0.65 with A/B. Offline NDCG "often inconsistent" with conversion. https://arxiv.org/html/2508.00751
- **Netflix** reported interleaving needing more than 100× fewer users [unverified; widely cited 2017 blog].
- **Etsy** saw engagement sometimes *fall* while relevance rose. Keep relevance as a guardrail metric next to engagement. Fully relevant share went from 58% to 62% (Aug→Oct 2025).

### 2.5 How many judged queries?

- **Sakai's topic-set-size design.** For nDCG@10 at a minimum detectable difference of 0.15, α = 0.05 and 80% power across 10 systems, about **48 topics** are needed. https://research.nii.ac.jp/ntcir/workshop/OnlineProceedings12/pdf/evia/02-EVIA2016-SakaiT.pdf
- **[estimate]** Required topics scale with roughly 1/Δ². Detecting Δ = 0.05 therefore needs about 430 queries and Δ = 0.03 about 1,200, *per slice you want to read*. Paired tests on one query set need fewer than this independent-groups figure.
- **Industry practice:**
  - Pinterest: 300 stratified queries × top 8 for human evaluation.
  - Zalando: 500 queries × 20 results per language.
  - Walmart: 66k test pairs.
  - Allegro: more than 380k pairs.
  - Amazon: 2M replayed queries for offline metrics (behavioral).

---

## 3. Personalization and taste

- **User vectors from engagement.**
  - Etsy UEPPR feeds recent searches, clicked shops, and terms from clicked and purchased items into the query tower. A 1-layer transformer added 2% recall, and signed-in habitual buyers gained most.
  - Pinterest PinnerFormer: a causal transformer over 28 days of actions, trained to predict long-term future engagement rather than only the next action. A daily batch embedding nearly halves the gap to realtime at a fraction of the cost. https://ar5iv.arxiv.org/html/2205.04507
- **Explicit taste capture.** Stitch Fix Style Shuffle has logged 10B thumbs-up/down ratings at 4.5M per day, feeding a "Latent Style" space of 10M item and client coordinates. Dislikes matter as much as likes. https://newsroom.stitchfix.com/blog/10-billion-interactions-and-counting-on-style-shuffle-the-data-powering-your-personalized-shopping-experience/
- **Cold start through language (Google, 2023).** LLM recommendation from a short *natural-language* description of tastes was competitive with item-based CF at near cold start (NDCG@10 0.571 vs 0.559–0.577). Writing the description took about 1 minute vs about 3 minutes to name 5 liked items. https://web3.arxiv.org/pdf/2307.14225
- **Outfit and compatibility.**
  - OutfitTransformer (Amazon, WACV 2023): transformer outfit tokens for compatibility and complementary-item retrieval. https://openaccess.thecvf.com/content/WACV2023/papers/Sarkar_OutfitTransformer_Learning_Outfit_Representations_for_Fashion_Recommendation_WACV_2023_paper.pdf
  - Pinterest Complete The Look (scene-based complementary items). https://ar5iv.labs.arxiv.org/html/1812.01748
  - Fashionpedia-Taste (explaining human fashion taste). https://arxiv.org/pdf/2305.02307
  - VOGUE (2025), a multimodal conversational fashion-recommendation dataset. https://arxiv.org/html/2510.21151v1
- **Aesthetic understanding.**
  - Pinterest found board titles (user-curated *taste groupings*) gave +17% save recall, the largest single enrichment after captions. "Moodboard" co-occurrence is a strong style signal.
  - "Aligning Vision Models with Human Aesthetics in Retrieval" (NeurIPS 2024). https://neurips.cc/virtual/2024/poster/93151
- **Principle for us.** Personalization re-ranks *within* the relevant set and never overrides an exact-intent query. Etsy and Pinterest both apply relevance filtering before engagement ranking.

---

## 4. Training rerankers and embeddings from behavior and from LLM labels

### 4.1 Behavior signals and position bias

- **Clicks are biased and noisy.**
  - eBay estimated position propensity without interventions, from items shown at two different ranks. It decays roughly as a power law, with dips at mobile page-load boundaries every 40 results. Correcting for it improved AUC 3.4–6.8% at ranks 1–16. https://ar5iv.arxiv.org/html/1812.09338
  - Zalando added position as a feature during training and set it to a default at serving. Popularity skew fell, catalog coverage rose 3.1%, and main KPIs were flat. https://arxiv.org/pdf/2412.08780
  - **Baidu-ULTR (2024):** unbiased-LTR methods improved click prediction but *not* expert-judged ranking. Untuned BM25 (DCG@10 9.54) beat every click-trained model (about 7.4–8.5). Click and relevance objectives diverge. https://arxiv.org/pdf/2404.02543
- **Practice.**
  - Use saves and purchase or click-out as positives, impressed-but-skipped items as weak negatives (Amazon's 3-part loss), and random catalog items as easy negatives.
  - Cap popularity (Pinterest limits pairs per item to 50 and per product to 200).
  - Apply logQ correction for in-batch sampling (Pinterest).
  - Clean labels with a relevance model (Walmart).
  - Use behavior to *weight* relevance labels or as ranking features, not as the only source of relevance truth.

### 4.2 Hard-negative mining

- Etsy: dynamic hard negatives from a large sampled batch, with weight increasing over training; removing them cost about 7% recall.
- Walmart: offline ANN negatives filtered by product type and token overlap, plus "semi-positives" (relevant items ranked below position 50).
- NV-Retriever: *positive-aware* filtering, which drops candidate negatives scoring above a percentage of the positive's score. In one MS-MARCO study about 70% of the top-similar "negatives" were actually positives. https://arxiv.org/html/2407.15831v2
- **For resale specifically.** Other listings of the *same canonical product* are false negatives, so mask them. The best hard negatives are same brand with a different model, the same model in a different colorway, or the same silhouette in a different era.

### 4.3 Distilling LLM judgments into small models (published gains)

| System | Pipeline | Gain |
|---|---|---|
| **Etsy (2026)** | o3 annotator → fine-tuned **Qwen3-VL-4B** teacher (labels millions of pairs daily, served on vLLM) → BERT two-tower student (<10 ms) | Student used to filter irrelevant items, as a ranking feature, for loss weighting and for boosting. Fully relevant share 58% → 62%. |
| **Pinterest (2024)** | Llama-3-8B cross-encoder teacher (0.602 accuracy vs 0.535 for mBERT) → labels 30M pairs (100× the human set) → feed-forward student | Student accuracy 0.484 (0.3M human labels) → 0.548 (30M distilled). Online: human-judged nDCG@20 +2.18%, fulfillment +0.7% (US) and +2.0% (non-US). https://arxiv.org/html/2410.17152v1 |
| **Alibaba Taobao (WWW 2025)** | Qwen2-7B CoT teacher (CoT from 72B/70B models) → 30M pseudo-labels → BERT/ColBERT students via score KL plus CoT token supervision | Offline AUC +2.2–4.1%. Online: CTR +0.17%, Good rate +0.89% (+1.96% on long tail). Per 1,000 pairs on an H20: ColBERT 135 ms, BERT 7.3 s, teacher 432 s. https://export.arxiv.org/pdf/2411.13045 |
| **Amazon (COLING 2025)** | LLM rationales guide cross-encoder training | 110M BERT within 1% ROC-AUC of 7B LLMs, about **50× faster**. ESCI AUC +2.4%. https://www.amazon.science/publications/rationale-guided-distillation-for-e-commerce-relevance-classification-bridging-large-language-models-and-lightweight-cross-encoders |
| **Walmart (2024)** | LoRA fine-tuned 7B judge | F1 0.896 (vs 0.843 for the cross-encoder baseline). https://arxiv.org/pdf/2406.00247 |
| **Instacart (2025)** | Frontier LLM → Llama-3-8B LoRA for query understanding | Matches the teacher's F1 about 95.7% at about 300 ms. |

---

## 5. Latency and cost budgets for LLM reranking

- **Published reference points:**
  - ANN retrieval: p99 18–20 ms at thousands of QPS (Etsy). Query embeddings: p50 3 ms, p90 20 ms at 300k rps with caching (Pinterest).
  - Online student relevance model: under 10 ms (Etsy).
  - Cross-encoder (BERT-base): about 7 ms per pair *unbatched* on an H20. ColBERT about 0.14 ms per pair (Alibaba table).
  - Fine-tuned 8B LLM, real time: about 300 ms on an H100 for short structured output (Instacart).
  - Listwise LLM reranking (RankZephyr-class 7B, window 20, stride 10, top 100): seconds per query on one A6000 or A100. First-token decoding saves 24–50% (FIRST papers).
  - Small pointwise LLM rerankers with offline hints: 149 ms (0.5B) to 473 ms (3B) added over retrieval (Amazon, L40S).
  - Vendor figures [unverified, ZeroEntropy, July 2025]: cross-encoder 12 ms and about $2 per 1k queries; Gemini-Flash listwise top-20 about 420 ms and about $18 per 1k queries; listwise LLM about 9× the cost and 35× the latency for +0.04 NDCG@10. https://zeroentropy.dev/articles/llm-as-reranker-guide
  - Judge runs: Zalando about $250 per full market QA run (GPT-4o). Allegro's local 26B model handles about 16 pairs per second.
- **[estimate] Our per-query token math.**
  - A text-only LLM listwise rerank of the top 20 uses about 20 × 150 tokens of normalized listing data plus about 300 tokens of query and instructions, so about **3.3k input tokens and about 20 output tokens**.
  - Adding one thumbnail per listing adds about 20 × (250–1,000) image tokens, so **3–6× more**.
  - At an illustrative small-model price of $0.10–0.30 per million input tokens (check current vendor pricing), text-only costs $0.33–1.00 per 1k queries and the VLM version $1–6 per 1k.
  - At 1M queries per day that is about $330–6,000 per day, *before* caching. Latency would be about 300–800 ms on a hosted flash-class model.
- **Implications:**
  - (a) Keep the LLM/VLM out of the default synchronous path. Run it on head queries offline (cache by normalized query; Instacart serves about 98% from cache) and on low-confidence or exact-intent tail queries.
  - (b) Cache (query-parse, listing) judgments. Listings are immutable once normalized.
  - (c) Distil to a cross-encoder or two-tower student within about 3 months.
  - (d) Use LLM/VLM verification for *identity* checks on the top 3–5 exact-intent candidates, where the value is highest and the candidate list is shortest.

---

## 6. Recommended search stack and eval program for us

### 6.1 Architecture in words

**Offline, at index time (per listing, on ingest and update):**

1. **Vision normalization.** A VLM extracts category, brand (with logo/hardware cues), model or line, era estimate, material, color, pattern, silhouette, condition cues, and measurements or size, each with a **confidence score**. It also records *claimed vs observed* conflicts, i.e., an eBay-style mismatch flag. Store an attribute JSON plus a caption.
2. **Canonical product resolution.** Cluster listings into canonical products (brand + model + colorway + era) using the Zalando fashionID recipe: image + text + numeric features, a contrastive projection, ANN restricted to brand, then a threshold, with expert review of low-confidence clusters. This gives a product ID, a cross-platform dedupe key, and price normalization (fees, shipping, currency).
3. **Embeddings.**
   - (a) Text embedding over the normalized attributes plus title.
   - (b) Image embedding, fashion-tuned for apparel and bags (Marqo-FashionSigLIP or a SigLIP2 fine-tune) and general-purpose or Qwen3-VL for furniture and home. Pick on our own benchmark.
   - (c) A **style embedding** trained on co-save and board-like co-occurrence plus aesthetic tags.
4. **Indexes.** Lexical BM25 over normalized fields and raw text (Vespa, OpenSearch or Elastic). Vector ANN per vertical and category (Pinterest per-category indexes). Streaming upserts for freshness, with sold-item removal within minutes.

**Online, per query:**

1. **Input.** Text, photo, or both. For photos: detect, crop the main and secondary objects, embed, and run a VLM identify pass ("Breuer Cesca chair, cane, chrome" plus confidence). Fan out as Google does.
2. **Query understanding.** A cache lookup for head queries; otherwise a small fine-tuned LLM (about 300 ms) or a rules-plus-NER fast path. Output:
   - `{intent: exact | spec | aesthetic, specificity, hard_constraints {price, size, category, condition}, soft_attributes {brand, era, material, color, style}, rewrites[], canonical_product_candidates[]}`
   - Spelling correction and taxonomy mapping happen here.
3. **Candidate generation in parallel** (about 20–50 ms):
   - (a) Canonical-ID lookup, if an exact product was identified.
   - (b) BM25 with field boosts.
   - (c) Text-dense ANN.
   - (d) Image ANN, for photo queries or style intent.
   - (e) Style-embedding ANN, for aesthetic intent.
   - Union about 1,000, then collapse duplicates across platforms.
4. **Hard-constraint filter** on normalized values. Filters soften to a penalty when attribute confidence is low.
5. **L1 ranker.** GBDT or a small MLP over features: fusion scores, attribute-match counts, constraint confidence, listing quality, price vs canonical-product median, seller reputation, freshness. Cut to the top 200.
6. **L2 relevance cross-encoder.** Text over the query parse and listing attributes and caption, optionally with an image tower. Distilled from the LLM/VLM judge. Cut to the top 30.
7. **L3, conditional.** For exact intent, a VLM identity verifier on the top 5 ("is this the same product as X?"), optionally with keypoint matching. For low-confidence or ambiguous queries, a listwise LLM pass on the top 20, run async or with a "refine" step.
8. **Personalization and diversity.** Taste-vector similarity, size and brand affinity, and platform preferences re-rank *within* relevance tiers. Cap near-duplicates and canonical-product repeats in the top 10.
9. **Presentation by intent.** "Exact matches" (canonical-ID hits, ranked by price and condition), then "Close alternatives", then "Same vibe". For exact intent, show a "why this matched" line from the attribute diff, which also feeds evaluation.

### 6.2 What to train when

| Phase | Timing | Build | Train |
|---|---|---|---|
| **0: Baseline** | Weeks 0–6 | BM25 over normalized fields; off-the-shelf SigLIP2 or FashionSigLIP plus text embeddings; score-normalized fusion; prompted LLM query parser with cache; off-the-shelf cross-encoder (bge-reranker-v2 or Qwen3-VL-Reranker-2B) on the top 50. | Nothing custom. Build **gold set v1** and **LLM judge v1** and calibrate the judge to humans. |
| **1: LLM-label distillation** | Months 2–4 | Judge labels 0.5–5M (query, listing) pairs from logged and synthetic queries. Pinterest and Taobao used about 30M; start smaller. | (a) Fine-tune a VLM teacher (Qwen3-VL 4B or 8B), Etsy-style. (b) Distil into the L2 cross-encoder. (c) Contrastive fine-tune of image and text embeddings on canonical-product pairs, with same-product false negatives masked and hard negatives from same brand/different model. (d) LoRA fine-tune of a small query-understanding LLM for the tail. |
| **2: Behavior** | Once about 100k+ search sessions with saves or click-outs have been logged | Log impressions with positions. Run small randomized swaps in the top 10 to estimate propensity (eBay or Zalando style). Run interleaving infrastructure. | Add saves, click-outs and purchases as L1 features and as label *weights*. Keep LLM/human relevance as the primary label (Baidu and Walmart lessons). Retrain the two-tower with a 3-part loss. |
| **3: Taste** | Months 4–9 | Onboarding swipe deck (Style Shuffle style) plus a free-text "describe your style"; taste vector = recency-weighted multi-cluster mean of saved-item style embeddings. | Sequence user model (PinnerFormer-lite, daily batch). Compatibility model for "complete the look". |

### 6.3 Judgment set: size and guidelines outline

**Size and stratification:**

- **v1 (month 1):** 600 queries, top 20 pooled from at least 3 systems (BM25, dense, hybrid plus rerank), about 12k pairs. **Two trained labelers plus an adjudicator**, using fashion and furniture resellers, not crowd workers.
  - [estimate] Cost: $12–25k at $0.50–1.00 per pair per label.
  - Strata, about 50 queries per cell for the key cells:
    - Intent: exact-model, spec, aesthetic, photo-of-item, photo-of-vibe.
    - Vertical: bags, apparel, shoes, jewelry/watches, furniture, home decor.
    - Head, torso, tail.
    - Queries with hard constraints (size or price) vs without.
- **v2 (month 3):** 1,500–2,000 queries, so slice-level differences of about 0.03–0.05 nDCG@10 are detectable (§2.5).
  - Add about 200 "known-item" photo queries with a verified canonical product present in the index, to measure exact P@1.
  - Add about 300 aesthetic queries with **pairwise** judgments (A vs B result lists), since graded "similar" labels are where agreement collapses (Allegro substitute F1 0.33–0.51).
- **Ongoing:** refresh 10–15% of queries monthly from live traffic to fight drift, as Etsy does. The LLM judge labels about 5–20k queries nightly for monitoring. A re-sampled human audit of judge disagreements runs weekly.
- **LLM judge acceptance bar:**
  - Agreement with adjudicated labels ≥ human-human agreement (Zalando).
  - Quadratic κ ≥ 0.65.
  - Exact-class F1 ≥ 0.9.
  - Launch decision agreement ≥ 85% on backtests (Walmart).
  - Use a **different model family for the judge than for the online reranker teacher**, or at least a held-out human set, to limit self-preference and circularity.

**Label scale.** Gain values for nDCG are shown in brackets.

- **3, Exact** [gain 7]: the same canonical product, or for spec queries every stated attribute satisfied, and all hard constraints met.
- **2, Close substitute** [gain 3]: the same brand and category with one *soft* attribute off (adjacent era, near colorway). For aesthetic queries: clearly the same style.
- **1, Related** [gain 1]: the right category and partly matches; a style-adjacent item; a different brand in the same aesthetic.
- **0, Irrelevant or violates a hard constraint** [gain 0]: the wrong category, over budget, the wrong size, unwearable condition when "excellent" was asked.

**Required flags (multi-select):**

- Constraint violated: price, size, condition, category, shipping.
- Listing data wrong: the title or size contradicts the photos. Record whether *our* normalization caught it.
- Possible counterfeit or misattributed brand.
- Duplicate of a higher-ranked result (cross-platform).
- Sold or unavailable.
- Hard to say.

**Guideline sections:**

1. How to read the query: write out the requirement list with must-have vs nice-to-have, Zalando-style.
2. Intent definitions with examples.
3. Attribute rules per vertical: era-dating cues (logos, tags, hardware), material vocabulary (Prada Re-Nylon / Tessuto), size systems (vintage vs modern, EU/US/IT), furniture designer vs "style of".
4. Condition scale mapping across platforms.
5. Authenticity red flags. The labeler flags; the label does not decide authenticity.
6. Aesthetic vocabulary with visual exemplars ("90s minimalism", "Y2K", "quiet luxury", "mid-century", "Memphis", "Japandi").
7. Edge cases: bundles and lots, "inspired by" and dupes, kids' sizes, replicas labeled as such.
8. Tie-break and escalation; how guidelines are versioned.

### 6.4 Target metrics

Targets are starting points. Re-baseline after gold set v1.

| Metric | Slice | Target, 6 months |
|---|---|---|
| **Exact P@1** (top result is the canonical product, when one exists in the index) | Exact-model text queries | ≥ 0.85 |
| Exact P@1, photo queries | Studio or flat-lay photo | ≥ 0.80 |
| Exact P@1, photo queries | Street or in-situ photo | ≥ 0.60. The best published fine R@1 on street looks is about 62% (LookBench). |
| **Exact-found@10** (share of in-index exact listings surfaced in the top 10, across platforms) | Exact intent | ≥ 0.90 |
| **Constraint-violation rate in the top 10** | Queries with hard constraints | ≤ 2% |
| **nDCG@10** (graded, gains 7/3/1/0) | Spec intent | +15% relative over the Phase-0 baseline |
| Share of top 10 that is "Exact or Close" | Spec intent | ≥ 70% (Etsy's "fully relevant" share is 62%, on a looser task) |
| **Pairwise win-rate vs baseline** (human, LLM-checked) | Aesthetic intent | ≥ 60% |
| Near-duplicate / same-canonical repeats in the top 10 | All | ≤ 1 per query, unless intent is exact |
| Candidate Recall@200 of judged-relevant items | All | ≥ 0.9 |
| Zero / near-zero result rate | All | < 1% |
| Latency, p95 end to end | Text | ≤ 600 ms |
| Latency, p95 end to end | Photo | ≤ 1.2 s, with L3 verification async or on the top 5 only |
| **Online** | Primary | Save rate per search and click-out rate per search. Guardrails: reformulation rate, time to first save, purchase-attributed click-outs. Run interleaving for ranker changes and A/B for UX changes. |

### 6.5 Gaps where we can lead

1. **A cross-platform canonical-product graph for resale.** Nothing has been published on resolving one-of-one secondhand listings into product identities (brand, model, colorway, era). Exact-intent precision depends on it, and it enables price comparison, dedupe and "notify me when one appears" alerts.
2. **Normalization-aware relevance.** Rank on *observed* attributes and flag claimed-vs-observed conflicts, eBay's mismatch idea taken further. Resale listings are often wrongly sized or titled. Treat "listing data wrong" as a labeled, measured failure class.
3. **Era, authenticity and condition as first-class attributes.** These are absent from ESCI-style schemes. A judgment guideline and benchmark that include them would be novel.
4. **Aesthetic-intent evaluation.** Published judges are weakest on the "substitute" and "similar" end. Pairwise style judgments with exemplar-anchored vocabularies, plus a style embedding trained on co-saves, are open territory.
5. **Photo-to-exact-item in the wild for resale.** LookBench shows street-photo exact retrieval tops out around 60%. Our ingestion of user-shot listing photos is a natural training set for that domain gap, similar to Etsy's review-photo task.
6. **An open benchmark.** Release a small "ResaleBench" of queries, listings and graded labels, like LookBench or ESCI. It would help with credibility, recruiting, and attracting partner platforms.
7. **Text-plus-photo composed queries** ("this, but in black, under $300"). Alibaba names this as an unsolved failure mode, and our query parse plus filters handle it explicitly.

---

## Sources

**Architecture and systems**
- Etsy UEPPR: https://arxiv.org/html/2306.04833v2
- Etsy LLM relevance (2026): https://www.etsy.com/codeascraft/how-etsy-uses-llms-to-improve-search-relevance
- Etsy visual representations (2024): https://www.etsy.com/codeascraft/efficient-visual-representation-learning-and-evaluation
- Etsy search by image: https://www.etsy.com/codeascraft/from-image-classification-to-multitask-modeling-building-etsys-search-by-image-feature [read via summary, unverified]
- Pinterest OmniSearchSage: https://arxiv.org/pdf/2404.16260
- Pinterest LLM relevance: https://arxiv.org/html/2410.17152v1
- Pinterest Shop The Look: https://ar5iv.labs.arxiv.org/html/2006.10866
- PinnerFormer: https://ar5iv.arxiv.org/html/2205.04507
- Amazon Semantic Product Search: https://ar5iv.labs.arxiv.org/html/1907.00937
- Amazon ESCI: https://ar5iv.arxiv.org/html/2206.06588
- Amazon hint-augmented reranking: https://arxiv.org/pdf/2511.13994
- Amazon offline vs online metrics: https://cdn.amazon.science/ed/07/7766149e4f8d80e4572af86c353b/how-well-do-offline-metrics-predict-online-performance-of-product-ranking-models.pdf
- Amazon rationale distillation: https://www.amazon.science/publications/rationale-guided-distillation-for-e-commerce-relevance-classification-bridging-large-language-models-and-lightweight-cross-encoders
- Walmart EBR: https://arxiv.org/html/2408.04884v2
- Walmart LLM judges: https://arxiv.org/pdf/2406.00247
- Walmart LLM labeling cost: https://www.alphaxiv.org/overview/2502.15990 [summary page]
- Instacart: https://tech.instacart.com/building-the-intent-engine-how-instacart-is-revamping-query-understanding-with-llms-3ac8051ae7ac
- Taobao BEQUE: https://astro.paperswithcode.com/paper/large-language-model-based-long-tail-query
- Taobao distillation: https://export.arxiv.org/pdf/2411.13045
- Pailitao-MMSearch: https://www.alphaxiv.org/abs/2607.17499
- Zalando fashionID: https://arxiv.org/pdf/2403.11593
- Zalando LLM judge paper: https://arxiv.org/html/2409.11860v1
- Zalando judge QA (2026): https://engineering.zalando.com/posts/2026/03/search-quality-assurance-with-llm-judge.html
- Zalando position bias: https://arxiv.org/pdf/2412.08780
- eBay multimodal embeddings: https://innovation.ebayinc.com/stories/beyond-words-how-multimodal-embeddings-elevate-ebays-product-recommendations/
- eBay position bias: https://ar5iv.arxiv.org/html/1812.09338
- Shopify: https://shopify.engineering/how-shopify-improved-consumer-search-intent-with-real-time-ml
- Google AI Mode and Shopping Graph: https://blog.google/products/search/search-ai-updates-september-2025/
- ThredUp: https://www.mannpublications.com/fashionmannuscript/2024/08/05/thredup-launches-suite-of-ai-shopping-features/
- Allegro: https://blog.allegro.tech/2026/08/automating-search-relevance-llm-as-a-judge.html
- Airbnb interleaving: https://arxiv.org/html/2508.00751

**Models and benchmarks**
- SigLIP 2: https://arxiv.org/pdf/2502.14786
- Marqo-FashionCLIP / FashionSigLIP: https://github.com/marqo-ai/marqo-FashionCLIP
- Qwen3-VL-Embedding / Reranker: https://arxiv.org/abs/2601.04720v1
- LookBench: https://arxiv.org/pdf/2601.14706
- PRISM: https://arxiv.org/pdf/2509.14985
- FIRST: https://arxiv.org/html/2406.15657v1
- FIRST reproduction: https://arxiv.org/html/2411.05508v2
- NV-Retriever: https://arxiv.org/html/2407.15831v2
- ExtractGPT: https://arxiv.org/abs/2310.12537
- OpenSearch RRF: https://opensearch.org/blog/introducing-reciprocal-rank-fusion-hybrid-search/
- ZeroEntropy (vendor): https://zeroentropy.dev/articles/llm-as-reranker-guide [unverified]

**Evaluation**
- Thomas et al.: https://arxiv.org/html/2309.10621v3
- UMBRELA: https://alphaxiv.org/abs/2406.06519
- UMBRELA on other LLMs: https://arxiv.org/html/2507.09483v1
- LLM judging critique: https://arxiv.org/html/2412.17156v1
- Rerankers as judges: https://arxiv.org/html/2601.04455v1
- Baidu-ULTR: https://arxiv.org/pdf/2404.02543
- Sakai topic set size: https://research.nii.ac.jp/ntcir/workshop/OnlineProceedings12/pdf/evia/02-EVIA2016-SakaiT.pdf

**Taste and personalization**
- Stitch Fix: https://newsroom.stitchfix.com/blog/10-billion-interactions-and-counting-on-style-shuffle-the-data-powering-your-personalized-shopping-experience/
- LLM near cold start: https://web3.arxiv.org/pdf/2307.14225
- OutfitTransformer: https://openaccess.thecvf.com/content/WACV2023/papers/Sarkar_OutfitTransformer_Learning_Outfit_Representations_for_Fashion_Recommendation_WACV_2023_paper.pdf
- Complete the Look: https://ar5iv.labs.arxiv.org/html/1812.01748
- Fashionpedia-Taste: https://arxiv.org/pdf/2305.02307
- VOGUE: https://arxiv.org/html/2510.21151v1
- Aesthetics in retrieval: https://neurips.cc/virtual/2024/poster/93151
