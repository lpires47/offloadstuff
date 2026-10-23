# Data program research: datasets, legal, labeling ops, flywheel (as of 2026-10-23)

Scope: exact product ID from seller photos (brand, model, colorway, size from tags, condition, flaws, authenticity risk) and design-literate search (text or photo to secondhand listings). Fashion first, then furniture, home and design objects.

How to read this:
- **[V]** means I checked it on the cited page.
- **[U]** means unverified: from memory, a secondary source, or a page that did not state it. Confirm before relying on it.
- Some pages could not be opened (permission timeouts on `github.com/amazon-science/esci-data` and `github.com/marqo-ai/GCL`; ecommercebytes.com has shut down). The web-search budget ran out near the end, so a few items stay [U]. They are flagged where they appear.
- Nothing here is legal advice.

---

## 1. Public datasets

**Bottom line.** Almost every well-known fashion dataset is non-commercial or has no clear license, and the images are usually scraped from third parties. Even a permissive annotation license (for example CC BY on Fashionpedia) does not give you rights in the underlying photos. For a commercial model, only a few sets are clean:

- **Amazon Berkeley Objects (ABO)**, CC BY 4.0
- **Amazon ESCI**, Apache-2.0
- **Fashionpedia** annotations, CC BY 4.0 (the image rights are a separate question)
- **RISE second-hand clothing set**, CC BY 4.0

Treat everything else as **evaluation or research only**, and keep it out of the production training mix unless counsel signs off.

| Name | Size | Labels | License / terms | Useful for |
|---|---|---|---|---|
| **DeepFashion** (CUHK MMLab) | 800K+ images; 300K+ cross-pose/domain pairs [V] | 50 categories, 1,000 attributes, bboxes, landmarks; MultiModal (2022) adds parsing, keypoints, text [V] | **Non-commercial research only.** Signed agreement, no redistribution, no commercial use of images or derived data [V] ([agreement](https://mmlab.ie.cuhk.edu.hk/projects/DeepFashion.html)) | Benchmarking attributes and consumer-to-shop retrieval. Not for production training |
| **DeepFashion2** | 491K images (paper, [U]); 801K items, 873K commercial-consumer pairs [V] | Style, scale, viewpoint, occlusion, bbox, dense landmarks, masks [V] | Listed as "Other" on [hyper.ai](https://hyper.ai/en/datasets/18036). The repo says academic research only and requires a signed form [U] | Consumer-to-shop eval. A 13.5K-triplet fine-tune on it beat FashionSigLIP (see §3) |
| **Fashionpedia** (Cornell/Google/Sama; also iMaterialist-Fashion 2020) | 48,825 images (45,623 train / 1,158 val / 2,044 test); 342K boxes [V] | 27 main categories + 19 parts, **294 fine-grained attributes** in 9 super-categories, masks, attributes per mask [V] ([arXiv](https://arxiv.org/abs/2004.12276)) | **CC BY 4.0** per the [HF card](https://huggingface.co/datasets/detection-datasets/fashionpedia/commit/2508afee1baf83aaaf179bec3179489b8b4193ab) [V]. Images come from Flickr and other free-license sources and may carry their own terms [U] | **Best public attribute ontology to start our taxonomy from.** Possibly usable commercially, after checking image provenance |
| **iMaterialist Fashion 2019 (FGVC6)** | ~50K images; 46 objects, 92 attributes [V] ([Sama/Cornell PR](https://www.edge-ai-vision.com/2019/05/samasource-and-cornell-tech-announce-imaterialist-fashion-a-robust-free-open-source-fashion-data-set-for-research-and-development/)) | Segmentation + attributes | Described as "free open source for research and development" [V]. No explicit license; Kaggle competition rules apply [U] | Superseded by Fashionpedia |
| **iMaterialist Fashion Attribute 2018** | 1M+ images, 228 attributes in 8 groups [V] ([PwC](https://paperswithcode.com/dataset/imaterialist)) | Multi-label attributes | Kaggle competition rules; images given as URLs [U] | Attribute pretraining or research only |
| **iMaterialist Furniture 2018** | ~194K train images, 128 furniture/home classes [U] | Category only | Kaggle rules, image URLs [U] | Coarse furniture classes only, no design attributes |
| **ModaNet** (eBay) | 55K images [U]; COCO-style JSON [V] | 13 categories, polygons [V] | **Annotations CC BY-NC 4.0** [V]. Images from PaperDoll (Chictopia), license not stated [V] ([GitHub](https://www.github.com/eBay/modanet)) | Street-photo garment segmentation research |
| **Fashion-Gen** (SSENSE) | 293,008 images (text) vs 325,536 (table); 78,850 items; 48 categories, 121 subcategories; 1360×1360 studio shots, 1–6 angles [V] | Paragraph-length descriptions written by designers, designer/brand, season, matching items [V] ([paper](https://arxiv.org/pdf/1806.08317)) | Paper states no license; research-only access agreement [U] | Shows what "design-literate" captions look like. Research/eval only |
| **FashionIQ** | ~77K images, ~30K relative-caption triplets [U] | Relative natural-language feedback ("make it longer, in red") | Repo under **CDLA** (version not confirmed) [V] ([GitHub](https://github.com/XiaoxiaoGuo/fashion-iq)). Images are Amazon URLs with no image rights granted [U] | Composed / conversational retrieval eval ("like this but…") |
| **Polyvore Outfits** (Vasileva et al.) | 251,008 items, 68,306 outfits (Disjoint: 152,785 / 35,140) [V] ([docs](https://outfit-datasets.readthedocs.io/en/latest/polyvore_outfits.html)) | 11 categories, outfit compatibility | No license stated [V]. Scraped from the defunct Polyvore site | Compatibility / "goes with" research only |
| **Maryland Polyvore** | 111,589 items, 21,889 outfits, 380 categories [V] | Outfits | No license stated [V] | Same as above |
| **Marqo/polyvore** (HF re-pack) | 94.1K rows, 377 categories [V] | Image, category, text | Tagged **Apache-2.0** [V] ([HF](https://huggingface.co/datasets/Marqo/polyvore)), but upstream image rights are unclear | Eval only. A re-pack's license tag does not fix upstream rights |
| **Marqo eval suites** (marqo-general-ecommerce-eval, google-shopping-general-eval, amazon-products-eval) | ~59 GB, 1M–10M rows [V] | Query/title/image | License not shown on the page [V]. GS-10M has been described as Apache-2.0 [U] | Off-the-shelf e-commerce retrieval benchmarks. Marqo-FashionSigLIP (Apache-2.0 [V]) was trained on 1M+ products and evaluated on 7 fashion sets ([blog](https://marqo.ai/blog/search-model-for-fashion)) |
| **H&M Personalized Fashion Recs** (Kaggle 2022) | ~105K articles with studio images [V via [HopitAI](https://hopitai.substack.com/p/beating-fashionsiglip)]; 1.37M customers, ~31M transactions [U] | Article metadata (type, color, graphic, section), purchases | Kaggle competition rules. Commonly read as competition / non-commercial use [U] ([overview](https://shaped.ai/blog/h-m-dataset-powering-personalized-fashion-recommendations-at-scale)) | Recommendation and retrieval eval. Fine-tuning on its studio images **hurt** consumer-photo retrieval by 5 pts R@1 (domain mismatch) [V] |
| **Amazon Berkeley Objects (ABO)** | 147,702 listings, 398,212 catalog images, 586,584 turntable images (8,209 sequences), 7,953 3D models [V] | Multilingual metadata (brand, color, material, product type, dimensions), 3D | **CC BY 4.0** (relaxed from CC BY-NC in 2023) [V] ([AWS registry](https://registry.opendata.aws/amazon-berkeley-objects/)) | **Commercially usable.** Furniture and home are heavily represented. Good for pretraining, multi-view, and synthetic renders from the 3D models |
| **Amazon ESCI (Shopping Queries)** | 130,652 queries / ~2.62M judgments (large); 48,300 / 1.12M (reduced); EN/ES/JA [V] | Exact / Substitute / Complement / Irrelevant [V] | **Apache-2.0** [V] (via a [mirror of the repo](https://github.com/Pixee-Bot-Python/esci-data); the original repo was blocked) | **Commercially usable** search-relevance training and eval. Use the ESCI scale as the basis for our relevance guidelines. An image add-on (SQID, 2024) exists [U] |
| **Products-10K** (JD.com) | 10K SKUs, ~150K images [U] | Human-labeled SKU IDs in a hierarchy [V] ([V7](https://www.v7labs.com/open-datasets/products-10k)) | Not stated [V]. Research [U] | Instance-level product-ID eval |
| **Stanford Online Products** | 120,053 images, 22,634 classes, 12 super-classes [V] ([TFDS](https://tensorflow.google.cn/datasets/catalog/stanford_online_products)) | Product instance IDs (from eBay listings) | No dataset-specific license [V]. Research [U] | Metric-learning benchmark. Mostly saturated |
| **eProduct** (eBay, 2021) | 2.5M images; 1.28M train + 50K val; 10K queries vs 1.1M index; 1,000 leaf categories [V] ([paper](https://arxiv.org/pdf/2107.05856)) | Hierarchical categories + titles. Human-verified exact matches (~10.2 per query, up to 10 raters) [V] | Not stated [V] | Million-scale visual-search eval. Closest public proxy for marketplace product matching |
| **Shopee Product Matching** (Kaggle 2021) | ~34K train listing images [U] | Same-product groups (image + title) | Kaggle competition rules [U] | Marketplace duplicate / same-item matching research |
| **3D-FUTURE** (Alibaba) | ~10K 3D furniture models, ~20K scene renders [U] | 3D shape, texture, style, material | **Scientific research only. No commercial use of data, derivatives, or results.** Indemnity required [V] ([agreement](https://terms.aliyun.com/legal-agreement/terms/suit_bu1_ali_cloud/suit_bu1_ali_cloud202004171628_60052.html)) | Do not use in a product model |
| **IKEA 3D Assembly** | 5 products (glb/obj + PDFs) [V] | 3D | **CC BY-NC-SA 4.0** [V] ([GitHub](https://github.com/IKEA/IKEA3DAssemblyDataset)) | Not useful at scale |
| **Clothing Dataset for Second-Hand Fashion** (RISE / Wargön / Myrorna; v2 June 2024) | **31,997 items × 3 images** (front, back, brand label), ~27 GB [V] | **Condition 1–5, pilling 1–5, stains/holes/smell (none/minor/major)**, material (NIR), "trend", price, damage comments, usage pathway. A 100-item subset was multi-annotated for agreement [V] | **CC BY 4.0** [V] ([Zenodo](https://zenodo.org/records/12518734)) | **The only open, commercially licensed secondhand condition/flaw dataset found.** Directly relevant to condition grading. Swedish charity-sorting distribution |
| **ILIAS** (CVPR 2025) | 1,232 image queries + 1K text queries, 4.7K positives, ~100M distractors [V] | Instance-level matches | "cc" on HF, version unclear [V] ([HF](https://huggingface.co/datasets/vrg-prague/ilias)) | Hard instance-retrieval eval at scale |
| **nyris Visual Product Search Benchmark** (Mar 2026) | 12 models compared on 4 private sets (incl. Furniture v1: 85K gallery images, 50.6K products) plus SOP, ILIAS, Products-10K [V] | R@1/R@5/mAP | Private data | Finding: general embeddings (SigLIP2, Gemini Embedding 2, Cohere v4) are strong on public sets, but "pretraining alone does not ensure reliable instance-level identification." On furniture, the vendor's model scored 65.8 R@1 vs SigLIP2 57.4 [V] ([arXiv 2603.17186](https://arxiv.org/pdf/2603.17186)). Vendor-authored |
| **ZooClaw-FashionSigLIP2** (Jun 2026) | Proprietary 200K / 400K / 800K pairs; open eval benchmark and weights [V] | Text-to-image fashion retrieval | Licenses not named [V] ([arXiv 2606.27708](https://arxiv.org/pdf/2606.27708)) | Data-scaling evidence (§3) and an extra eval set |

**Gaps no public dataset covers.** We will need our own data for all of these:
- size and care-tag OCR on worn or used garments
- exact model/colorway identification for secondhand items
- flaw localization
- authenticity
- furniture designer, maker, and model attribution (e.g., "Cassina LC4 vs a replica")

---

## 2. Using marketplace data for training (legal landscape). Not legal advice.

### US case law on scraping
- **hiQ v. LinkedIn (final, Dec 2022).** The Ninth Circuit had twice said scraping public pages is likely *not* a CFAA violation. But in Nov 2022 the district court granted LinkedIn summary judgment for **breach of the User Agreement**: hiQ had agreed to it with a corporate account and used contractors to create fake profiles. The case ended in a consent judgment: a permanent injunction, deletion of scraped data, code and models, and **$500K** to LinkedIn [V] ([ZwillGen](https://www.zwillgen.com/alternative-data/hiq-v-linkedin-wrapped-up-web-scraping-lessons-learned/)). **Lesson:** once you hold an account, the ToS binds you. That includes contractors acting for you. Remedies can include **deleting models trained on the data**.
- **Meta v. Bright Data (N.D. Cal., Jan 23 2024, Judge Chen).** Summary judgment for Bright Data. **Logged-off scraping of public data was not "use"** of Facebook or Instagram under Meta's terms, and the survival clause did not reach it [V] ([FBM](https://www.fbm.com/post/102kqw7/)). On Feb 23 2024 Meta dropped its remaining claim and **waived appeal** [V] ([TechCrunch](https://techcrunch.com/2024/02/26/meta-drops-lawsuit-against-web-scraping-firm-bright-data-that-sold-millions-of-instagram-records)). This is a district-court ruling only and is not binding precedent.
- **X Corp v. Bright Data (N.D. Cal., Judge Alsup).** May 9 2024: contract, interference and unjust-enrichment claims were dismissed as **preempted by the Copyright Act**. Users own their posts; X holds only a non-exclusive license and cannot create copyright-like rights through its ToS [V] ([AFS](https://www.afslaw.com/perspectives/ai-law-blog/can-you-prevent-ai-scraping-your-website-data-district-court-says-answer)). **But** on Nov 26 2024 the court let amended claims proceed: **trespass to chattels** (X said it bought 10–20% more server capacity), contract claims about *server access*, and new **DMCA / CFAA** claims. Bright Data counterclaimed on antitrust grounds [V] ([Goldman blog](https://blog.ericgoldman.org/archives/2025/01/catching-up-on-the-heavyweight-scraping-battle-between-x-and-bright-data-guest-blog-post.htm)). Current status [U].
- **The new front is DMCA §1201 anti-circumvention.**
  - *Reddit v. SerpApi, Oxylabs, AWMProxy, Perplexity* (S.D.N.Y. 25-cv-8736, filed Oct 22 2025): Reddit says the defendants circumvented Google's SearchGuard bot controls. Motions to dismiss were pending as of Mar 2026.
  - *Google v. SerpApi* (N.D. Cal., filed Dec 19 2025): MTD hearing set for May 2026 [V] ([PPC Land](https://ppc.land/serpapi-pushes-to-kill-reddits-dmca-suit-over-google-scraping/)). Outcomes [U].
  - **Practical read:** evading CAPTCHAs, bot-detection or rate limits is now the highest-risk scraping behavior.
- **Fair use for AI training (US).** Bartz v. Anthropic (June 2025): training ruled fair use, but pirated libraries were not; later a ~$1.5B settlement. Kadrey v. Meta (June 2025): fair use on that record. Thomson Reuters v. Ross (Feb 2025): not fair use for a competing non-generative tool. **[U] — search budget ran out before I could verify these.** Thomson Reuters v. Ross is the closest analogy for us: a non-generative tool that competes in the source's own market.

### EU and UK
- **DSM Directive Art. 4 TDM exception.** Covers commercial use **unless the rightsholder opts out by "machine-readable means"** for online content. It does not apply if access was unlawful [V].
- **Hamburg Court of Appeal (5 U 104/24, Dec 10 2025).** Dataset creation may fall under the TDM exceptions, and a natural-language opt-out in ToS **may not be machine-readable** [V]. This is likely the appeal in Kneschke v. LAION [U].
- **Munich I court.** Nov 11 2025 (GEMA v. LLM provider) and Jul 31 2026 (GEMA v. music generator): memorized works reproduced in outputs infringe, and the TDM exception covers only copies made *before* training [V] ([Reed Smith](https://www.reedsmith.com/articles/entertainment-media-guide-to-ai-three-years-on/text-data-mining-in-the-eu/)).
- **Pending CJEU case** C-250/25 (Like Company); hearing held Mar 2026 [V].
- **AI Act Art. 53(1)(c)–(d).** Providers of **general-purpose AI** models must have a copyright-compliance policy that respects TDM opt-outs, and must publish a training-content summary [V]. A narrow product-ID / retrieval model we post-train is probably **not** a GPAI model. Fine-tuning a GPAI model may create obligations only if the modification is substantial [U]. The Commission consulted on opt-out protocols in Dec 2025 [V] ([CEPIC](https://www.cepic.org/post/european-commission-launches-consultation-on-ai-act-opt-out-protocols-for-text-and-data-mining)).
- **UK: Getty v. Stability AI (High Court, Nov 4 2025).** Getty dropped its primary training claims (training took place outside the UK [U]). Secondary infringement was rejected; trademark wins were "extremely limited" [V] ([Cleary](https://www.clearygottlieb.com/news-and-insights/publication-listing/uk-high-court-issues-landmark-ruling-in-getty-images-v-stability-ai)). The UK has no commercial TDM exception, and government consultation is ongoing [V].

### Copyright in product photos
- Seller photos are copyrightable by the **seller**, because the originality threshold is low [U, general doctrine]. Platforms take only a license:
  - **Poshmark:** "you continue to own all your Content … nonexclusive, worldwide, royalty free … transferable, sublicensable, perpetual, irrevocable license" [V] ([Poshmark ToS](https://poshmark.com/terms)).
  - **eBay:** irrevocable, royalty-free, sublicensable license; may keep photos in its catalogue and offer them to other sellers [V] ([eBay UA](https://www.ebay.co.uk/help/policies/member-behavior-policies/user-agreement?id=4259)).
- **Two consequences:**
  - (a) Under the X v. Bright Data reasoning, platforms may struggle to stop logged-off copying on copyright-like grounds.
  - (b) The *sellers* still hold the rights. Brand catalog and studio photos (e.g., SSENSE, Farfetch) are professional work and carry the highest risk.
- **Training vs output.** Training a non-generative model on photos is a weaker infringement theory than redistributing the photos. **Never redisplay scraped photos in the product.**
- **Privacy.** Seller photos often contain faces, homes, and names on tags or receipts. GDPR/CCPA apply to EU and CA sellers. Illinois BIPA covers face geometry if we ever process faces [U]. Blur or crop faces at ingestion.

### Platform terms (contract risk if we hold accounts, and we will, since the product cross-lists)
- **eBay User Agreement:** bans "robot, spider, scraper, data mining tools … or other automated means" without express permission. The update effective **Feb 20 2026** adds "buy-for-me agents, LLM-driven bots, or any end-to-end flow that attempts to place orders without human review" [V] ([Value Added Resource](https://www.valueaddedresource.net/ebay-bans-ai-agents-updates-arbitration-user-agreement-feb-2026/); [eMarketer](https://www.emarketer.com/content/ebay-joins-amazon-tightening-control-over-ai-shopping-agents)). eBay's API License Agreement reportedly restricted using API data to train AI from July 2025 [U] (the source site has shut down).
- **Poshmark:** prohibits "copy, scrape, harvest, crawl or use any technology … automated systems to collect any information" [V].
- **Depop, Vinted, Grailed, The RealReal:** similar anti-scraping clauses expected [U; not checked].
- **Key point for an agentic cross-lister.** Our agent operates *inside* seller accounts, so hiQ-style contract liability attaches. We also depend on these platforms to function. Being banned costs us far more than any court ruling would.

### Licensed and owned data options (lowest risk first)
1. **Our own sellers' uploads, with an explicit ML-training license in our ToS and an opt-out.** We receive photos and corrected attributes for every item we list. This is the core asset.
2. **Commercial-license open sets:** ABO (CC BY), ESCI (Apache-2.0), Fashionpedia annotations (CC BY), RISE second-hand set (CC BY).
3. **Affiliate product feeds** (Awin, Rakuten, CJ, Impact): name, description, price, **images**, vertical-specific fields [V] ([Awin](https://help.awin.com/developers/docs/product-feed-publisher-guide-intro)). Feeds are licensed for promoting products; ML-training rights are **not stated** [V]. Ask for a written addendum. They give us canonical new-retail product identity (brand, model, colorway, GTIN) to match resale items against.
4. **Brand catalog partnerships and resale-as-a-service partners.** Trove, Archive, Recurate and brand take-back programs [U] hold model/SKU-level ground truth, archive images, and authenticity knowledge. Offer analytics or routing in exchange.
5. **Data vendors.** Bright Data sells scraped datasets, e.g., SSENSE 261.9K records, ModeSens 15M+ records, $250 per 100K records ($0.0025/record) [V] ([SSENSE](https://brightdata.com/products/datasets/ssense), [ModeSens](https://brightdata.com/products/datasets/modesens)). They say "publicly available … compliant" but give **no license for commercial training**. Buying them does not transfer copyright clearance; the risk stays with us. Fine for price and metadata analytics; risky for image training.
6. **Authentication outcome data** bought from authenticators (LegitApp at $3 per sneaker and $10+ per luxury item, 2+ experts per item, 3M+ checks [V] ([App Store](https://apps.apple.com/app/id1531627344))) or partnerships (Entrupy: 25M-image database, claims 99.1% accuracy [V] ([FashionUnited](https://fashionunited.uk/news/fashion/behind-entrupy-official-ai-authenticator-for-luxury-handbags-on-tiktok-shop/2023102372204))).

**Risk flags:**
- **High:** logged-in scraping; bypassing bot defenses (DMCA §1201); training on brand studio photos; redisplaying third-party photos.
- **Medium:** logged-off, polite crawling of public listings for metadata or pricing only.
- **Low:** our own seller data under a clear ToS; CC BY / Apache sets with attribution.
- Keep a **provenance ledger** (source, license, date, opt-out status) for every training image. Deletion remedies like hiQ's make this a must-have.

---

## 3. Labeling operations

### Taxonomy / ontology design
- **Start from Fashionpedia's ontology** (27 categories, 19 parts, 294 attributes in 9 super-categories) and extend it with resale-specific fields. Then reconcile with marketplace schemas, so we can export to eBay item specifics, Poshmark, Depop and similar.
- **Controlled vocabularies enforced in the tool.** One case study (3M+ fashion images, 7 attribute types) enforced vocabularies in the UI with 3-layer QA [V] ([Claru](https://claru.ai/case-studies/fashion-ai-annotation)).
- **Structure:**
  - **Identity layer:** brand → line → model → colorway / style code → size. Size is read from the tag image and normalized across US/EU/UK/JP.
  - **Visual-attribute layer:** silhouette, material, pattern, hardware, era cues.
  - **Condition layer:** a fixed grade (NWT/NWOT/Excellent/Good/Fair) **plus** flaw instances (type × location × severity, with a box). The RISE set's stains/holes/pilling none/minor/major scale is a good model [V].
  - **Authenticity layer:** a *risk* label with evidence regions, never a binary "authentic" claim.
  - **Furniture:** maker/designer → model → material/finish → era → condition, plus "attributed to" vs "in the style of".
- **Every field needs:** an "unknown / not visible" option, a confidence score, and a link to the evidence image. That makes partial labels usable and prevents guessing.

### Vendors (2026 landscape)
| Vendor | Model | Pricing signals |
|---|---|---|
| **Scale AI** | Self-serve Rapid + enterprise | Rapid ~$0.05 per box, ~$2 per segmentation label [V-ish] ([CostBench](https://www.costbench.com/software/ai-data-labeling/scale-ai/)). Enterprise typically $10K–500K+ per project [V]. Meta bought 49% for $14.3B in Jun 2025, and Google, OpenAI and others pulled spend [V] ([HeroHunt](https://www.herohunt.ai/blog/mercor-vs-surge-vs-scale-ai-2026-buyer-guide/)). Neutrality concern |
| **Surge AI** | Expert per-task / project, no self-serve | Contractor pay ~30–40¢ per working minute (≈$18–24/h); not focused on bulk image boxes [V] |
| **Mercor / Handshake AI / micro1** | Hourly experts + ~30–35% take | Mercor average $109/h (Aug 2026), roles $60–250/h, **design roles ~$70–80/h** [V]. Handshake STEM $100–125/h [V] |
| **Labelbox** | Platform (LBU) + Alignerr workforce | Starter $0.10/LBU; earlier listed labeling $8–10/h [V] ([PricingSaaS](https://pricingsaas.com/companies/labelbox/diffs/2025Q2)). Enterprise has a minimum annual spend [V] |
| **Encord** | Platform; SAM2/YOLO/GPT-4o pre-labels, active-learning loop | Custom pricing [V] ([HITL](https://humansintheloop.org/best-enterprise-data-annotation-platforms-2026/)) |
| **Label Studio** | OSS (Apache-2.0) / Enterprise ~$1.5–5K+/mo | ML-backend pre-labeling claimed to save 40–60% of time [V] |
| **Sama, CloudFactory, iMerit** (managed) | Managed teams | $3–12/h general managed. iMerit $6.48/h offshore and $28.80/h US on AWS Marketplace [V] ([BasicAI](https://www.basic.ai/blog-post/image-annotation-services-cost)). Sama co-built iMaterialist/Fashionpedia [V] |
| **Prolific** | Vetted crowd | Minimum $8/h, recommended $12/h, **+42.9% corporate fee** [V] ([Prolific](https://researcher-help.prolific.com/en/articles/445239-what-is-your-pricing)). Good for relevance and "taste" judgments |
| **Toloka** | Crowd + Crowd-Kit aggregation (Dawid-Skene, Krippendorff α) | Rates not checked [U] |

**Expert networks for fashion, vintage and authentication** (not reachable through generic vendors):
- Professional resellers and vintage dealers, who can be recruited directly at ~$30–60/h [U].
- Consignment authenticators from TRR, Fashionphile, or LegitApp-style shops. Per-check pricing of $3–10+ [V] is a useful way to buy verdicts.
- Furniture: auction-house specialists, vintage dealers on 1stDibs/Chairish, design-history graduates. Mercor's design tier is ~$70–80/h [V].

### Unit costs and throughput
Market ranges from BasicAI's survey [V]:

| Task | Price range |
|---|---|
| Classification | $0.02–0.10 per image; complex multi-label $0.35; custom $0.75 |
| Bounding box | $0.015–0.10 simple, up to $1 |
| Polygon | $0.03–0.20 |
| Segmentation | $0.20–3.00 per image |
| OCR | ~$0.50 per image |

Throughput math [V]:
- $6/h at 300 boxes/h ≈ $0.02 per box; at 60 boxes/h ≈ $0.10 per box.
- In-house $25/h at 80 boxes/h ≈ $0.31 per box.
- MTurk adds 20%; CVAT has a $5K minimum.

**Our estimate [derived]:** a full resale item record (identity + 15–25 attributes + condition + 2–5 flaw boxes + tag OCR, across 4–8 photos) is ~4–10 min for an expert from scratch, or ~1.5–3 min to *verify and correct* a VLM pre-label.
- Generalist verification at $12–20/h ≈ **$0.40–1.00 per item**.
- Expert at $40–80/h ≈ **$1.50–4 per item verified**, or $5–13 from scratch.

Relevance judgments: ~20–60 s each, so **$0.10–0.35 per judgment** at $12–20/h before platform fees [derived].

### Model-assisted pre-labeling and LLM judges
- **eBay (Feb 2026).**
  - Built ~4M e-commerce instruction examples from ~15M listings, using VLM captioning (InternVL-2.5-26B) plus an LLM filter that kept only image-verifiable aspects.
  - Annotated 100K multi-image items with GPT-4.1, then **refined labels using bbox crops**. Better labels improved every model size.
  - A **fine-tuned Gemma3-4B beat zero-shot Gemma3-27B (53.8 vs 44.8 F1)** at ~3.8× speed [V] ([arXiv 2602.11733](https://arxiv.org/pdf/2602.11733)).
- **LLM relevance labels.** Walmart Mexico: approaches human weighted-F1, ~**500× cheaper**, 30 min/record and 2–3 week human turnaround vs seconds [V] ([arXiv 2502.15990](https://arxiv.org/pdf/2502.15990)). Allegro (Aug 2026): local Gemma-4-26B judge reached **κ-quad 0.69, accuracy 0.87** against an expert gold set of 380K+ items. Gold built with 2 blind annotators + expert arbitration on an extended ESCI scale; weak on "substitute" (F1 0.33) [V] ([Allegro](https://blog.allegro.tech/2026/08/automating-search-relevance-llm-as-a-judge.html)). **Implication:** LLM judges work for exact matches but humans still need to label the ambiguous middle.
- **Active learning.** 2–4× more label-efficient than random sampling, even with augmentation. Plain uncertainty sampling ≈ BADGE [V] ([ICML 2021](https://icml.cc/virtual/2021/11191)).

### Inter-annotator agreement (IAA) targets
- Fashion attributes: Cohen's κ **> 0.85**, tracked weekly; retrain any category below 0.80 [V] ([Claru](https://claru.ai/case-studies/fashion-ai-annotation)).
- Common convention: Krippendorff α ≥ 0.80 reliable, 0.667–0.80 tentative [U, standard Krippendorff guidance, not fetched].
- Proposed targets for us:
  - objective fields (brand, size, category, color family): α ≥ 0.85
  - subjective fields (style, era, condition grade): α ≥ 0.70, using an ordinal metric
  - relevance: quadratic-weighted κ ≥ 0.70 between humans (an LLM judge at 0.69 is the bar to beat)
  - authenticity: unanimous expert agreement or the item is excluded

### Gold sets and auditing
- Seed ~5% of every batch with hidden gold items.
- Have 2 blind labels plus expert adjudication on gold and on disagreements (the Allegro pattern).
- Re-label a random 1–2% sample each month to catch drift.
- Freeze a versioned eval set that is never used for training.
- Run the 3-layer pipeline: automated schema checks → peer consensus → expert audit of high-disagreement categories [V].

### How many labels? Published data points
| Setting | Data | Result |
|---|---|---|
| VLM instruction SFT (MM-LIMA) | **200** curated examples (6% of MiniGPT-4's 3,439) | Beat MiniGPT-4 on MME/MMBench [V] ([arXiv 2308.12067](https://arxiv.org/pdf/2308.12067)) |
| Text SFT (LIMA) | 1,000 curated examples | Style/format alignment ([LIMA](https://ar5iv.labs.arxiv.org/html/2305.11206)) [U on details] |
| E-commerce VLM attribute task (eBay) | 100K multi-image items, model-labeled then refined | Fine-tuned 4B > zero-shot 27B [V] |
| E-commerce VLM full adaptation (eBay) | ~4M instruction examples | Domain gains over general models [V] |
| Fashion embedding fine-tune (HopitAI) | **13,557 triplets** (DeepFashion2 shop↔consumer) on a laptop | +2.7 R@1 over FashionSigLIP; +9.4 on street-look. **105K off-domain H&M images *reduced* R@1 by 5** [V] |
| Fashion embedding (ZooClaw, 2026) | 200K → 400K pairs helped slightly (R@10 0.741 → 0.750 LoRA, 0.768 full FT); 800K and +733K Marqo pairs **did not help or hurt** (distribution mismatch) [V] | |
| Pinterest unified visual embedding | 340K human-labeled Shop-the-Look (50K instances) + 540K human-labeled Lens + 800K engagement-derived | Multi-task over all three beat every single source [V] ([arXiv 1908.01707](https://arxiv.org/pdf/1908.01707)) |
| Marqo-FashionSigLIP | 1M+ products with metadata | +57% text-to-image R@1 over FashionCLIP2.0 [V] |
| Entrupy authentication | 3M images (2017) → 25M (2023) | Claims >98% / 99.1% accuracy [V] ([TechCrunch](https://techcrunch.com/2017/08/11/machine-learning-can-tell-if-youre-wearing-swap-meet-louie)) |

**Takeaway.** For SFT, **hundreds to low thousands of high-quality examples per task teach format and behavior.** Tens of thousands to about 100K items move fine-grained accuracy. For embeddings, **10K–400K in-distribution pairs** give most of the gain. Matching the target distribution (consumer phone photos of used items) matters more than volume.

---

## 4. Data flywheels and synthetic data

### Flywheels at comparable companies
- **Seller corrections as labels.**
  - eBay: 10M+ sellers have used its AI tools, 200M+ AI-assisted listings, ~500K per day. It iterates on seller feedback, but acceptance and edit rates are not public [V] ([Modern Retail](https://www.modernretail.co/technology/hoping-to-sway-sellers-ebay-steps-up-ai-tools/)).
  - Depop (Sep 2024): one-photo listing fills category, colour, sub-category and brand; "almost half of listers" tried it in testing; sellers can keep, adjust or delete [V] ([Depop](https://news.depop.com/depop-launches-ai-powered-listing-from-one-photo/)).
  - **Design lesson:** log the model's prediction, the seller's final value, and which fields they touched. "Accepted without edit" is a weak positive (sellers rubber-stamp). "Edited" is a strong correction. "Sold and not returned or disputed" is the strongest confirmation of identity and condition.
- **Expert decisions as labels.** The RealReal's Athena pre-fills attributes and authenticates. It was expected to touch ~50% of items in its authentication centers by end-2025, and 85% of items were priced with AI help [V] ([PYMNTS](https://www.pymnts.com/earnings/2025/the-realreal-ai-tools-improve-sales-operational-efficiency-customer-service/)). Shield checks 50+ attributes per item; humans make the final call; models are "constantly being refined as new items are added" [V] ([TRR](https://resources.therealreal.com/technology-behind-luxury-authentication/)).
- **Buyer behavior as relevance labels.** Pinterest's engagement-mined classes (800K images, 15K classes) were strong in-domain, but weak on the crop-to-product task (11.0 vs 49.2 P@1 with human labels). Combining sources won [V]. **Engagement data needs debiasing** (position bias, popularity) and works best *alongside* human gold.
  - Useful signals: saves/likes after search, click → watch → purchase, "not what I wanted" dismissals.
  - **Returns or "item not as described" disputes are negative labels for identity and condition.**
- **Cross-listing gives us something unusual.** The same physical item is listed on several platforms with different photos and titles. That yields free positive pairs for instance-level embedding training, and platform category mappings give weak attribute labels.

### Synthetic data: what works and what doesn't
- **Works:**
  - Standard and photometric augmentation (lighting, blur, JPEG, crops, background swap) to imitate phone photos.
  - **Synthetic pretraining followed by a small amount of real fine-tuning.** Industrial detection: synthetic + real fine-tune reached 82–83.7 AP vs ~77 real-only; gains plateaued at ~17.5K synthetic images; 1.7K synthetic was already decent [V] ([arXiv 2211.16066](https://arxiv.org/pdf/2211.16066)).
  - **Diffusion augmentation in low-data regimes.** +8–11 pts at 5-shot fine-grained (Birds, Aircraft); DA-Fusion up to +10 pts few-shot. Gains shrink as real data grows (Birds 10-shot +3.6) [V] ([arXiv 2603.08364](https://arxiv.org/pdf/2603.08364); [DA-Fusion](https://arxiv.org/pdf/2302.07944)).
  - **Renders from licensed 3D assets** for furniture (ABO 3D models, CC BY) for multi-view and pose coverage.
- **Doesn't work or is risky:**
  - **Fully replacing real data:** Caltech-101 fell from 76.1% to 51.4% [V].
  - **Subtle-cue tasks:** diffusion augmentation *lowered* accuracy on species-level iNat and medical cues; SD3.5 lost fine details vs SD1.5 (Birds 71.7 → 58.1) [V]. This maps directly to **authenticity cues (stitching, fonts, hardware) and flaw detection. Do not train authenticity on generated images.**
  - **FID doesn't predict downstream accuracy** [V].
  - Off-distribution "more data" (H&M studio images, Marqo pairs) hurt [V].
- **Targeted uses for us:**
  - Synthetic tag/label images for size and care OCR (render text onto tag templates, with wrinkles and wear).
  - Synthetic flaws (stains, pilling, holes) for detector *pretraining* only, always validated on real flaws.
  - Diffusion background swaps.
  - "Same item, different photo" positives for embeddings.

---

## 5. Recommended data program for us

**Guiding principles:**
- (1) The flywheel from our own sellers is the moat. Public data is for bootstrapping and evaluation.
- (2) Build the eval set first.
- (3) VLM pre-labels with human verification by default; experts only where generalists measurably fail.
- (4) Provenance ledger and ToS consent from day one.
- (5) Authenticity is a *risk score plus routing to partners*, not a claim we make, until we have expert-labeled volume.

### What to build ourselves (no public substitute)
1. **Resale item ontology v1:** fashion first, furniture v2. Built on Fashionpedia + marketplace item-specifics + RISE condition scales, with unknown/confidence on every field.
2. **Gold eval sets (frozen):**
   - (a) Identity/attribute gold: ~3K fashion items, multi-photo, including tag images.
   - (b) Condition/flaw gold: ~1K items with boxes.
   - (c) Search relevance gold: ~400 real buyer queries (text + photo + "like this but…") × ~30 candidates ≈ 12K pairs on an extended ESCI scale with a "design-equivalent" grade.
   - (d) Authenticity: ~500 expert-verified items in our top 10 brands, mixed authentic/counterfeit, sourced through an authenticator partner.
3. **SFT set for the VLM:** item → structured JSON (identity, attributes, condition, flaws, tag OCR, evidence regions).
4. **Embedding pairs:** same-item cross-listing pairs, seller-photo ↔ retail-catalog (affiliate feed) pairs, query ↔ purchased-item pairs, and hard negatives (same brand, different model or colorway).
5. **Tag OCR set:** real tag crops + synthetic renders.

### Phases, label volumes, budgets (year 1). Budgets are estimates [derived from §3 unit costs]

| Phase | Timing | Labels | Who | Est. cost |
|---|---|---|---|---|
| **0. Ontology + gold** | Months 0–2 | Ontology; 3K identity gold (2 blind expert labels + adjudication); 1K flaw gold; 12K relevance pairs × 3 judgments; 500 authenticity verdicts | Reseller/vintage experts for identity and condition ($40–60/h, ~$10–15 per gold item all-in). Prolific/vetted generalists for relevance ($0.15–0.35 per judgment incl. fee). Authenticator partner ($10–40 per luxury verdict) | **$50K–90K** (gold $30–45K; flaw $8–15K; relevance $6–13K; authenticity $5–20K) + tooling (Label Studio OSS free, or Labelbox/Encord ~$20–60K/yr) |
| **1. Bootstrap SFT + embeddings** | Months 2–5 | 20–50K items labeled by VLM pre-label + generalist verify; 10–20% expert review on hard brands; 2–5K hand-curated "perfect" SFT examples; 100–200K mined embedding pairs + 10–20K human-verified hard negatives | Managed generalist team (offshore $6–12/h or US $15–25/h) with expert reviewers; active learning picks what experts see | **$30K–80K** |
| **2. Flywheel + furniture** | Months 5–12 | 200K–1M items labeled *implicitly* (seller edits, sales, returns) with 1–2% human audit; 10–30K furniture items (designer/model/material/era) with expert verification; relevance refresh 5K pairs/quarter; LLM-judge calibrated to gold for continuous search eval | In-house "data steward" (1 FTE) runs QA; furniture design experts ($60–80/h); generalists for audits | **$70K–180K** |
| **Total year 1** | | | | **~$150K–350K labeling** + ~1 FTE data-ops lead + tooling |

**Volume rationale:**
- Published evidence says hundreds to thousands of curated examples fix SFT format.
- About 100K well-labeled items made a 4B VLM beat a 27B zero-shot model (eBay).
- 10K–400K in-distribution pairs capture most embedding gains (HopitAI, ZooClaw).
- Beyond that, the flywheel should supply volume for free.

### Who labels
- **Generalists (vetted crowd / managed teams):** category, color, visible attributes, box drawing, tag transcription, verifying VLM pre-labels, search relevance on clear cases.
- **Domain experts (resellers, vintage dealers, stylists):** brand/model/colorway ID for long-tail and vintage, era dating, condition grading calibration, adjudicating disagreements, writing guidelines and examples. Recruit directly from our own power sellers. They know the domain and they are cheaper than Mercor-tier rates.
- **Authenticators (partners, per check):** authenticity labels only, with ≥2 independent verdicts. Unanimity is required for inclusion.
- **Furniture design specialists:** maker/designer attribution, "attributed to" vs "in the style of", period, material.
- **LLM/VLM:** first-pass labels everywhere, plus a relevance judge calibrated against the human gold (target κ-quad ≥ 0.70). Never used for authenticity or as the final word on fields with low IAA.

### QA process
1. **Guidelines with visual examples** for every field, including borderline cases. Version them, and re-certify annotators on each version (a qualification test of 50 gold items, passing ≥ 90% on objective fields).
2. **Hidden gold in 5% of tasks.** Auto-pause any annotator who falls below threshold.
3. **2 blind labels on 10–20% of production tasks** (100% for gold). Compute IAA per field weekly with these targets:
   - objective fields: α ≥ 0.85
   - subjective fields: α ≥ 0.70 (ordinal)
   - relevance: κ-quad ≥ 0.70
   - Fields below target trigger guideline revision and retraining.
4. **Expert adjudication** of disagreements and of high-value or low-confidence items selected by uncertainty sampling.
5. **Automated checks:** schema/taxonomy validity, brand↔model consistency, size-format normalization, duplicate detection.
6. **Monthly audit:** 1–2% random re-label plus a drift report. Track model-vs-gold accuracy per category on the frozen eval sets.
7. **Flywheel hygiene:** treat seller "accept" as weak and edits as strong. Count sales without returns as confirmation. Debias engagement signals for position and popularity. Keep flywheel labels in a separate tier so we can weight or ablate them.
8. **Provenance:** tag every image and label with source, license, consent status and annotator ID, so data can be deleted or retrained around on request.

### Immediate next steps
- Add an ML-training license and opt-out to our seller ToS. Instrument prediction-vs-final-value logging in the listing flow.
- Download ABO, ESCI, Fashionpedia and the RISE set for commercial bootstrapping. Gather DeepFashion2, Fashion-Gen, FashionIQ, eProduct, SOP and ILIAS for **internal eval only**, after legal review of each agreement.
- Recruit 5–10 expert resellers (vintage, luxury, sneakers, streetwear) and 1–2 furniture dealers. Pilot 200 items to measure minutes per item and IAA before committing budget.
- Ask affiliate networks for a written ML-use addendum. Open talks with one authenticator for per-check API pricing and outcome-data rights.

---

### Verification gaps to close
- DeepFashion2, Fashion-Gen, H&M, Shopee and iMaterialist exact license text. Kaggle rules pages were not fetched.
- Marqo-GS-10M license.
- eBay API AI-training clause (July 2025).
- Bartz, Kadrey and Ross details.
- Current status of X v. Bright Data and Reddit/Google v. SerpApi.
- Depop, Vinted and Grailed ToS text.
- Krippendorff thresholds (from memory).
