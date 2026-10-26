# Post-training our own VLMs for resale: what the literature says, and what to do

Prepared 2026-10-25.

**Evidence tags**
- **[V]**: I read the claim in the primary source this session (paper PDF/HTML, official terms page).
- **[V-prev]**: verified in an earlier research pass (`research2/*.md`). I did not re-open the source here.
- **[3P]**: a third-party summary of a primary source.
- **[U]**: unverified.
- **[D]**: my own calculation from cited inputs.

**Access note.** The direct arXiv HTML pages for Qwen2.5-VL, Qwen3-VL, InternVL3.5 and InternVL3 were blocked on the first attempt, and the sandbox proxy blocks arxiv.org for curl. I read the same papers through the PDF links that search returned. I could not read **InternVL3 (2504.10479)** at all. **Section 7 (vision) of the Llama 3 paper** was cut off in the copy I could reach.

---

## 0. The answer in ten lines

1. **Post-training is not labeling.** Every 2025–26 VLM report uses the same recipe, and none of it uses large human labeling:
   - a few hundred thousand to a few million SFT examples, mostly synthetic or distilled, filtered by rules, reward models and **rejection sampling against ground truth**;
   - then **RL with verifiable rewards on only 10K–100K prompts**;
   - and a small human-written slice. Seed1.5-VL used about 13K crowdsourced SFT samples. Molmo used human speech captions.
2. **For a narrow task, curated SFT is tiny.** LIMA used 1,000 examples, LIMO 817, s1 1,000, MM-LIMA 200, Fine-R1 404. Volume comes from **automatically verified** data, not human-verified data.
3. **For perception, RL beats SFT on few-shot recognition, counting and detection, and generalizes better.** Visual-RFT went from 56.0 to 80.3 on one-shot fine-grained classification, while SFT got 51.7. **Explicit "thinking" hurts perception tasks** (No-Thinking-RFT 84.4 vs Thinking-RFT 81.3). SFT still wins on low-ambiguity tasks such as OCR and grounding.
4. **RL teaches policy, not knowledge.** It carries about 1 bit per episode. It does not add sub-category knowledge (Fine-R1's linear probe was unchanged). RLVR is bounded by what the base model can already reach. So knowledge of millions of SKUs has to come from **retrieval over catalogs and listings**, not from labels or RL. The VLM's job is to **verify, choose among candidates, abstain, or ask for a photo**.
5. **Calibration is trainable without new labels.** Adding a Brier term to the reward (RLCR) cut ECE from 0.37 to 0.03 with no loss of accuracy. Plain RLVR makes calibration *worse*. A ternary reward (wrong = −1, abstain = 0) cuts hallucination. RL can teach a model to **ask for another view** (ProactiveBench: 11.0% to 37.4%), as long as asking pays less than a correct answer.
6. **"Near-zero confident errors" is a statistical claim.** It needs a held-out calibration set and risk-controlled thresholds per category. Certifying a confident-error rate of ≤1% at 95% confidence takes about 300–800 *answered* items per category group [D].
7. **Our training signal is already in the world:**
   - style codes, GTINs and RN numbers on tags;
   - retail catalogs;
   - structured listing fields;
   - cross-listed duplicates;
   - sold, not-returned listings.

   These give **programmatic verifiers**. They are what Qwen, Seed and GLM call "rule-based rewards" and rejection-sampling filters.
8. **Distilling from frontier APIs is restricted.**
   - **Anthropic:** "We prohibit customers from using our services to train or develop AI models without our written permission," and it lists "Using Outputs as training targets for models" as prohibited.
   - **OpenAI:** allows classifiers only if they are "not distributed or made commercially available to third parties."
   - **Google:** bars "models that compete with the Services."
   - **So use Apache-2.0 open teachers** (Qwen3-VL-235B, Gemma 4, InternVL3.5) for anything that becomes a training target, or get written permission.
9. **Compute is cheap.** SFT of an 8B VLM on 100K multi-photo items is about 20 H100-hours per epoch [D]. A GRPO run on 10–20K prompts is tens to about 100 H100-hours [D]. A full first quarter of experiments fits in roughly **$5–20K of GPU time**. People and evaluation are the real cost.
10. **Train two models first:**
    - **(A) a calibrated product-ID verifier** (retrieve, then verify/select/abstain/ask);
    - **(B) a tag and label reader** (tag photo to brand, RN, size system, materials, style code, GTIN, with checksums).

    Both are cheap to supervise and verifiable. Both are useful on their own, and both feed everything else.

---

## 1. How leading labs post-train (2024–2026)

### 1.1 VLM technical reports

| Model | Stages | Data sizes per stage | Data sources | What moved the needle / lessons | Compute |
|---|---|---|---|---|---|
| **Qwen2.5-VL** (Feb 2025) [V] [PDF](https://arxiv.org/pdf/2502.13923) | 3-stage pretrain (1.5T + 2T + 0.6T = 4.1T tokens), then **SFT, then DPO**; ViT frozen in post-training; no RL described | SFT **~2M entries, 50% text / 50% multimodal**; DPO size not stated | Open-source, purchased, and online query data. **Rejection sampling**: an intermediate model generates; "Only samples where the model's output matches the expected answers are retained". Reward-model scoring of queries and answers. Grounding via synthesis with Grounding DINO and SAM; 1M synthetic charts; 6M tables auto-recognized and filtered | Heavy filtering pipeline (domain tagger, rule filters, RM filters); synthetic document, OCR and chart data | Not stated |
| **Qwen3-VL** (Nov 2025) [V] [PDF](https://arxiv.org/pdf/2511.21631) | SFT (32K then 256K context), then long-CoT cold start (thinking models), then strong-to-weak distillation (small models; off- and on-policy KL), then **reasoning RL**, then **general RL** | SFT **~1.2M** (1/3 text); reasoning RL **~30K queries**; "thinking with images" **~10K** grounding SFT, then **~120K** distilled multi-turn agentic trajectories | Open-source, web, synthesized; manual annotation for some RL queries | RL queries filtered by sampling 16 responses: drop all-wrong; **drop >90% pass-rate**. **Rule- or code-verified rewards**, no format reward. General RL **targets flawed SFT priors with counting and clock tasks**. Hybrid rule and model-judge rewards. **A tool-call-count reward was added because models collapsed to a single tool call** | Not stated |
| **InternVL3.5** (Aug 2025) [V] [PDF](https://arxiv.org/pdf/2508.18265) | SFT, then **Cascade RL: offline MPO, then online GSPO**, then ViCO (for Flash) | SFT **~56M samples / ~130B tokens**; MPO **~200K pairs** (MMPR-v1.2); GSPO **~70K queries** (MMPR-Tiny) | Reused InternVL3 SFT data plus "thinking" data. Per the HF card [V], InternVL3-78B descriptions were fed to DeepSeek-R1, keeping only correct answers | GSPO keeps queries whose rollout accuracy is **between 0.2 and 0.8**. "Up to +16.0%" overall reasoning vs InternVL3. Claims Cascade RL gets gains "at a fraction of the GPU time" (ablation numbers are only in images [U]) | Not in the text I could read |
| **Molmo / PixMo** (Ai2, Sep 2024) [V] [arXiv](https://arxiv.org/pdf/2409.17146) | Caption pretraining, then SFT. **No RLHF** | PixMo-Cap **712K images / ~1.3M captions** from **spoken** 60–90 s descriptions; Points 2.3M; AskModelAnything 162K; CapQA 214K; Docs 2.3M QA (LLM-generated); Clocks 826K | Human speech plus LLM cleanup; explicitly **avoids distilling proprietary VLMs** | Molmo-72B 11-benchmark average 81.2 vs GPT-4o 78.5. **Key nuance:** training on **GPT-4o captions of the same PixMo images "performs strongly" too**, while ShareGPT4V captions did worse. The advantage came largely from **image diversity and distribution**, not from humans per se. Caption F1 correlates with downstream average at ρ = 0.82 across 22 ablations | Not stated |
| **LLaVA-OneVision** (Aug 2024) [V] [HTML](https://arxiv.org/html/2408.03326v3) | Align (558K), then high-quality knowledge (4M), then single-image (3.2M), then OneVision (1.6M) | As listed | **99.8% of the high-quality knowledge data is synthetic** (re-captioned by LLaVA-NeXT-34B, "an early version of the model itself") | "Quality over quantity" is stated as an axiom, not ablated | Not read |
| **Cambrian-1** (NeurIPS 2024) [V] [PDF](https://proceedings.neurips.cc/paper_files/paper/2024/file/9ee3a664ccfeabc0da16ac6f1f1cfe59-Paper-Conference.pdf) | Instruction-tuning study | Curating **10M down to 7M** raised the average from 54.8 to 55.9 (+2.7 vision-centric) | Public data plus a targeted "data engine" | **Per-source caps of 250–350K**; balance general, OCR and language; system prompts against the "answer machine" effect | — |
| **Gemma 3** (Mar 2025) [V] [report copy](https://52nlp.cn/wp-content/uploads/2025/03/Gemma3技术报告英中对照版.pdf) | **Distillation from a large instruction-tuned teacher**, then RL (improved BOND, WARM, WARP) | Not stated | Teacher outputs; reward sources are weight-averaged reward models, **code execution, ground-truth math** | Including data that "encourage[s]... **hedging, and refusals**" reduces hallucination. Frozen 400M SigLIP at 896 px with Pan & Scan | — |
| **Gemma 4** (Apr 2026) [3P] [Gigazine](https://www.gigazine.net/gsc_news/en/20260403-google-released-gemma-4) | Not disclosed | — | — | **Apache-2.0**; E2B, E4B, 26B-A4B, 31B; all multimodal | — |
| **Llama 3 (text template)** [V] [PDF copy](https://www.rivista.ai/wp-content/uploads/2024/11/2407.21783v2.pdf) | **6 rounds** of (reward model, rejection sampling with K = 10–30, SFT, DPO) | Not totaled | Human preferences plus RS | Top-quartile RM data is treated as high quality. Vision Section 7 **not read [U]** | — |
| **Llama 4** [3P] [arXiv 2601.11659](https://arxiv.org/pdf/2601.11659) (not by Meta) | **Lightweight SFT, then online RL on hard prompts, then lightweight DPO** | — | — | Removed >50% of "easy" SFT data using Llama-as-judge; continuous hard-prompt filtering during RL | — |
| **Seed1.5-VL** (May 2025) [V] [PDF](https://arxiv.org/pdf/2505.07062) | SFT, then **hybrid RLHF + RLVR (PPO)**, then **4 rounds of rejection-sampling fine-tuning** | SFT **~50K multimodal** = **~13K crowdsourced** + **30K selected from a 1.5M open pool**, plus text and LongCoT; RLVR **>1M STEM** problems, **>20K synthetic puzzles**, "spot the difference" boxes | Human (small), filtered open data, synthetic | Drop questions with 0% or >75% accuracy. **Remove text-answerable questions** so RL cannot learn shortcuts. KL only on RM-scored prompts (1e-5), none on verifiable ones. Reward only the final answer, not the CoT. "A stronger cold-start SFT naturally leads to a stronger final model" | **RL 60K GPU-h; RM 24K GPU-h; pretraining 1.3M GPU-h** |
| **MiMo-VL** (Jun 2025) [V] [PDF](https://arxiv.org/pdf/2506.03569) | 4-stage pretrain (2.4T tokens, **synthetic long-CoT inside pretraining**), then **MORL** (mixed on-policy RL) | 80K visual reasoning problems plus others; vanilla GRPO plateaus around 20K samples | Synthetic reasoning | **Rewards:** GIoU for boxes; point-in-box; count accuracy; temporal IoU. A reward router serves rewards as services. **Interference:** reasoning lengthens CoT while grounding and counting shrink it | — |
| **Kimi-VL** (Apr 2025) [V] [PDF](https://arxiv.org/pdf/2504.07491v1) | Joint SFT (32K then 128K), then long-CoT SFT ("small yet high-quality"), then RL (online mirror descent, binary reward plus length penalty) | Not stated | Rejection-sampling-style long-CoT from Kimi k1.5 | Synthetic data in cooldown gave "significant" gains | 4.4T pretraining tokens |
| **GLM-4.1V / 4.5V** (Jul 2025) [V] [HTML](https://arxiv.org/html/2507.01006v6) | Long-CoT SFT, then **RLCS** (curriculum-sampled RL) | Not stated | Mixed | **"any weakness in the reward signal for a single capability can derail the entire training."** A counting task was gamed with "a correct number between 0 and 10". **Verifiers:** OCR reward = 1 − edit distance / max length; grounding = fraction of boxes above an IoU threshold. Cold start of 1,000 vs 2,000 steps converged to the same result after RL | — |

### 1.2 Text post-training references (the template)

| Work | What it shows | Numbers |
|---|---|---|
| **Tülu 3** [V] [PDF](https://arxiv.org/pdf/2411.15124) | SFT, then DPO, then RLVR, fully open | SFT **939,344 prompts** (from 23.3M candidates). DPO **271K pairs (8B) / 334K (70B)**, labeled by **GPT-4o as judge** on 4 aspects. 8B scores SFT, DPO, final: GSM8K 76.2, 84.3, 87.6; IFEval 72.8, 81.1, 82.4. **Compute:** 8B SFT 32 H100 × ~6 h; 8B DPO 8 H100 × ~10 h; 70B SFT 64 × ~50 h. On-policy preference data helps. **Duplicating prompts (64K to 383K) did not help.** Kept an unseen eval suite they did not look at during development |
| **DeepSeek-R1** [V] [HTML](https://arxiv.org/html/2501.12948v1) | Pure-RL emergence (GRPO, rule rewards). No neural RM "because... reward hacking" | R1-Zero AIME 15.6 to 71.0. R1 uses "thousands" of cold-start examples, then RL, then **800K** rejection-sampled SFT (600K reasoning + 200K other), then RL. **Distillation beats RL for small models:** Qwen-32B distilled 72.6 vs RL-only 47.0 (AIME). PRM and MCTS failed |
| **LIMA** [V] [ar5iv](https://ar5iv.labs.arxiv.org/html/2305.11206) | Superficial-alignment hypothesis | **1,000 examples** (750 forum, 250 hand-written) on LLaMA-65B. Equal or preferred to GPT-4 in 43% of cases. Up to 16× more data plateaued; prompt diversity mattered |
| **s1** [V] [HTML](https://arxiv.org/html/2501.19393v2) | Small curated set plus budget forcing | **1,000** examples picked from 59K by quality, difficulty and diversity. **Training on all 59K gave no substantial gain.** Fine-tune took **26 min on 16 H100s** for 32B. Traces came from the Gemini Thinking API |
| **LIMO** [V] [HTML](https://arxiv.org/html/2502.03387v1) | Curation by difficulty and chain quality | **817 samples** beat 100K–114K-sample sets (AIME24 57.1 vs 50.2 for OpenThoughts-114K). Top-quality vs bottom-quality chains: about 15 points on AIME |

### 1.3 Synthesis: the 2026 recipe and what transfers to us
- **Pretraining and mid-training put knowledge in. Post-training shapes behavior.** Kimi-VL, MiMo and Seed all add synthetic data in mid-training. For us, "mid-training" means **continued SFT on large automatically verified in-domain data** (see eBay below), not pretraining from scratch.
- **SFT data is mostly machine-produced and then filtered.** The filters are:
  - ground-truth match (rejection sampling);
  - rule checks;
  - reward-model or judge scores;
  - **difficulty filtering**: drop what the model already solves or can never solve.

  Human data is a small, high-leverage slice: Seed's 13K, Molmo's captions, LIMA's 1K.
- **RL needs prompts with a checkable answer, not labeled demonstrations.** Sizes are 10K–100K prompts:
  - Qwen3-VL ~30K;
  - InternVL3.5 ~70K;
  - Seed >1M STEM (frontier scale).

  Filter prompts to an intermediate pass rate (0.2–0.8, or drop >90%).
- **The reward is the product.** GLM, VLM-R1 and Qwen3-VL all report collapse or hacking from a single weak verifier.
- **What humans did at labs:** set the data distribution (Molmo), write a small exemplary slice (Seed, LIMA), and build **evals**. They did not label millions of items.

---

## 2. Perception-focused RL and data efficiency

| Paper | Setup | Data | Result | Lesson |
|---|---|---|---|---|
| **Visual-RFT** [V] [HTML](https://arxiv.org/html/2503.01785v1) | Qwen2-VL-2B/7B, GRPO | **1–16 shots**; "around 100 samples" for one-shot classification; LISA 239 images | One-shot fine-grained classification (Flowers, Pets, FGVC, Cars) **56.0 to 80.3 (RL) vs 51.7 (SFT, below baseline)**. COCO 2-shot mAP 19.6 to 41.5 vs SFT 21.0. LISA mIoU 26.9 to 37.6 vs SFT 28.3 | Reward = accuracy plus format; for detection, IoU plus confidence plus format. **SFT on tiny data hurts; RL helps** |
| **To Think or Not To Think (No-Thinking-RFT)** [V] [HTML](https://arxiv.org/html/2503.16188v6) | Qwen2-VL-2B/7B, 4-shot, 11 classification datasets | 4 per class | Average: zero-shot 62.21, SFT 70.65, **Thinking-RFT 81.25, No-Thinking-RFT 84.39**. ImageNet fine-tune time: SFT 35 min, Thinking 1,587 min, **No-Thinking 94 min** | **Drop CoT for perception**: better and about 17× cheaper. Thinking helps math (7B MathVista 64.6 vs 59.1). "Free lunch" cross-dataset transfer |
| **Fine-R1** (ICLR 2026) [V] [HTML](https://arxiv.org/html/2602.07605) | Qwen2.5-VL-3B/7B; CoT SFT, then TAPO (DAPO plus positive-pair and hard-negative augmentation) | **404 CoT samples** plus **4 shots per seen class**, 6 fine-grained datasets | 7B: seen 91.71 / unseen 85.70 (+7.73 / +9.28 over base; **beats SigLIP-L**). SFT alone: +3.98 seen, **−6.12 unseen** | **Linear probe unchanged (84.26 vs 85.00):** RL does not add knowledge, it "deploys" it. Contrasting against hard negatives works (ideal for colorway vs colorway). Ran on 4 × A6000 |
| **Perception-R1** (NeurIPS 2025) [V] [HTML](https://arxiv.org/html/2504.07954v1) | Qwen2-VL-2B / Qwen2.5-VL-3B, GRPO | **5K grounding, 5K OCR, 10K counting**, 110K detection | Counting +17.9; COCO **31.9 AP (RL) vs 25.9 (SFT)**; RefCOCO+ +4.2 | **Thinking hurt all four perception tasks.** RL beats SFT on high "perceptual perplexity" tasks (counting, multi-object). **SFT is as good or better for OCR and grounding.** Hungarian matching in the reward matters (31.9 vs 23.5 without). More rollouts help |
| **VLM-R1** [V] [PDF](https://arxiv.org/pdf/2504.07615) | Qwen2.5-VL-3B, REC + OVD | RefCOCO splits; D3 | In-domain RL vs SFT about +2; **out-of-domain LISA 63.14 vs 54.82** | **Reward hacking:** an mAP reward made the model list every category (score 0.99 for junk output). Fixed with a redundancy-penalized reward (`odLength`) |
| **R1-V** [3P] [MarkTechPost](https://www.marktechpost.com/2025/02/04/deep-agent-released-r1-v-reinforcing-super-generalization-in-vision-language-models-with-cost-effective-reinforcement-learning-to-outperform-larger-models/) | 2B, counting (CLEVR) | CLEVR-70K | Out-of-domain beats 72B; **8 A100 × 30 min, $2.62** | Order of magnitude for cost only [3P] |
| **SFT Memorizes, RL Generalizes** [V] [HTML](https://arxiv.org/html/2501.17161v2) | Rule and visual variants | — | RL out-of-domain gains on visual variants (+17.6 / +61.1) while SFT declined. **RL improved underlying visual recognition.** **SFT is needed first to stabilize format** | SFT, then RL ordering |
| **Vision-R1** [V] [HTML](https://arxiv.org/html/2503.06749v4) | 7B math reasoning | 200K distilled cold-start CoT, **10K** RL | MathVista 73.5 | **Over-thinking:** correct chains are short; limit length early |
| **ProactiveBench** (2026) [V] [PDF](https://arxiv.org/pdf/2603.19466) | MLLMs asking the user for an intervention (move the occluder, change the view) | GRPO on QuickDraw + COCO | Qwen2.5-VL-3B average **11.0% to 37.4%** (beats o4-mini 34.0). Transfers to unseen scenarios | **Reward for a valid "ask" must be below a correct answer** (r_p = 0.5–0.75). r_p = 1.0 causes over-asking. This is directly our "request a specific photo" behavior |
| **Limits of RLVR** [V] [abs](https://arxiv.org/abs/2504.13837v4) | — | — | RLVR raises pass@1, but the base model wins pass@k at large k. **Distillation can add new patterns; RL mostly cannot** | Knowledge has to come from SFT or retrieval |
| **RL's Razor** [V] [HTML](https://arxiv.org/html/2509.04259v1) | Qwen2.5-3B, OpenVLA-7B | — | RL matches SFT on the new task but **forgets less**. Forgetting tracks KL to the base policy (R² 0.71 for LLMs) | Prefer on-policy RL, or KL-light SFT, to keep general skills |
| **LoRA Without Regret** [V] [Thinking Machines](https://thinkingmachines.ai/blog/lora/) | — | — | LoRA matches full fine-tuning on small and medium SFT; **matches it in RL even at rank 1**. Apply to all layers incl. MLP; LR about 10× full FT; about 2/3 the FLOPs | **RL absorbs ~1 bit per episode**, so it cannot teach a catalog |

### When RL beats SFT, for our tasks
- **RL wins on these tasks:**
  - choosing among visually similar candidates (fine-grained ID, colorway, era);
  - counting and multi-object flaw detection;
  - abstain-or-ask decisions;
  - calibration;
  - generalizing to new categories and photo conditions.

  RL also needs **far fewer examples**: hundreds to low thousands per task, versus tens of thousands.
- **SFT wins, or is required, on these:**
  - output schema and format;
  - low-ambiguity transcription (tag OCR, Perception-R1);
  - **injecting knowledge** (brand and line vocabulary, style-code formats, size systems).

  SFT also has to come first to stabilize the format.

### Reward design that worked for perception
- Exact match for classes, after normalization.
- IoU or GIoU for boxes, with **Hungarian matching** for multiple objects.
- F1 for sets, with **redundancy and length penalties**.
- 1 − normalized edit distance for OCR.
- Point-in-box for pointing.
- Count accuracy for counting.

### Pitfalls
- **Single-verifier hacking:** GLM counting; VLM-R1 mAP.
- **"Thinking" hurting perception.**
- **Text-answerable prompts teaching shortcuts:** Seed removes them. For us, the title text must never be in the input when the label came from that title.
- **Interference** between long-reasoning and perception tasks (MiMo-VL).
- **All-correct or all-wrong groups give zero gradient**, so filter to a 0.2–0.8 pass rate.

---

## 3. Calibration and abstention through post-training

| Method | Mechanism | Evidence |
|---|---|---|
| **R-Tuning** [V] [HTML](https://arxiv.org/html/2311.09677v2) | SFT targets with "I am sure / unsure", set by whether the *model's own* prediction matched the label | ECE 0.255 to 0.018 (ParaRel ID, 3B). Refusal works as a transferable meta-skill. Out-of-domain results are mixed |
| **RLCR** ("Beyond Binary Rewards", ICLR 2026) [V] [PDF](https://arxiv.org/pdf/2507.16806) | R = 1[correct] − (q − 1[correct])²: **a Brier proper scoring rule on verbalized confidence**; GRPO; provably rewards both accuracy and calibration | HotpotQA **ECE 0.37 (RLVR) to 0.03** at the same accuracy. Out-of-domain average ECE: **0.46 (RLVR) vs 0.40 (base) vs 0.21 (RLCR)**, so **standard RLVR makes calibration worse**. Log-score variant collapsed; **use bounded Brier**. Trained on 20K + 15K examples |
| **Rewarding Doubt** (ICLR 2026) [V] [HTML](https://arxiv.org/html/2503.02623v4) | Log-score reward on a 0–10 confidence; PPO with LoRA on Llama-3-8B | TriviaQA ECE 0.346 to 0.023; AUROC 0.586 to 0.859. Some out-of-domain transfer (MedQA AUROC 0.51 to 0.66) |
| **TruthRL** (Meta, 2025) [V] [HTML](https://arxiv.org/html/2509.25760v1) | **Ternary reward: correct +1, abstain 0, wrong −1** | Hallucination down 28.9% vs vanilla RL (abstract). Table rows show **accuracy can drop** (Qwen 7B average 18.6 vs 28.6 binary), so tune the penalty |
| **OpenAI, "Why language models hallucinate"** [V] [blog](https://openai.com/index/why-language-models-hallucinate/?so=1) | Accuracy-only grading rewards guessing; "Penalize confident errors more than you penalize uncertainty" | SimpleQA: gpt-5-thinking-mini abstains 52%, 26% errors; o4-mini abstains 1%, 75% errors, at a similar ~22–24% accuracy |
| **Reliable VQA** (ECCV 2022) [V] [abs](https://arxiv.org/abs/2204.13631) | Learned selector on top of the VQA model | Softmax gating gives **under 7.5% coverage at 1% risk**. Selector raises coverage **6.8% to 15.6%** (2.3×). Proposes "Effective Reliability," which costs errors more than abstentions |
| **CAP: conformal abstention for LLMs and VLMs** [V] [HTML](https://arxiv.org/html/2502.06884v1) | Two conformal thresholds (predict, set, abstain), tuned by RL | About 90% coverage target met empirically on LLaVA-1.6. Hallucination AUROC 0.80 (34B). **The RL-tuned version loses the formal guarantee.** Use plain split-conformal or risk control for the guarantee |
| **Gemma 3** [V] | Hedging and refusal data in SFT | Reported to reduce hallucination (qualitative) |
| VLM overconfidence; IVON | Most VLMs have ECE >0.25. Variational fine-tuning raised coverage at 1% risk from 28.4 to 37.0 | [V-prev] [2505.20236](https://arxiv.org/abs/2505.20236), [2505.09591](https://arxiv.org/html/2505.09591v2) |

### How to get "never wrong when confident". No single method does it; stack these layers.
1. **Make the decision evidence-grounded and closed-set.** Retrieve K catalog or listing candidates. The VLM picks one, picks "none of these," abstains, or asks for a photo. Generative open-vocabulary ID is where wrong IDs come from (the eBay mousepad case [V-prev]). RAR shows retrieve-then-rank beats either alone [V-prev] ([2403.13805](https://arxiv.org/html/2403.13805v1)).
2. **Train calibrated confidence into the policy.** Use an RLCR Brier term per field plus a ternary penalty for confident wrong answers.
3. **Train an "ask" action** with a cost (ProactiveBench, r_p < 1). This is cheap to simulate from multi-photo listings (§8.3).
4. **Add independent agreement signals:**
   - retrieval margin;
   - deterministic code match (style code, GTIN, RN);
   - self-consistency across sampled answers;
   - a second, smaller verifier model.

   Reliable VQA's learned selector more than doubled coverage at 1% risk.
5. **Set thresholds per category group with split-conformal or Learn-then-Test risk control** on a held-out calibration set. The guarantee holds under exchangeability. Re-certify whenever the input distribution shifts (new category, new app camera flow).
6. **Monitor in production** with a small, continuous human audit plus PPI (§5).

---

## 4. Where the training signal comes from without a labeling army

### 4(i) Existing structured data: listings, catalogs, sold listings
- **Evidence it works:**
  - **eBay** turned about 15M raw listings into about 4M instruction examples. A VLM captioned each image and an LLM **kept only aspects verifiable from the caption or image**. The paper calls raw listings "rather noisy... or just simply wrong inputs" [V] ([2602.11733](https://arxiv.org/html/2602.11733)).
  - On 100K multi-image items labeled by GPT-4.1, then refined with bbox crops, fine-tuned **Gemma3-4B reached 53.8 F1 vs zero-shot Gemma3-27B 44.8**. Refined labels raised all sizes by 3.3–6.4 F1 [V] ([PDF](https://arxiv.org/pdf/2602.11733)).
  - **Marqo-FashionSigLIP:** over 1M products, with titles, descriptions, colors, categories and materials as supervision. Text-to-image R@1 +57% vs FashionCLIP2.0 [V] ([blog](https://marqo.ai/blog/search-model-for-fashion)).
  - **WDC product matching:** schema.org GTIN, MPN and SKU identifiers used as distant supervision gave 26M offers in 16M clusters and **20.7M positive pairs**. Models trained on it reached **F1 of about 0.89–0.92** on a hand-verified gold set [V] ([PDF](https://www.uni-mannheim.de/media/Einrichtungen/dws/Files_Research/Web-based_Systems/pub/ECNLP_19_PrimpeliPeetersBizer.pdf)).
- **Failure modes:**
  - Seller fields are wrong or missing (eBay). SKU fields are vendor-scoped: over 19% of WDC "global" identifiers were actually `sku`.
  - Studio catalog photos differ from user photos.
  - Popular items dominate.
  - Titles leak the answer, so strip them from model inputs.
  - Web-supervised data typically has about 20% noise (WebVision: "About 20% of images are considered as true noisy images") [V] ([ar5iv](https://ar5iv.arxiv.org/html/1708.02862)). Yet web-trained models matched ImageNet-trained transfer: Caltech-256 70.43 vs 70.44.
- **Mitigations:**
  - triangulation (§8.2);
  - confident-learning pruning of likely label errors (≈10% data removed with modest gains) [V] ([1911.00068](https://arxiv.org/pdf/1911.00068));
  - per-source caps (Cambrian, 250–350K).

### 4(ii) Self-supervision and consistency
- **The same item seen several times:**
  - multi-photo listings;
  - the same seller cross-listing on several platforms (near-identical photos, different titles and fields);
  - relists after a price drop.

  These give **free positives** for instance embeddings and **consistency targets**: the model's ID from photo subset A should equal its ID from subset B.
- **Evidence:**
  - Pinterest found engagement-mined and human labels complement each other, and multi-task over all sources beat any single source [V-prev] ([1908.01707](https://arxiv.org/pdf/1908.01707)).
  - Fine-R1's intra-class pooling and inter-class KL are exactly a "same item / similar-but-different item" consistency objective [V].
- **Failure mode:** consistency is not correctness. A model can be consistently wrong. Use it as an auxiliary signal or a hard-negative miner, never as the only reward.

### 4(iii) Programmatic verification, used as verifiable rewards and as label filters

| Verifier | What it checks | Source |
|---|---|---|
| **GTIN / UPC / EAN check digit** | Validates an OCR'd barcode number (mod-10) before a catalog lookup | [Wikipedia: check digit](https://en.wikipedia.org/wiki/Check_digit) [V-search] |
| **FTC RN lookup** | US textile-label RN maps to the company, a cross-check on brand | FTC: "The RN Look-Up Service can be accessed through the Business Guidance Page" [V] ([FTC](https://www.ftc.gov/node/43948)) |
| **Style-code regex plus catalog lookup** | For example Nike `AA1234-100`; the catalog returns model, colorway and release | [U: per-brand formats to be compiled] |
| **Size-system consistency** | US/UK/EU/JP conversions; label vs measured | Rules |
| **Material % sum = 100** | Fiber-content parse | Rules |
| **Catalog image-embedding agreement** | Listing photos vs catalog images of the predicted SKU | Embedding model |
| **Furniture marks** | IKEA article numbers, manufacturer labels and dates | [U: compile per maker] |

These are the same kind of rule-based verifiers Qwen3-VL, Seed and GLM use. **GLM's lesson applies:** any weak verifier will be gamed. For example, if the reward only checks "GTIN is valid," the model will emit valid but wrong GTINs. **Reward match to ground truth. Use validity only as a filter.**

### 4(iv) Distillation from strong models, with verification
- **Evidence:**
  - Qwen2.5-VL and Qwen3-VL rejection sampling keeps only outputs matching ground truth [V].
  - InternVL3.5 and Vision-R1 distill DeepSeek-R1 traces and filter on correct answers [V].
  - DeepSeek's distilled small models beat small-model RL (72.6 vs 47.0) [V].
  - **Weak-to-strong:** a strong student trained on weaker labels recovers about half the gap to ground truth, and about 80% with a confidence loss [V] ([2312.09390](https://www.arxiv.org/pdf/2312.09390)). So a student can surpass a noisy teacher.
  - Molmo found GPT-4o captions of the right images about as good as human captions [V].
  - **Industry:** eBay (GPT-4.1 labels to a 4B student) and Etsy (o3 to a Qwen3-VL-4B teacher to a BERT student) [V-prev] ([Etsy](https://www.etsy.com/codeascraft/how-etsy-uses-llms-to-improve-search-relevance)).
- **Failure modes:** the student inherits teacher biases and blind spots on the long tail; licensing (below).

### 4(v) Synthetic data
- **Evidence:**
  - Qwen2.5-VL uses synthetic OCR, documents and 1M synthetic charts [V].
  - LLaVA-OV's knowledge stage is 99.8% synthetic [V].
  - Seed uses 20K synthetic puzzles and synthetic spot-the-difference [V].
  - DRAEM-style anomaly simulation trains surface-defect detectors without real defects. Its abstract claims a large-margin state of the art on MVTec; I did not read the numbers [V-abstract] ([2108.07610](https://arxiv.org/abs/2108.07610v2)).
- **Good uses for us:**
  - **rendered tags** (fonts, RN, care symbols, size systems, blur, wrinkles, glare);
  - **inpainted flaws** (stains, holes, pilling) for localization pre-training;
  - augmentations (crops, lighting).
- **Failure modes:**
  - the synthetic-to-real gap;
  - **model collapse** when recursively trained on generated data: "irreversible defects... tails of the original content distribution disappear" [V] ([Shumailov, Nature 2024](https://oatml.cs.ox.ac.uk//publications/202407_Shumailov_ModelCollapse.html)).

  Always keep real data in the mix and evaluate only on real photos.

### 4(vi) Terms of service: can we distill from Claude, GPT or Gemini?

**Anthropic Commercial Terms** (effective Jun 17, 2025) [V] ([anthropic.com/legal/commercial-terms](https://www.anthropic.com/legal/commercial-terms)), §D.4:

> "Customer may not and must not attempt to (a) access the Services to build a competing product or service, including to train competing AI models or resell the Services except as expressly approved by Anthropic; (b) reverse engineer or duplicate the Services; or (c) support any third party's attempt at any of the conduct restricted in this sentence."

Outputs: "Customer... owns its Outputs."

**Anthropic Help Center, "Can I use my Outputs to train an AI model?"** (Mar 16, 2026) [V, via summarizer, quotes ≤125 chars] ([support.claude.com](https://support.claude.com/en/articles/12326764-can-i-use-my-outputs-to-train-an-ai-model)):

> "We prohibit customers from using our services to train or develop AI models without our written permission."

- Listed as permitted (models that don't compete): "Sentiment analysis tools," "Content categorization systems," "Summarization tools," **"Information extraction tools,"** "Semantic search tools," "Anomaly detection tools."
- "Uses that are prohibited include:" "General purpose chatbots," "Models designed for open-ended text generation," **"Using Outputs as training targets for models,"** "Reverse engineering training methods."

**Reading:** a product-ID or tag-extraction VLM looks like "information extraction" and "categorization." But the page also says training needs written permission, and it bans outputs as training targets. **Do not use Claude outputs as SFT targets without written permission from Anthropic.**

**OpenAI Business Terms** [V] ([openai.com/policies/business-terms](https://openai.com/policies/business-terms)), §2(e):

> "use Output (as defined below) to develop any artificial intelligence models that compete with our products and services. However, you can use Output to (i) develop artificial intelligence models primarily intended to categorize, classify, or organize data (e.g., embeddings or classifiers), as long as such models are not distributed or made commercially available to third parties and (ii) fine tune models provided as part of our Services"

The OpenAI Services Agreement (v.010126) has the same "Permitted Exception" [V] ([PDF](https://cdn.openai.com/osa/openai-services-agreement.pdf)).

**Reading:** an internal classifier is OK. **Selling the model or its API to others is not OK** if it was trained on OpenAI outputs. That matters for the "independently useful model" strategy (§7).

**Gemini API Additional Terms** (last updated 2026-04-28) [V] ([ai.google.dev/gemini-api/terms](https://ai.google.dev/gemini-api/terms)):

> "You may not use the Services to develop models that compete with the Services (e.g., Gemini API or Google AI Studio)."

The page also says "reverse engineer, extract or replicate any component of the Services." A narrow product-ID model arguably does not compete with the Gemini API. A general multimodal API would. Vertex AI terms were not checked [U].

**Open-weight teachers:**
- **Qwen3-VL-235B-A22B is Apache-2.0** (released Sep 22, 2025) [3P] ([llm-stats](https://llm-stats.com/models/qwen3-vl-235b-a22b-instruct)). Apache has no output restrictions.
- **Gemma 4 is Apache-2.0** [3P].
- **Gemma 3's terms** define "Model Derivatives" to include models trained "by... methods based on the generation of synthetic data Outputs by Gemma," and attach distribution obligations [V] ([Gemma terms](https://ai.google.dev/gemma/terms?hl=es)). **Avoid Gemma 3 as a teacher. Gemma 4 / Apache-2.0 is fine.**

**Policy for us (not legal advice; have counsel confirm):**
1. Anything that becomes a **training target** comes from:
   - programmatic ground truth (catalogs, codes);
   - our own users' consented data;
   - human labels; or
   - **Apache-2.0 open teachers** (Qwen3-VL-235B, InternVL3.5-241B, Gemma 4 31B).
2. Frontier APIs are for **production inference, evaluation and judging, and as a baseline**.
3. Ask Anthropic or OpenAI for written permission if we want their labels.
4. Separately, the rights to listing data and photos (marketplace ToS, copyright in photos) need legal review. See `research2/index.md` and `research2/data.md` [V-prev].

---

## 5. Evaluation first

### 5.1 How big the eval sets must be [D] (scipy calculations)

**95% CI half-width for accuracy:**

| n | acc 0.80 | acc 0.90 | acc 0.95 |
|---|---|---|---|
| 300 | ±4.5 pp | ±3.4 pp | ±2.5 pp |
| 500 | ±3.5 pp | ±2.6 pp | ±1.9 pp |
| 1,000 | ±2.5 pp | ±1.9 pp | ±1.4 pp |
| 2,000 | ±1.8 pp | ±1.3 pp | ±1.0 pp |

**Comparing two models on the same items (paired, McNemar), α = 0.05, power 0.8.** Items needed:

| True difference | 6% discordant | 10% discordant | 15% discordant |
|---|---|---|---|
| 2 pp | 1,175 | 1,960 | 2,941 |
| 3 pp | 521 | 870 | 1,306 |
| 5 pp | 186 | 312 | 469 |

An unpaired comparison at p = 0.85 needs **2,036 per arm** for 3 pp. So **always compare paired**, as Anthropic recommends [V] ([statistical evals](https://anthropic.com/research/statistical-approach-to-model-evals); [2411.00640](https://arxiv.org/pdf/2411.00640)). Also cluster standard errors by item when an item has several photos or questions. Clustered SEs can be over 3× naive SEs.

**Certifying the confident-error rate** (Clopper-Pearson 95% upper bound; "n" = items the model *answered*):

| Answered n | 0 errors | 1 error | 2 errors | 5 errors |
|---|---|---|---|---|
| 300 | ≤0.99% | ≤1.57% | ≤2.08% | ≤3.47% |
| 500 | ≤0.60% | ≤0.95% | ≤1.25% | ≤2.09% |
| 1,000 | ≤0.30% | ≤0.47% | ≤0.63% | ≤1.05% |
| 2,000 | ≤0.15% | ≤0.24% | ≤0.31% | ≤0.52% |

To certify **≤1%** when the true rate is 0.5% takes **about 780 answered items**. To certify ≤0.5% when the true rate is 0.25% takes about 1,550. At 70% coverage, that is about 1,100 and 2,200 *total* items per certified category group.

**Implication:** an "expert gold" set sized at a round 3K is fine for headline accuracy. But the *real* requirement is **about 1–2K real-photo items per category group we want to certify**, split into a calibration half and a test half. Start with 3–4 groups (sneakers, branded tops and bottoms, bags, outerwear). Add more only when the product needs them.

### 5.2 Building eval sets cheaply and well
- **Real phone photos only.** Use public listings, which already contain multiple user photos including tags. Ground truth comes from **catalog match plus code match, then human adjudication**. No item purchase is needed. Freeze and version the set. Keep an **unseen** test split nobody looks at during development (Tülu 3 practice).
- **Use PPI (prediction-powered inference)** to estimate label precision of auto-labels, and production error rates, from a small human audit plus a large model-labeled pool. Intervals stay valid whatever the model's quality. Typical savings are **1.2–2.5× fewer human labels** [V] ([2301.09633](https://arxiv.org/pdf/2301.09633)).
- **Active learning** for what humans see: send humans disagreements, low-margin retrievals, ask/abstain cases and new brands.
  - Uncertainty sampling is about as good as BADGE and 2–4× more label-efficient than random [V-prev].
  - A 2025 practitioner survey says AL still pays off on complex tasks: projects were "successful in 91%... effective in 67%," and LLM pre-annotation is the main trend [V] ([2503.09701](https://arxiv.org/html/2503.09701v2)).
  - Savings are not guaranteed, so measure them.

### 5.3 Metrics that matter
- **Coverage at risk** (C@R): the fraction answered at ≤R confident-error rate. Report C@1% and C@0.5% per category.
- **Selective risk** at the deployed threshold, with its CP upper bound.
- ECE and AUROC of confidence (RLCR, Rewarding Doubt).
- Hierarchical accuracy: brand, line, model, colorway, era.
- **Ask quality:** the fraction of asks whose requested photo actually resolves the item, and the average number of asks.
- Tag reader: field exact match per field.
- Flaws: Hungarian-matched F1@IoU 0.5.
- Condition: quadratic-weighted κ vs expert.

---

## 6. Compute and cost

### 6.1 Reported numbers [V unless noted]

| Run | Hardware and time | GPU-hours |
|---|---|---|
| Tülu 3 8B SFT (939K text examples, 2 epochs, 4K context) | 32 H100 × ~6 h | ~190 H100-h |
| Tülu 3 8B DPO (271K pairs) | 8 H100 × ~10 h | ~80 H100-h |
| LLaVA-1.5-13B, full (558K + 665K) | 8 A100: ~6 h + ~20 h | ~210 A100-h |
| s1-32B SFT (1K long examples) | 16 H100 × 26 min | ~7 H100-h |
| R1-V 2B counting GRPO [3P] | 8 A100 × 30 min, "$2.62" | ~4 A100-h |
| No-Thinking-RFT, ImageNet few-shot, 2B | 94 min (hardware not stated); Thinking-RFT 1,587 min | — |
| Fine-R1 3B/7B | 4 × A6000 (hours not stated) | — |
| EasyR1 GRPO memory [V] ([repo](https://github.com/ssmisya/EasyR1)) | 7B full: 8 × 40GB (AMP) or 4 × 40GB (BF16); 3B: 1–4 × 40GB | — |
| Seed1.5-VL RL (frontier scale) | — | 60K GPU-h (RM 24K) |

### 6.2 Estimates for our sizes [D]
**Assumptions:**
- About 5 photos per item at ~1K visual tokens each. Qwen2.5-VL merges 2×2 patches of 14 px, so about one token per 28×28 px; ~1 MP gives ~1K tokens [D/U on the exact budget]. Total ~5K tokens per item.
- Training FLOPs ≈ 6 × params × tokens.
- H100 at about 35% MFU ≈ 350 TFLOP/s.

**SFT, 8B, 100K items per epoch:**
- 6 × 8e9 × 5e8 tokens ≈ 2.4e19 FLOPs, which is **~19 H100-h**.
- 4B: ~10 h. 1M items: ~190 h.
- LoRA uses about 2/3 of the FLOPs.
- At $2.65–4.29/H100-h (Oct 2026 on-demand range [V] [Spheron](https://www.spheron.network/blog/lambda-cloud-h100-pricing-2026/)), **100K items × 3 epochs on 8B ≈ $150–250**.

**GRPO, 8B, perception (no-think, ≤200 output tokens):**
- Per prompt: G = 8 rollouts × ~5K-token context. Prefix caching helps generation, but the policy forward/backward over 40K tokens is about 2e15 FLOPs, plus old and reference log-probs.
- That is **~6–10 H100-s per prompt-step**.
- 10K prompts × 2 epochs ≈ **35–55 H100-h**. Double it for overhead, giving **~$200–500 per run**. Multi-turn "ask a photo" episodes cost about 1.5–2× more.

**Teacher labeling with open Qwen3-VL-235B-A22B (22B active)** on 8×H100: an order of **thousands of items per node-hour**. 1M items is therefore roughly 100–300 node-hours, or **$3–10K** [U: measure throughput first].

**Whole first quarter** (all ablations, about 10–20 SFT runs and 10–20 RL runs, plus teacher labeling): **1,500–4,000 H100-h ≈ $5–16K**, plus $3–10K of teacher inference. The founder's earlier $150–350K went almost entirely to human labeling. The GPU line is not the constraint.

### 6.3 Serving
- **Measured:** Qwen2.5-VL-7B on **L40S**, 32 concurrent requests, one 512 px image, 500 input / 150 output tokens: **~320–350 requests/min**; TTFT ~0.34–0.36 s; ~0.032 s/token [V] ([Clarifai](https://www.clarifai.com/blog/benchmarking-best-open-source-vision-language-models)). Gemma-3-4B was similar (~250 rpm).
- **Our real requests** (5 photos, ~5K prefill tokens) are prefill-bound. I estimate **~1–3 items/s per L40S or H100-class GPU** [D/U]. At $1–4/GPU-h, that is **~$0.0001–0.001 per item**, before caching and batching. This is far below frontier-API per-item cost, which is where owning the model pays off.
- **Escalate the ~5–20% of low-confidence items** to the frontier API (production inference is permitted).

---

## 7. "Independently useful" model targets

| Candidate | Market need (evidence) | Feasibility from the literature | Verdict |
|---|---|---|---|
| **A. Calibrated product-ID verifier** (photos plus retrieved candidates → SKU / none / ask; plus a confidence that is honest) | eBay's photo-to-listing tool misidentified a mousepad twice and the wrong ID "flowed into the title, item specifics, and description" [V-prev]. **No published system reports calibrated, near-zero confident-error product ID** [V-prev]. Everything downstream (pricing comps, search, cross-listing, authenticity routing) keys off ID | High. Closed-set selection with exact-match rewards (Visual-RFT, Fine-R1). Hard negatives from catalogs. Calibration via RLCR. Ask-action via ProactiveBench. Labels come from style codes and catalog triangulation | **Train first.** It is the moat and is sellable as an API to marketplaces, consignment and recommerce ops. Licensing: only with clean (non-API-distilled) targets |
| **B. Tag and label reader** (tag/care/size labels → brand, RN, size + system, fiber %, country, style code, GTIN, care) | Poshmark Smart List "missed the size even from a clear tag photo" and confused men's and women's [V-prev]. Every reseller, thrift-sorting operation and recommerce warehouse reads tags | Very high. OCR suits SFT (Perception-R1). Verifiers exist (checksum, RN lookup, catalog). **Synthetic rendering** provides unlimited data. A 2–4B model is enough | **Train first, in parallel.** Fast to "great," cheap to serve, feeds A with hard evidence |
| C. Product-matching / dedup embedding (listing ↔ listing ↔ catalog) | Aggregated secondhand search across 100M+ listings needs it (Phia-style; see `research2/index.md`) | High. WDC-style identifier supervision (F1 ~0.9), cross-listing positives, FashionSigLIP-style multi-field contrastive | **Train third.** This is contrastive embedding work, not VLM post-training. Needed for A's retrieval and for search |
| D. Condition grader plus flaw localizer | Real need (returns and "not as described") but **subjective**. Needs a rubric and expert calibration; the inter-annotator target is α ≥ 0.70 [V-prev] | Localization fits RL (IoU and F1 rewards, Hungarian matching). Weak labels come from seller-described flaws plus synthetic flaws. The grade itself needs human-calibrated data | Later (month 3+). Start with flaw *detection* (verifiable), then grade |
| E. Listing → attribute normalizer (text) | Useful, but frontier and open LLMs already do it well; eBay's 4M-example adaptation shows gains [V] | Easy | No moat by itself. Fold into A and B |
| F. Authenticity risk | High value, but **needs expert labels**. Platforms route to authenticators | Low for us now | Risk score plus routing to partners (as earlier) |

---

## 8. Recommended post-training strategy

### 8.1 Principles
1. **Eval set and verifiers before training data.**
2. **Separate knowledge from policy:**
   - Knowledge (catalog of SKUs, colorways, eras) lives in **retrieval indexes plus SFT on in-domain data**.
   - Decision policy (select, abstain, ask, calibrate) is learned by **RL with verifiable rewards**.
3. **No CoT for perception fields.** Use short structured outputs. Allow optional short reasoning only for era or attribution.
4. **Ground truth comes from programs and catalogs. Humans adjudicate and audit.**
5. **Training targets come only from licensed sources** (§4(vi)).

### 8.2 Data engine: getting labels without buying items
**Sources:**
- public resale listings (multi-photo, usually including tag shots);
- sold, not-returned listings;
- retail and brand catalogs (affiliate feeds; official images, style codes, colorway names, release dates);
- our users' uploads with consent (the flywheel);
- cross-listed duplicates;
- synthetic tags and flaws.

**"Triangulated label" rule.** A listing gets an auto-label for SKU S only if **at least two independent signals agree**, for example:
- (a) a style code, GTIN or RN parsed from listing text or OCR'd from a tag photo resolves to S in the catalog;
- (b) the photo embedding's top-1 catalog match is S with margin ≥ m;
- (c) the open teacher VLM (Qwen3-VL-235B), given photos only (no title), picks S from the candidates.

Then:
- Estimate the precision of triangulated labels per category with a **300–500-item human audit** plus PPI. Target ≥98% before using a category for SFT.
- Keep disagreements as **hard cases** for human adjudication (active learning) and as RL prompts.
- **Strip titles and descriptions from model inputs** whenever they were the label source (the Seed "text-answerable" lesson).
- Hard negatives come free from the catalog: same brand and line, different colorway, year or size run.

### 8.3 Stages, data per stage and rewards

**Base:** **Qwen3-VL-8B-Instruct** (Apache-2.0) for A. **Qwen3-VL-4B / 2B** (or Gemma 4 E4B) for B. Swap in Qwen3.5 if it evaluates better [V-prev for licenses].

| Stage | Purpose | Data (how obtained) | Count, and the literature behind it | Method |
|---|---|---|---|---|
| **S0. Eval and verifier harness** (weeks 0–3) | Measure before training | Gold ID eval: real listings, **catalog- and code-verified, then human adjudicated**. Tag eval: real tag crops with codes. Flaw eval: listings that mention flaws, with boxes | **ID: ~1–2K items per certified group**, starting with 3–4 groups (≈4–6K total; §5.1 power table). **Tags: 1–2K crops** (field-level CI ±1–2 pp). **Flaws: ~500 items** (localization F1 only). Human time: experts **adjudicate**, they do not label from scratch | Baselines: current frontier pipeline, zero-shot open models, retrieval-only |
| **S1. In-domain SFT ("mid-training")** (weeks 3–6) | Teach vocabulary, schema, brand and code knowledge, multi-photo reading | Triangulated auto-labels; tag OCR from synthetic plus real (codes as ground truth); open-teacher descriptions **filtered by rejection against catalog truth** | **50K–300K items**: eBay's 100K items gave 4B > 27B zero-shot; eBay's broad adaptation used 4M. Diminishing returns past distribution match [V-prev]. Per-source and per-brand caps of ~5–10% (Cambrian-style) | LoRA (all layers) or full fine-tune; 1–3 epochs. Keep 10–20% general VLM data to limit forgetting (RL's Razor) |
| **S2. Curated behavior SFT** (week 6) | Abstain, "none of these," ask-for-photo format, calibrated-confidence format, evidence fields | Hand-written and edited examples (founders plus 1–2 experts), seeded from S0 disagreements | **1–3K examples** (LIMA 1K, LIMO 817, s1 1K, MM-LIMA 200, Fine-R1 404) | Short SFT (Seed: "stronger cold start leads to a stronger final model") |
| **S3. RL with verifiable rewards and calibration** (weeks 7–10) | Selection among look-alikes, abstain and ask policy, honest confidence | Prompts = triangulated items plus hard negatives. **Filter to rollout pass rate 0.2–0.8.** Multi-turn env: hide some photos (tag, sole, label) and return them only when the model asks for that view | **10–30K prompts** (Qwen3-VL 30K; InternVL3.5 70K; Perception-R1 5–10K per task; RLCR 20K + 15K). G = 8 rollouts | GRPO or DAPO; no-think; LoRA works even at low rank for RL |
| **S4. Calibration and risk control** (weeks 10–11) | Certify "confident ⇒ correct" | Held-out calibration split of S0, per category group | ≥ ~800 answered items per group for a ≤1% guarantee (§5.1) | Split-conformal / Learn-then-Test thresholds on the combined score (policy confidence, retrieval margin, code match, self-consistency). Optional small learned selector (Reliable VQA) |
| **S5. Shadow, escalation, flywheel** (weeks 11–14+) | Production | Logged predictions vs seller final values, edits, sales without returns, disputes | Continuous; 1–2% audited with PPI | Rejection-sampling fine-tune rounds (Seed did 4) with new verified data every 2–4 weeks |

**Reward designs (S3)**

- **Product ID (model A).**
  - **Output schema:** {choice ∈ candidates ∪ {NONE, ABSTAIN, ASK(view)}, per-field confidences q_f for brand, line/model, colorway/variant, era}.
  - **Per field f:** r_f = 1[correct_f] − (q_f − 1[correct_f])² − λ·1[wrong_f ∧ q_f > τ]. This is the RLCR Brier term plus an extra penalty for confident errors. Start with λ ≈ 1 and τ = 0.8, then tune on dev (TruthRL showed accuracy can drop if the penalty is too harsh).
  - **Weights:** brand 0.15, line/model 0.35, colorway/variant 0.35, era 0.15. Total r = Σ w_f·r_f.
  - **NONE:** +1 if the true SKU is not among the candidates, else −1. This teaches open-set rejection. Make sure about 10–20% of prompts have no correct candidate.
  - **ABSTAIN:** 0.
  - **ASK(view):** the environment returns that view if the listing has it. The final reward is the continuation's reward × (1 − c_ask), with c_ask ≈ 0.25. If the view doesn't exist or wasn't needed, −0.1. Allow at most 2 asks. Follows ProactiveBench (r_p < 1 avoids over-asking).
  - **Anti-hacking:**
    - no title text in inputs;
    - candidates shuffled;
    - a length cap;
    - monitor the ask and abstain rates per category;
    - every verifier unit-tested against adversarial outputs (GLM lesson).
- **Tag reader (model B).** Mostly SFT (OCR is low-perplexity, so SFT is enough per Perception-R1). Then a light RL or DPO pass:
  - per-field exact match after normalization;
  - 1 − normalized edit distance for free text;
  - **reward = match to ground truth.** Checksum or RN validity is only a filter, never the reward;
  - an "illegible" token with the same calibrated-confidence scheme.
- **Flaws (later).** Hungarian-matched IoU plus count F1, with a redundancy penalty (Perception-R1, VLM-R1), plus confidence per flaw.

### 8.4 Timeline (1–2 ML engineers plus part-time domain experts)

| Weeks | Milestone |
|---|---|
| 0–3 | Legal pass on data sources and ToS. Eval v0 (ID, 3–4 groups; tags). Verifier library (codes, RN, GTIN, size systems). Baselines (frontier and zero-shot open models) |
| 2–5 | Data engine: catalog ingest, listing ingest, triangulation, synthetic tag renderer. PPI audit of auto-label precision |
| 4–6 | **Model B v1** (SFT, 2–4B). **Model A SFT** (8B) |
| 6–10 | Behavior SFT, then GRPO with the calibration, abstain and ask rewards. Ablations: think vs no-think, LoRA vs full, reward weights |
| 10–12 | Conformal thresholds per group; shadow mode vs the frontier pipeline; escalation policy |
| 12–14 | Go/no-go per category on the targets below. Start the flywheel retraining cadence. Plan flaws and condition (D) and the embedding model (C) |

### 8.5 Budget (first ~14 weeks)
- **GPU:** 1.5–4K H100-h ≈ **$5–16K**.
- **Open-teacher labeling:** **$3–10K** [U].
- **Human:** about 10–20 expert-days for adjudication plus 2–4K adjudicated eval items at about 1.5–3 min each to *verify* (≈100–200 hours) ≈ **$10–25K** [D, rates from `research2/data.md`].
- **Total ≈ $20–50K**, plus engineering salaries. Nothing is purchased.

### 8.6 What "great" looks like

**Model A, calibrated product-ID verifier** (fashion groups with style codes first: sneakers, branded apparel, bags):
- **Confident-error rate ≤0.5% observed, with a 95% upper bound ≤1%**, on the frozen real-photo test split per group.
- **Coverage ≥70% at that risk**, rising toward ≥85% after one flywheel cycle.
- ECE ≤0.03 on answered items.
- **At least half of asks resolve the item.** Average asks per item ≤0.4.
- **Beats the current frontier pipeline on C@1% by ≥10 pp** (paired test, about 900 items for 3 pp resolution).
- p95 latency ≤1.5 s on one GPU; cost ≤$0.001 per item.

**Model B, tag reader:**
- Field exact match on legible tags:
  - brand / RN ≥99%;
  - size + system ≥98%;
  - fiber composition ≥97%;
  - style code / GTIN ≥99%.
- **Precision ≥99.5% when confident.**
- Illegible detection AUROC ≥0.95.
- ≤300 ms per tag crop.
- Zero GTIN outputs that fail the checksum.

---

## 9. What the earlier plan got wrong

The earlier plan was "3K expert gold + 20–50K human-verified labels + 2–5K hand-curated SFT + human-verified negatives, $150–350K" (`research2/data.md` §5).

1. **It treated human labels as the training signal.** At labs, the signal is **machine-generated data filtered by verification** (rejection sampling, rules, reward models), plus **RL on prompts with checkable answers**. Humans write a small slice (Seed: ~13K of ~50K SFT; LIMA: 1K) and build evals. 20–50K human-verified training labels is the wrong unit of work.
2. **It missed that our domain already has verifiers.** Style codes, GTIN checksums, RN lookup, catalog matches and cross-listing duplicates are exactly the "rule-based rewards" that drove Qwen3-VL, Seed1.5-VL, MiMo-VL and GLM. They also make better label filters than human spot-checks.
3. **It had no RL stage and no calibration objective,** although "near-zero confident errors" and "ask for a specific photo" are the core requirements. The literature shows these are trainable:
   - RLCR: ECE 0.37 to 0.03;
   - ternary rewards;
   - ProactiveBench: ask rate learned, 11% to 37% accuracy.

   Plain RLVR or SFT makes calibration worse.
4. **It conflated knowledge with labels.** Knowing millions of SKUs or colorways cannot come from 50K labels. It comes from **retrieval over catalogs and listings**, with the VLM choosing among candidates. RL carries about 1 bit per episode and doesn't add sub-category knowledge (Fine-R1, Yue et al.).
5. **Eval sizes were round numbers, not power or risk calculations.** The real requirement is about 1–2K real-photo items **per certified category group** to certify ≤1% confident error, and about 900 paired items to detect 3 pp. Some groups need more than 3K, others need none yet.
6. **It assumed "VLM pre-label + human verify" with frontier models.** Anthropic's help page bars "Using Outputs as training targets for models" without written permission. OpenAI allows only classifiers that are "not distributed or made commercially available." Google bars models that "compete with the Services." That also blocks selling a model trained on those labels. Use Apache-2.0 teachers.
7. **It budgeted before measuring.** There was no pilot of auto-label precision (PPI makes a 300–500-item audit enough per category) and no stage gates tied to C@R. Its "100K labels → 4B beats 27B" anchor came from eBay labels that were **model-generated (GPT-4.1) and refined automatically**, not human-verified.
8. **What it got right, and we keep:**
   - eval-first;
   - a flywheel from seller edits and sales;
   - provenance and consent;
   - authenticity as routing, not a claim;
   - experts adjudicating instead of labeling everything.

---

## 10. Open questions and unverified items
- InternVL3.5 Cascade RL ablation numbers and GPU-hours appear only in images [U]. InternVL3 (MPO details) not read.
- Llama 3 vision post-training (Section 7) not read [U]. Llama 4 details are from a third-party synthesis [3P]. Gemma 4 post-training is not disclosed.
- R1-V cost and time come from press coverage [3P].
- Visual token budgets for Qwen3-VL at our resolutions, and real serving throughput for 5-photo requests, need measuring [U].
- Teacher-labeling throughput for Qwen3-VL-235B needs measuring [U].
- Vertex AI (vs Gemini API) generative AI terms not checked [U]. The Anthropic help page was read through a summarizer with quote limits, so pull the exact page before relying on it.
- Per-brand style-code formats, and furniture maker-mark verifiers, still need compiling [U].
- The legality of training on scraped listing photos and text is not resolved here; see `research2/index.md`.

## Sources (opened this session)
- Qwen2.5-VL https://arxiv.org/pdf/2502.13923
- Qwen3-VL https://arxiv.org/pdf/2511.21631
- InternVL3.5 https://arxiv.org/pdf/2508.18265 and https://huggingface.co/OpenGVLab/InternVL3_5-8B
- Molmo / PixMo https://arxiv.org/html/2409.17146v1 and https://arxiv.org/pdf/2409.17146
- LLaVA-OneVision https://arxiv.org/html/2408.03326v3
- Cambrian-1 https://proceedings.neurips.cc/paper_files/paper/2024/file/9ee3a664ccfeabc0da16ac6f1f1cfe59-Paper-Conference.pdf
- Gemma 3 (report copy) https://52nlp.cn/wp-content/uploads/2025/03/Gemma3技术报告英中对照版.pdf
- Gemma 4 https://www.gigazine.net/gsc_news/en/20260403-google-released-gemma-4
- Gemma terms https://ai.google.dev/gemma/terms?hl=es
- Llama 3 https://www.rivista.ai/wp-content/uploads/2024/11/2407.21783v2.pdf
- Llama 4 synthesis https://arxiv.org/pdf/2601.11659
- Seed1.5-VL https://arxiv.org/pdf/2505.07062
- MiMo-VL https://arxiv.org/pdf/2506.03569
- Kimi-VL https://arxiv.org/pdf/2504.07491v1
- GLM-4.5V https://arxiv.org/html/2507.01006v6
- Tülu 3 https://arxiv.org/pdf/2411.15124 and https://arxiv.org/html/2411.15124v1
- DeepSeek-R1 https://arxiv.org/html/2501.12948v1
- LIMA https://ar5iv.labs.arxiv.org/html/2305.11206
- s1 https://arxiv.org/html/2501.19393v2
- LIMO https://arxiv.org/html/2502.03387v1
- Visual-RFT https://arxiv.org/html/2503.01785v1
- Think or Not Think https://arxiv.org/html/2503.16188v6
- Fine-R1 https://arxiv.org/html/2602.07605
- Perception-R1 https://arxiv.org/html/2504.07954v1
- VLM-R1 https://arxiv.org/pdf/2504.07615
- R1-V (press) https://www.marktechpost.com/2025/02/04/deep-agent-released-r1-v-reinforcing-super-generalization-in-vision-language-models-with-cost-effective-reinforcement-learning-to-outperform-larger-models/
- SFT Memorizes, RL Generalizes https://arxiv.org/html/2501.17161v2
- Vision-R1 https://arxiv.org/html/2503.06749v4
- ProactiveBench https://arxiv.org/pdf/2603.19466
- Limits of RLVR https://arxiv.org/abs/2504.13837v4
- RL's Razor https://arxiv.org/html/2509.04259v1
- LoRA Without Regret https://thinkingmachines.ai/blog/lora/
- R-Tuning https://arxiv.org/html/2311.09677v2
- RLCR https://arxiv.org/pdf/2507.16806
- Rewarding Doubt https://arxiv.org/html/2503.02623v4
- TruthRL https://arxiv.org/html/2509.25760v1
- OpenAI on hallucination https://openai.com/index/why-language-models-hallucinate/?so=1
- Reliable VQA https://arxiv.org/abs/2204.13631
- CAP https://arxiv.org/html/2502.06884v1
- Anthropic Commercial Terms https://www.anthropic.com/legal/commercial-terms
- Anthropic help page https://support.claude.com/en/articles/12326764-can-i-use-my-outputs-to-train-an-ai-model
- Anthropic AUP archive (2023) https://www.anthropic.com/legal/archive/4903a61b-037c-4293-9996-88eb1908f0b2
- OpenAI Business Terms https://openai.com/policies/business-terms
- OpenAI Services Agreement https://cdn.openai.com/osa/openai-services-agreement.pdf
- Gemini API terms https://ai.google.dev/gemini-api/terms
- Distillation law analysis https://variant.fund/articles/license-distill-law-distillation-anthropic/
- Qwen3-VL license https://llm-stats.com/models/qwen3-vl-235b-a22b-instruct
- eBay VLM adaptation https://arxiv.org/html/2602.11733 and https://arxiv.org/pdf/2602.11733
- Confident learning https://arxiv.org/pdf/1911.00068
- Marqo-FashionSigLIP https://marqo.ai/blog/search-model-for-fashion
- WDC product matching https://www.uni-mannheim.de/media/Einrichtungen/dws/Files_Research/Web-based_Systems/pub/ECNLP_19_PrimpeliPeetersBizer.pdf
- Weak-to-strong generalization https://www.arxiv.org/pdf/2312.09390
- WebVision https://ar5iv.arxiv.org/html/1708.02862
- Model collapse https://oatml.cs.ox.ac.uk//publications/202407_Shumailov_ModelCollapse.html
- DRAEM https://arxiv.org/abs/2108.07610v2
- FTC RN lookup https://www.ftc.gov/node/43948
- Anthropic on statistical evals https://anthropic.com/research/statistical-approach-to-model-evals
- Prediction-powered inference https://arxiv.org/pdf/2301.09633
- Active learning survey https://arxiv.org/html/2503.09701v2
- LLaVA-1.5 https://arxiv.org/html/2310.03744v2
- EasyR1 https://github.com/ssmisya/EasyR1
- Clarifai VLM serving benchmark https://www.clarifai.com/blog/benchmarking-best-open-source-vision-language-models
- H100 pricing https://www.spheron.network/blog/lambda-cloud-h100-pricing-2026/
