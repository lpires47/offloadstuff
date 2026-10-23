# Vision moat research: exact-product ID and design-literate retrieval for resale

Research date: 2026-10-23. Every claim has a source link next to it, and I opened each of those pages. **[UNVERIFIED]** marks claims I recall but could not confirm in a source during this session. The shared web-search budget ran out partway through, so some sub-topics have thinner coverage. They are listed at the end ("Coverage gaps in this research").

---

## 1. Fine-grained product recognition and instance-level retrieval: encoders and benchmarks

### 1.1 Open vision encoders

| Model | Sizes | License | Key numbers | Source |
|---|---|---|---|---|
| **SigLIP 2** (Google DeepMind, Feb 2025) | B (86M), L (303M), So400m (400M), g (1B); 224–512px fixed-res, plus a **NaFlex** variant for native aspect ratio | Apache-2.0 per the big_vision checkpoints **[UNVERIFIED: the paper page did not state it]** | Zero-shot IN-1k: B/16-256 79.1, So/16-384 84.1, g/16-384 85.0. COCO T→I R@1: 52.1–56.1. RefCOCO B/16 83.8 vs 64.1 for SigLIP v1. Recipe adds a LocCa captioning decoder, self-distillation, and masked prediction | [arXiv 2502.14786](https://arxiv.org/html/2502.14786v1) |
| **DINOv3** (Meta, Aug 2025) | ViT-7B teacher, distilled to ViT-S/S+/B/L/H+ (21M–0.8B) and ConvNeXt-T/S/B/L | **Custom "DINOv3 License"**, gated (`license: other`). Read the commercial terms before shipping | Instance retrieval vs DINOv2: Oxford-H 60.7 vs 58.2, Paris-H 87.1 vs 84.6, **Met 55.4 vs 44.6**, AmsterTime 56.5 vs 48.9. iNat21 linear probe: 89.8 (PE-core 87.0, SigLIP2 82.7). On the Fine-S 12-dataset average it trails PE-core (94.5) and SigLIP2 (93.7) | [arXiv 2508.10104](https://arxiv.org/pdf/2508.10104), [HF card](https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m/blob/main/README.md) |
| **Perception Encoder (PE-core / PE-lang / PE-spatial)** (Meta, Apr 2025) | B, L, G | Apache-2.0 (per HF card listing in search results; [HF README](https://huggingface.co/facebook/pe_core_base_patch16_224_timm/blob/main/README.md) not opened) **[partly UNVERIFIED]** | Key claim: the best embeddings sit in *intermediate* layers. Average zero-shot IN robustness 86.6 | [arXiv 2504.13181](https://arxiv.org/abs/2504.13181v1) |
| **Marqo-FashionSigLIP / FashionCLIP** (Marqo, 2024) | ViT-B/16 (SigLIP base) | **Apache-2.0** | Averaged over 6 fashion datasets: T→I R@1 0.121 vs FashionCLIP2.0 0.077 and base SigLIP 0.111. Category→product P@1 0.758. Sub-category→product P@1 0.767 | [GitHub](https://github.com/marqo-ai/marqo-FashionCLIP) |
| **Jina Embeddings v4** (Jun 2025) | 3.8B, Qwen2.5-VL-3B backbone; single-vector (2048-d, MRL down to 128) and multi-vector | Not stated on the page (Qwen-research-derived) **[UNVERIFIED]** | ViDoRe 90.2. Built for documents, with no e-commerce results | [Jina blog](https://jina.ai/news/jina-embeddings-v4-universal-embeddings-for-multimodal-multilingual-retrieval/) |
| **Marqo-Ecommerce-Embeddings B/L** | — | — | I could not read the page (blocked URL: `huggingface.co/Marqo/marqo-ecommerce-embeddings-L`) | — |

### 1.2 Head-to-head on product instance retrieval (the most relevant evidence)

**nyris Visual Product Search Benchmark** ([arXiv 2603.17186](https://arxiv.org/abs/2603.17186), Mar 2026). It covers 8 datasets, including SOP, Products-10K, ILIAS, and a proprietary **Furniture v1** set (50,641 products). The average over 6 datasets (R@1 / mAP@20):

| Model | Avg R@1 | Avg mAP@20 |
|---|---|---|
| nyris GEM v5.1 (proprietary, domain-trained) | **58.3** | 49.5 |
| Gemini Embedding 2 (API) | 43.8 | 34.4 |
| **SigLIP2 SO400M** (best open model) | 43.4 | 34.2 |
| DINOv3 ViT-L/16 | 41.9 | 30.2 |
| Vertex AI Multimodal | 40.9 | 33.1 |
| PE-Core L/14 | 40.0 | 31.3 |
| Cohere Embed v4 | 35.8 | 28.2 |
| DINOv2-L | 33.0 | 22.0 |
| Jina v4 | 28.5 | 19.6 |
| Nomic Embed MM 3B | 27.0 | 18.0 |

Furniture v1 R@1: GEM 65.8 vs SigLIP2 57.4. SOP R@1: GEM 86.9 vs Gemini Emb 2 about 80.3. The paper's conclusion is that general pretraining is not enough for exact instance matching, and that near-identical instances and domain shift are where foundation models fail. The paper has some text/table inconsistencies.

**LookBench** (Gensmo.ai, [arXiv 2601.14706](https://arxiv.org/abs/2601.14706), v3 Apr 2026) is a live fashion image-retrieval benchmark with about 2.5k queries against a 60k-image corpus, in studio and street-look subsets, using *fine* Recall@1 (attribute-faithful match):

| Model | Fine R@1 overall |
|---|---|
| GR-Pro (proprietary) | 67.38 |
| **GR-Lite (open; DINOv3-derived, under the DINOv3 License)** | 65.71 |
| Marqo-FashionCLIP | 63.24 |
| Marqo-FashionSigLIP | 62.77 |
| SigLIP2-B/16 | 59.44 |
| SigLIP2-L/16 | 54.84 |
| DINOv3 ViT-L / 7B (zero-shot) | 43.97 / 43.33 |
| CLIP-L/14 | 39.79 |

Takeaways from LookBench:
- **Fine-tuning DINOv3 on fashion moves it from about 44 to 65.7**, so the backbone's zero-shot rank is a poor guide to its fine-tuned ceiling.
- Data scaling saturated near 6.5M training images.
- Going from a 0.3B to a 0.8B backbone gave about no gain.
- Outfit-level (multi-item street) retrieval stays at about 47–53%.

**Practitioner replication** ("Beating FashionSigLIP", [Substack](https://hopitai.substack.com/p/beating-fashionsiglip), undated). It fine-tuned FashionSigLIP on 13.5k DeepFashion2 shop↔consumer triplets with InfoNCE plus L2 weight-drift regularization (lr 2e-6, 4 epochs, laptop). Results:
- Fine R@1 went from 63.84 to 66.52, and to 67.68 when ensembled with FashionCLIP.
- **Joint text-image fine-tuning *hurt* image→image retrieval (−9 points).** DINOv2 zero-shot scored 39.5.
- Lesson: the domain shift in the training data (consumer photo → studio photo) matters more than the loss or architecture.

**Zalando fashionID** ([arXiv 2403.11593](https://arxiv.org/abs/2403.11593)) does product matching over 2M offers. It uses a frozen CLIP ViT-bigG image+text encoder with a linear projection to 192-d, trained with contrastive loss at batch 16k in about 10 min on one A100. AUCPR:
- Raw CLIP image: 27.2
- Image-only projection: 57.2
- Image+text+numeric: **66.1**
- **Raw DINOv2-G: 2.4**

CLIP beat DINOv2 for matching. Expert human-in-the-loop with 3-vote majority raised output precision from 0.285 to **0.937**. Crowd workers could not reach 90% precision.

**Shopee MIEM** ([arXiv 2311.17954](https://arxiv.org/abs/2311.17954), AAAI 2024). It fuses multiple images with the title. Offline R@1 went from 0.820 to 0.872. Online same-item R@4 went from 50.6% to 53.7%, and orders/user rose 4–5%.

### 1.3 Classic benchmarks (reported numbers)

- **Stanford Online Products (SOP)**, R@1 leaderboard ([HyperAI](https://vercel.hyper.ai/en/sota/tasks/metric-learning/benchmark/metric-learning-on-stanford-online-products-1)): Unicom+ViT-L@336 91.2, STIR 88.3, Recall@k Surrogate (ViT-B/16) 88.0, Hyp-ViT 85.9. These are fine-tuned on SOP. Zero-shot foundation models reach about 80 (Gemini Emb 2, per nyris).
- **Products-10K** (JD.com, about 10k SKUs, 150k images, consumer and shop photos; [arXiv 2008.10545](https://ar5iv.labs.arxiv.org/html/2008.10545)): the EfficientNet-B3 baseline gets 60.0% top-1, rising to 64.1% with high resolution and a metric loss. nyris calls SOP and Products-10K "pre-foundation-model" benchmarks with small gaps between models.
- **Amazon Berkeley Objects (ABO)** ([arXiv 2110.06199](https://ar5iv.arxiv.org/html/2110.06199), CC BY-NC 4.0): 147,702 listings and 7,953 3D models. Multi-view retrieval R@1 is 30.0% for rendered queries and 39.7% for catalog queries (2022-era baselines).
- **DeepFashion In-shop**: I found no 2025 foundation-model leaderboard. Marqo includes it in its averaged tables (§1.1). **[gap]**
- **eProduct, iMaterialist-Product**: not covered (search budget). **[gap]**

---

## 2. Open VLMs to post-train for attribute extraction and identification

| Model | Sizes | License | Notes and published results | Source |
|---|---|---|---|---|
| **Qwen3-VL** (Alibaba, Sep–Oct 2025) | Dense 2B/4B/8B/32B; MoE 30B-A3B and 235B-A22B; Instruct and Thinking editions; FP8 builds | **Apache-2.0** | 256K context; DeepStack (multi-layer ViT features), interleaved MRoPE. Post-training is SFT → strong-to-weak distillation → RL (SAPO). 235B: **OCRBench 920**, DocVQA 97.1. Repo has a `qwen-vl-finetune` folder | [arXiv 2511.21631](https://arxiv.org/abs/2511.21631), [GitHub](https://github.com/QwenLM/Qwen3-VL) |
| **Qwen3.5** (Feb–Mar 2026) | Dense 0.8B/2B/4B/9B; MoE 35B-A3B, 122B-A10B, 397B-A17B | Mostly Apache-2.0 | "Native multimodal" (early fusion) across the family; claims fine-grained OCR. No vision numbers in the source I read. A Qwen3.6 also exists (Roboflow comparison pages), with no details found | [qudata](https://qudata.com/en/news/exploring-qwen35-family/) |
| **Gemma 4** (Google DeepMind, 2 Apr 2026) | E2B, E4B, 26B-A4B MoE (3.8B active), 31B dense | **Apache-2.0** (replaces the Gemma license) | Image input at all sizes; 31B MMMU-Pro 76.9 | [DataNorth](https://datanorth.ai/news/google-releases-gemma-4-open-models) |
| **InternVL3.5** (Shanghai AI Lab, Aug 2025) | 1B, 2B, 4B, 8B, 14B, 38B, 20B-A4B, 30B-A3B, 241B-A28B | **Apache-2.0** | InternViT-300M/6B encoder. **Cascade RL**: offline MPO, then online GSPO. Reports +16% reasoning over InternVL3 | [HF card](https://huggingface.co/OpenGVLab/InternVL3_5-4B), [arXiv 2508.18265](https://arxiv.org/abs/2508.18265v2) |
| **Molmo 2** (Ai2, Dec 2025) | 4B and 8B (Qwen3 base), O-7B (Olmo base, fully open) | Open; exact license not stated **[UNVERIFIED]** | Pixel and temporal **pointing/grounding**, tracking, counting | [AI Business](https://aibusiness.com/foundation-models/ai2-molmo-open-video-models) |
| **Pixtral 12B** (Mistral, Oct 2024) | 12B; encoder trained from scratch at native resolution | **Apache-2.0** | Beats Llama-3.2 11B and Qwen2-VL 7B | [arXiv 2410.07073](https://arxiv.org/abs/2410.07073) |
| **Gemma 3** (Mar 2025) | 1B–27B, 128K context | Gemma Terms **[UNVERIFIED]** | Superseded by Gemma 4 | [arXiv 2503.19786](https://arxiv.org/abs/2503.19786) |
| Llama 4 / Llama 3.2 Vision | 11B/90B (3.2) | Llama Community License (3.2, per [Labellerr](https://www.labellerr.com/blog/top-open-source-vision-language-models/)) | Llama 4 not verified **[UNVERIFIED]** | — |

### 2.1 Fine-tuning recipes and evidence

- **RL with verifiable rewards works for fine-grained recognition.** Visual-RFT ([arXiv 2503.01785](https://arxiv.org/html/2503.01785v1), ICCV 2025) trains Qwen2-VL-2B with GRPO and the reward `R = R_acc + R_format`. One-shot fine-grained average accuracy went from 56.0 to **80.3**, while SFT got 51.7 (lower than the baseline). Cars196 went from 56.8 to **93.8**. At 16-shot, RFT reached 85.3 vs SFT 64.0. With roughly 100 examples, SFT overfits and RFT generalizes. This bears directly on long-tail SKUs where each one has few labeled photos.
- **Retrieve-then-rank beats either part alone.** RAR ([arXiv 2403.13805](https://arxiv.org/html/2403.13805v1)): CLIP retrieves the top-5 candidates, then an MLLM fine-tuned on about 30k ranking examples picks one. Fine-grained average went from 57.0 (FineR) to 58.5. LVIS rare-class AP went from 40.6 to 60.2. MLLMs on their own break down with large label vocabularies, so give them candidates instead of asking them to generate the answer.
- **Fine-grained is where VLMs are weakest.** FG-BMK ([arXiv 2504.14988](https://arxiv.org/html/2504.14988v2), 1.01M questions). InternVL3 is about 99.8% accurate at class level, about 61% at species level, and 31% on shape attributes. Contrastive encoders (EVA-CLIP, InternViT, DINOv2) hold more fine-grained signal than generative ones. **Text alignment costs about 3.4% fine-grained accuracy.** Data quality matters more than scale. FROW ([arXiv 2512.10384](https://arxiv.org/abs/2512.10384v1)) adds that putting fine-grained data into *pretraining* gives up to +10%.
- **E-commerce attribute extraction.** On ImplicitAVE ([arXiv 2404.15592](https://arxiv.org/html/2404.15592v2)), GPT-4V scores 86.8 micro-F1 but only 77.4 on Clothing and 66.0 on sleeve style, with frequent confusion of close values (3/4 vs long sleeve). Open 2024 models score about 71. Zalando's GPT-4o attribute copilot ([blog](https://engineering.zalando.com/posts/2024/09/content-creation-copilot-ai-assited-product-onboarding.html), Sep 2024) has **about 75% attribute accuracy** and is weak on fashion-specific terms such as "deep scoop neck". Front product-only images work best.
- **Tooling.** TRL has VLM tutorials for SFT, DPO, MPO, and **GRPO** ([TRL community tutorials](https://huggingface.co/docs/trl/en/community_tutorials), [GRPO VLM cookbook](https://huggingface.co/learn/cookbook/fine_tuning_vlm_grpo_trl)). InternVL3.5's MPO→GSPO cascade is a recipe others can follow. LLaMA-Factory, ms-swift, and Unsloth also support Qwen-VL LoRA **[UNVERIFIED this session]**.
- **Pinterest's production pattern** (VentureBeat, 29 May 2026, [link](https://venturebeat.com/ai/pinterest-cut-ai-costs-90-by-gutting-a-frontier-models-vision-layer/)). Pinterest's shopping assistant runs on **Qwen3-VL**. They removed its vision encoder and fine-tuned the model on precomputed in-house multimodal embeddings, reporting about 90% lower cost and about 30% higher accuracy. Without precomputed embeddings, latency would be about 20× worse.

---

## 3. What industry leaders have published

- **eBay**
  - Visual search (2017; [arXiv 1706.03154](https://arxiv.org/abs/1706.03154)): category prediction narrows the search, then binary-hash retrieval, in a single network.
  - Multimodal recommendations (BERT titles + ResNet-50 images, Siamese two-tower with TransH, plus an image/title **mismatch detector**): CTR +15.9%, purchase-through rate +31.5%, live since Feb 2023 ([blog](https://innovation.ebayinc.com/stories/beyond-words-how-multimodal-embeddings-elevate-ebays-product-recommendations/)).
  - Magical Listing (Sep 2023, Azure OpenAI): 95% of users who tried the description feature kept it, CSAT over 80% ([blog](https://innovation.ebayinc.com/tech/features/magical-listing-tool-harnesses-the-power-of-ai-to-make-selling-on-ebay-faster-easier-and-more-accurate/)).
  - The next-gen photo-to-listing tool became the default in the US (announced on the Q4-2025 earnings call). An independent test found **it misidentified a mousepad twice, giving a different wrong item each time, and the wrong ID then flowed into the title, item specifics, and description**. eBay published no accuracy figures ([ValueAddedResource, Feb 2026](https://www.valueaddedresource.net/ebay-ai-magical-listing-revisited/)).
  - Product knowledge graph details: not found **[gap]**.
- **Amazon**
  - Lens Live (Sep 2025): an on-device detector plus a deep visual embedding matched against "billions" of products, with Rufus answering questions. No architecture details published ([GeekWire](https://www.geekwire.com/2025/amazons-lens-live-mobile-shopping-feature-uses-camera-and-ai-to-find-real-time-product-matches/)).
  - ABO dataset: §1.3. StyleSnap: not covered **[gap]**.
- **Google Shopping Graph**: more than 60B listings, about 2B updated per hour (Google figures, Nov 2025 and May 2026), now feeding agents in AI Mode and Gemini ([PPC Land, Sep 2026](https://ppc.land/googles-heiko-hotz-pitches-60-billion-listings-as-fuel-for-shopping-agents/)). No Lens technical details in the sources I opened.
- **Pinterest**
  - Unified Visual Embedding (KDD'19; [arXiv 1908.01707](https://arxiv.org/pdf/1908.01707)): multi-task proxy classification, with product *instance* labels (50k) as one of the tasks, then binarization. Shop-the-Look P@1 went from 33.0 to 52.8, and human-judged P@5 from 37.3% to 64.2%.
  - Complete-the-Look ([arXiv 2006.10792](https://ar5iv.arxiv.org/html/2006.10792)): a triplet style embedding, R@1 20.3.
  - OmniSearchSage (2024; [arXiv 2404.16260](https://arxiv.org/abs/2404.16260v1)): relevance +8%.
  - **PinCLIP (2026; [arXiv 2603.03544](https://arxiv.org/html/2603.03544v1))**: an in-house Hybrid-ViT-g plus SigLIP text encoders with a 2-layer fusion module. Trained on 890M Pins and 2.4B neighbor pairs, with MRL at 64/128/256 dims. Related-Pins image→image R@10 is 44.5 vs SigLIP2-g 35.7. Multimodal R@10 is 57.2 vs **Qwen3-VL-Embedding-8B 23.6**. Fresh repins +15%.
- **Zalando**: fashionID matching (§1.2) and the GPT-4o attribute copilot at about 75% accuracy and about 50k attributes per week (§2.1).
- **Depop**: one-photo AI listing (Sep 2024) that fills category, subcategory, color, and brand using in-house models. About 180k new listings per day. **No accuracy published** ([AOL/BI](https://www.aol.com/depops-ai-image-recognition-tool-165818029.html)).
- **ThredUp**: computer vision for item identification and tagging, an RL model for markdown pricing, more than 4M listings, about $400M in automation, 79.5% gross margin in Q2-25. No model details ([PYMNTS, Apr 2026](https://www.pymnts.com/?p=3671049)). Earlier Lily AI enrichment gave a 15% sell-through lift (search snippet only) **[UNVERIFIED]**.
- **Instacart PARSE** (Aug 2025; [blog](https://tech.instacart.com/multi-modal-catalog-attribute-extraction-platform-at-instacart-b9228754a527)): a multimodal LLM cascade from cheap to expensive models (70% cost cut on easy attributes). **Confidence comes from a second "is this value correct? yes/no" prompt, scored by the first-token probability of "yes"**. Low-confidence values go to human review. Multimodal input gave +10% recall over text-only.
- **Authentication**
  - **Entrupy**: hardware microscope attachment. Claims **99.1%** accuracy (vendor claim, not independently verified; [Macronomy](https://macronomy.substack.com/p/ai-luxury-authentication-entrupy-trust)). KDD 2017 paper: about 3M microscopic images, above 98% accuracy across fabrics, leather, and other materials ([Entrupy papers](https://ja.entrupy.com/papers)). Major brands only. (Blocked URL: `entrupy.com/about-us/`.)
  - **CheckCheck**: AI screening first, then 2 human authenticators, results in under 30 min. **No accuracy published** ([Sneaker Freaker, 2021](https://www.sneakerfreaker.com/features/great-apps-for-checking-the-legitimacy-of-sneakers)).
  - **Legit Check App**: certificate-based, no accuracy published (same source).
  - **Academic photo-only result**: Cypheme/Lacoste polo logos from smartphone photos reached **99.71% with a 3.06% rejection rate**. The authors say it is "highly unlikely to generalize" beyond that one brand and task ([arXiv 2410.05969](https://arxiv.org/html/2410.05969v2)).
- **Etsy, Farfetch, Lyst, Vinted**: no primary sources retrieved before the search budget ran out **[gap]**.

---

## 4. Failure modes, gaps, and calibration/abstention

- **Near-identical variants within a brand.** nyris found that near-identical instances and repetitive patterns break foundation models (Clips & Connectors: DINOv3 26.4 R@1 vs 63.4 for a domain model) [§1.2]. ImplicitAVE shows confusion between close values [§2.1]. FG-BMK shows species-level accuracy falling to about 61% [§2.1]. In LookBench, T-shirts, sweatshirts, and coats are the hardest categories.
- **Counterfeits.** Photo-only authentication is brand- and task-specific. The 99.7% result needed 3% rejection and was one brand. Entrupy uses microscopy hardware. No public cross-brand photo benchmark exists [§3].
- **Tag/label OCR.** The strongest open OCR is Qwen3-VL (OCRBench 920), but I found **no public benchmark for wrinkled or curved garment care labels and size tags** (the search was cut short). The RISE/Wargön second-hand dataset includes **brand-label close-ups** per item ([Zenodo](https://zenodo.org/records/12518734)). Verbalized calibration is *worse* on text embedded in images: instruction-tuned VLMs exceed ECE 0.4 ([arXiv 2505.20236](https://arxiv.org/abs/2505.20236)).
- **Condition grading.** The only public structured dataset I found is the **Clothing Dataset for Second-Hand Fashion v2**:
  - 31,997 used garments with front, back, and brand-label photos.
  - Labels: overall condition 1–5, pilling 1–5, and stains/holes/smell as none/minor/major.
  - License CC BY 4.0, from RISE with Wargön/Myrorna ([Zenodo](https://zenodo.org/records/12518734)).
  - A related thesis found CLIP beats MAE for second-hand retrieval and price estimation ([AI Sweden](https://my.ai.se/projects/247)).
  - No inter-annotator agreement numbers published.
- **Multi-object scenes and piles.** SAM 3 (848M parameters, SAM License, 3.1 released Mar 2026) does text-prompted "segment all instances of concept X". It scores 54.1 cgF1 vs a human 72.8 on SA-Co/Gold ([README](https://cdn.jsdelivr.net/gh/facebookresearch/sam3@main/README.md)). Outfit-level retrieval in LookBench is only about 47–53%.
- **Hallucinated IDs propagate.** In eBay's next-gen tool, the wrong ID flowed into the title, specifics, and description [§3]. VLMs are **systematically overconfident** (most have ECE above 0.25; [arXiv 2505.20236](https://arxiv.org/abs/2505.20236)).
- **Calibration and abstention methods.**
  - *Coverage at risk (C@R)* is the metric to optimize (the fraction answered at ≤R error). Variational fine-tuning (IVON instead of AdamW) cut ECE by 53–71% and raised C@1% from 28.4 to 37.0 at the same accuracy ([arXiv 2505.09591](https://arxiv.org/html/2505.09591v2)).
  - *Conformal prediction* gives distribution-free coverage guarantees. Conf-OT, for CLIP-style zero-shot models, makes the sets up to 20% more efficient under domain drift ([CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/html/Silva-Rodriguez_Conformal_Prediction_for_Zero-Shot_Models_CVPR_2025_paper.html)).
  - *The cost of guarantees, and how to cut it*: holding hallucination ≤5% with a conformal filter means abstaining on **more than 80%** of claims. **BCEA** adds a third action, "acquire more evidence" (zoom, crop, re-look), and recalibrates on post-acquisition scores. That keeps the guarantee and recovers coverage. Naively adding acquisition without recalibrating overshoots risk by up to 17 points ([arXiv 2606.16667](https://papers.cool/arxiv/2606.16667), Jun 2026). For us, the equivalent of acquiring evidence is asking the seller for a tag close-up.
  - *Self-verification probability*: Instacart's yes-token logit approach [§3].
  - *Human-in-the-loop*: Zalando's expert majority vote raised precision from 0.29 to 0.94 [§1.2].

---

## 5. Design literacy: style, era, designer, ontologies, compositional retrieval

- **Fashionpedia ontology** (ECCV 2020, Google/Cornell): **27 main garment categories, 19 apparel parts, 294 fine-grained attributes**, with relationships and segmentation masks ([ECCV](https://www.ecva.net/papers/eccv_2020/papers_ECCV/html/1203_ECCV_2020_paper.php)). License not stated on that page (the dataset is generally CC BY 4.0) **[UNVERIFIED]**.
- **LookBench taxonomy**: more than 100 attributes, pre-annotated by Qwen2.5-VL-72B, with about 93% correctness judged by an LLM [§1.2].
- **Getty AAT**: 55,661 concepts (Jan 2020). It has a **Styles and Periods** facet (e.g., Louis XIV, Chippendale) and an **Objects > Furnishings and Equipment** hierarchy that includes Costume. Released as Linked Open Data in Feb 2014 at vocab.getty.edu and updated every two weeks ([Wikipedia](https://en.wikipedia.org/wiki/Art_%26_Architecture_Thesaurus)). The ODC-By 1.0 license is widely reported but **[UNVERIFIED]** this session. AAT is the natural backbone for furniture and decor era/style labels (mid-century modern, Bauhaus, Memphis, etc.).
- **iMaterialist**: one of Marqo's 7 evaluation datasets [§1.1]. Details not retrieved **[gap]**.
- **Era classification and designer attribution**: I found no 2024–26 benchmark before the search budget ran out **[gap; likely thin literature]**.
- **Compositional (image + text-edit) retrieval, supervised SOTA**:
  - CIRR test R@1: **54.70** (PTHA with synthetic MTST triplets, [arXiv 2504.05316](https://arxiv.org/pdf/2504.05316)) and 54.05 (DQE-CIR, [arXiv 2603.04037](https://arxiv.org/abs/2603.04037)). Strong baselines are QuRe 52.2 and SPRC 50.8.
  - **FashionIQ R@10 average: 54.6–55.0** and R@50 about 76. Zero-shot CLIP-B/32 gets only 21.2 R@10 ([arXiv 2506.06602](https://arxiv.org/html/2506.06602v1)).
  - Generating modification texts from image pairs with an MLLM (808k CIRR and 579k FashionIQ synthetic triplets) is the current data recipe.
  - These numbers show that even the best "like this but in black suede" retrieval misses the target in the top 10 almost half the time.

---

## Recommended architecture for us

**Principle.** Use the VLM to *verify and explain*, not to *generate* the product ID. Generate candidates with retrieval and with deterministic code lookups. Then verify per attribute. Only commit when independent signals agree and the calibrated risk is under target. Otherwise, ask the seller for more evidence before abstaining.

### Seller side: photo → exact product

1. **Capture protocol (cheap, high leverage).** The app guides the seller through front, back, inner tag, size label, hardware or logo, and sole or base (for furniture: maker's mark and underside).
   - Zalando found clean front shots work best.
   - BCEA shows extra evidence recovers coverage that strict abstention would give up.
2. **Segment piles.** Use SAM 3 with text prompts ("shoe", "handbag", "jacket", "chair") to get one crop per item, plus crops of the tag/label region. Check the SAM License for commercial use.
3. **Hard-ID channel (deterministic).** OCR the tag crops with the frontier VLM, plus a fine-tuned Qwen3-VL-8B as a second opinion. Extract:
   - style or model codes (e.g., Nike `DD1391-100`), RN/CA numbers, and size strings;
   - origin and material composition.
   Run exact or fuzzy lookups against a product catalog that we license or scrape. A code match is the highest-precision signal. Treat it as near-ground truth when the OCR passes a checksum or format check and the visuals agree.
4. **Retrieval channel.** Fine-tune our own encoder:
   - **Primary: SigLIP2-So400m (Apache-2.0), warm-started from Marqo-FashionSigLIP-style fashion tuning.** It is the best open model in the nyris product benchmark and has a strong text tower for shopper queries. Train **image↔image separately from text↔image** (or keep the image head frozen when tuning text), because joint training hurt image→image by 9 points in one replication. Use pairs of seller/consumer photos and the verified catalog image for the same SKU, with hard negatives from the *same brand and line*. Use MRL (64/256/1152) for cheap ANN.
   - **Secondary: DINOv3-ViT-L fine-tuned for image-only instance matching**, used in the ensemble or re-ranker. GR-Lite shows fashion-tuned DINOv3 beating everything open on LookBench. Before production, have counsel review the DINOv3 License. PE-core-L (Apache) is the fallback.
   - Late-fuse with title and attribute text from the catalog side, as in Zalando fashionID, where text plus numeric features added about 9 AUCPR.
5. **VLM verifier and re-ranker (RAR pattern).** Feed the top-k (around 5–10) candidates, with their catalog images and attribute tables, alongside the seller crops. For each candidate the VLM outputs `same_product: yes/no/uncertain` plus per-attribute agreement covering colorway, hardware, stitching, logo placement, and size-tag match.
   - **Post-train Qwen3-VL-8B (Apache-2.0)**, with Qwen3.5-9B or Gemma 4 31B (both Apache-2.0) as alternates.
   - Training stages: (a) SFT on our structured schema, then (b) GRPO / Visual-RFT with **verifiable rewards**:
     - exact SKU match: +1;
     - attribute F1;
     - size-string exact match;
     - format;
     - **asymmetric abstain reward**: a confident wrong answer scores far below an abstention, and an abstention scores below a correct answer.
   - Optionally add InternVL3.5-style MPO preference training on rejected/accepted pairs that come from seller corrections.
   - Keep Claude as the high-capacity fallback and judge for hard cases and for writing descriptions.
6. **Calibrated gating.** Combine these into a meta-classifier such as gradient-boosted trees or logistic regression with isotonic calibration:
   - code-lookup match;
   - retrieval top-1 similarity and top-1/top-2 margin;
   - VLM yes-token probability (Instacart method), with self-consistency across N samples and across both VLMs;
   - ensemble agreement.
   Then set thresholds **per category with split-conformal risk control** so the target is, e.g., ≤0.5% wrong exact-ID at maximum coverage. Track C@0.5% and C@1% as headline KPIs.
   - Below threshold, take the "acquire" action first (ask for a specific photo), recalibrated on post-acquisition scores per BCEA. Next, offer the seller a confirmation list of the top 3 candidates. As a last resort, fall back to line-level ID ("Nike Dunk Low, colorway unconfirmed").
   - Fine-tune with IVON or ensembles to reduce overconfidence.
7. **Condition and authenticity heads.**
   - Condition: train on our own rubric, using the RISE dataset (CC BY 4.0) as a seed for the 1–5 overall, pilling, and stain/hole labels. Score each flaw with localized evidence (boxes) so the grade can be audited.
   - Authenticity: output a **risk score and the missing evidence**, never a verdict. Route high-value or high-risk items to a partner (Entrupy-style hardware or human authenticators). Brand-specific photo models are realistic only for the top counterfeited lines, with a rejection option (the Cypheme pattern).
8. **Human-in-the-loop and the data flywheel.** Every seller confirmation or correction and every sale becomes a labeled (photo → SKU, attributes, condition) pair. Feed these into contrastive hard-negative mining and RL preference data. Expert review on the uncertain slice can lift precision substantially (Zalando: 0.29→0.94).

### Shopper side: description or photo → listings

- An LLM parses free text into a **structured query over our ontology**. The ontology combines Fashionpedia (27 categories, 19 parts, 294 attributes), a LookBench-style attribute list, and **Getty AAT Styles & Periods** for era and movement, with a hand-built "designer lineage" graph of designer → house → era → signature motifs. Retrieval then runs in two parts:
  - (a) hard attribute filters over listing attributes extracted by the seller-side pipeline;
  - (b) a SigLIP2-tuned text→image embedding for soft aesthetics.
- **Compositional queries** ("this but longer, in black suede"): do not rely on CIR models, which score about 55 R@10 on FashionIQ. Decompose instead. Embed the reference image, have the VLM turn the modification into attribute deltas, then apply filters and re-rank. Later, train a CIR head on MTST-style synthetic triplets generated from our own listings.
- A VLM re-ranks the top 50 with a short explanation ("matches: 1970s, bias-cut, Ossie Clark-like print; differs: synthetic fabric"). That explanation is the visible design literacy.

---

## Biggest open gaps where we can lead

1. **Public benchmarks for consumer photo → exact variant, with size from the tag, do not exist.** LookBench (fine R@1 ≤67, no size or variant split) and nyris (furniture R@1 ≤66) are the closest. An internal "exact-variant + size + condition" benchmark built from second-hand seller photos would be a moat and an attractive data asset.
2. **No published system reports calibrated "near-zero confident error" product ID.** eBay, Depop, and Zalando publish no ID accuracy, or about 75% at attribute level. Conformal and BCEA-style "ask for evidence before abstaining" has been shown only on generic VQA. Applying it to product ID with per-category risk control is open territory.
3. **No dataset or benchmark for OCR on wrinkled, curved, or faded labels.** Style codes, RN/CA numbers, and size tags give exact-ID shortcuts that pure-vision approaches ignore.
4. **Condition grading lacks a standard rubric.** There is one public dataset (RISE, 32k items) and no inter-rater reliability work. A consistent, evidence-localized grade is a trust differentiator for buyers.
5. **Design literacy.** I found no benchmarks for era dating, designer attribution, or furniture style (the search was incomplete). Ontologies exist (AAT, Fashionpedia) but nobody links them to secondhand visual retrieval. Compositional retrieval SOTA is still weak (CIRR R@1 about 55).
6. **Furniture and design objects.** General encoders score about 57 R@1 on furniture instance retrieval, while a domain-trained model reaches 66 (nyris). Maker's-mark OCR combined with AAT style labels is not covered by any published system.
7. **Multi-item piles.** Concept segmentation is at about 75% of human (SAM 3), and outfit-level retrieval at about 50%. A pile-to-multi-listing pipeline with per-item verification is unsolved in public work.
8. **Authentication from ordinary phone photos across brands** has no published, generalizing results. The defensible position is a risk score with an evidence checklist and partner escalation.

---

## Coverage gaps in this research

The shared WebSearch budget ran out after about 55 searches by this agent. I could not retrieve primary sources for these, so they are unconfirmed:
- Etsy, Farfetch, Lyst, and Vinted engineering posts
- Amazon StyleSnap and product-matching papers
- eBay's product knowledge graph
- Google Lens technical details
- EVA-CLIP numbers
- Voyage multimodal embeddings
- Llama 4 vision
- Molmo and Gemma 3 licenses
- Qwen3-VL-Embedding and Gemini Embedding 2 model cards
- Era/designer classification literature
- DeepFashion In-shop and eProduct 2025 SOTA

Two URLs were blocked by unanswered permission prompts: `huggingface.co/Marqo/marqo-ecommerce-embeddings-L` and `entrupy.com/about-us/`. A follow-up turn can resume searching.
