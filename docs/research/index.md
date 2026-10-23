# Building a "universe of secondhand" index: sources, methods, infrastructure, strategy

Research date: 2026-10-23. Scope: US first. The aim is better coverage and freshness than Phia, which claims 300M+ items. Google Shopping, Lyst and ShopStyle are adjacent competitors.

**Labels used in this report**
- **[V]**: verified on the cited page.
- **[U]**: unverified. This covers my estimates, memory and secondary sources I could not confirm.
- **[calc]**: my own arithmetic.

**Research limits**
- The web-search budget ran out before I could check ShopStyle, Klarna/PriceRunner, Grailed, Mercari, LiveAuctioneers and Invaluable volumes, Etsy's rate limits and Diffbot pricing. Those cells are marked [U].
- developers.etsy.com was blocked by a permission prompt that nobody answered.

---

## 1. Source landscape

"Est. volume" means live listings unless noted. Many are self-reported.

**Freshness difficulty**
- **Low**: an API or feed with change data.
- **Med**: crawlable, with a predictable structure.
- **High**: anti-bot protection, login walls or no sold signal.

**Risk**: combines legal/ToS risk with operational risk of being blocked.

| Source | Est. volume | Access method | Freshness difficulty | Risk | URL |
|---|---|---|---|---|---|
| **eBay** | 2.3B live listings worldwide (Q1 2025 Fast Facts, via secondary source) [V-secondary]. Pre-owned is a minority, but "Recommerce (Pre-Owned and Refurbished)" GMV grew 20%+ YoY in Q2 2026 [V]. Total FY25 GMV was $79.6B [V]. | **Buy Browse API** (search, searchByImage) needs eBay Partner Network (EPN) membership. Default 5,000 calls/day, max 200 items per call, max 10,000 results per query (offset ≤ 9,999) [V]. **Buy Feed API** mirrors whole categories as feed files: Feed v1 allows 75k calls/day, and the Beta item_snapshot allows 75k/day [V]. Requires EPN affiliate status plus approval of a "limited release" business model; approval is not guaranteed [V]. Limits can be raised through the "Application Growth Check" [V]. | Low via the Feed API, Med via Browse. The 10k result cap forces you to slice queries by category, price and other facets. | Low if you comply. There are display rules (eBay logo, shipping shown separately, "Partners and users are not permitted to sort items" in the checkout context) [V]. | https://developer.ebay.com/develop/get-started/api-call-limits · https://developer.ebay.com/develop/api/buy/browse_api.md · https://www.developer.ebay.com/api-docs/buy/buy-requirements.html · https://redstagfulfillment.com/how-many-items-are-listed-on-ebay/ |
| **Depop** (eBay-owned since **2026-07-30**) | 3M+ active sellers and 7M active buyers; about $1B GMS in 2025, with US GMS up about 60% [V]. Listing count not published. | Public web pages and internal JSON. **New option:** a data relationship through eBay now that eBay owns it [U]. Gem said it was "seeking permission" from Depop [V]. | Med–High | Med | https://news.depop.com/ebay-to-acquire-depop-from-etsy/ · https://ebay.q4cdn.com/610426115/files/doc_financials/2026/q2/2026_Q2_eBay_Earnings_Presentation_Final.pdf |
| **Poshmark** (Naver) | "More than 200 million available listings" and 80M+ users (undated) [V-Wikipedia]. Sacra cites 150M+ users [V-secondary]. | No public catalog API. The Posh affiliate program is influencer-oriented, with no feed found [V, 2021 article]. Options are a crawl, a data vendor, or a partnership. Beni and Phia both report a Poshmark partnership [V-secondary]. | High: a huge volume of stale listings and no sold flag in the feed. | Med–High | https://en.wikipedia.org/wiki/Poshmark · https://fashionunited.com/news/business/resale-browser-extension-beni-launches-ios-app-announces-new-partnerships/2024020658268 |
| **Mercari US** | 21M active customers (March 2025, possibly global) [V-secondary]. Listing count not published [U: tens of millions]. | Crawl only. The site is behind Cloudflare and datacenter IPs are blocked; an Apify actor needs US residential proxies at $1.50 per 1k listings [V]. Search results carry `status` (on_sale/trading) [V]. | High | Med–High | https://apify.com/quine/mercari-scraper.md · https://sacra.com/chat/h/19343852-e146-4b98-b511-1010ad0e7ba0/ |
| **Vinted** | About **1B searchable items** in its own Vespa index, mostly in the EU [V]. US launch began in New York in January 2026 [V-secondary]. 2025 GMV €10.8B [V-secondary]. | Crawl. No public API found. A partnership is unlikely until US growth needs traffic [U]. | High | Med–High (EU database rights matter if you go global) | https://www.zenml.io/llmops-database/migrating-from-elasticsearch-to-vespa-for-large-scale-search-platform · https://en.wikipedia.org/wiki/Vinted |
| **Grailed** | Listing count not published [U: around 10M]. | Affiliate program on FlexOffers: 8.8% of sales from new customers, 15-day cookie; feed not confirmed [V]. Crawl otherwise. | Med | Med | https://www.flexoffers.com/affiliate-programs/grailed-affiliate-program |
| **Etsy** (vintage = 20+ years old) | 100M+ active listings, 8M sellers, 96M buyers (end of 2024) [V]. The vintage share is not published [U: roughly 10–15%]. | **Open API v3** with an API key and OAuth. Rate limits not verified, because the documentation page was blocked [U: memory says about 10 QPS and 10k QPD by default]. ToS restricts caching and display [U]. | Low–Med | Low (if you comply) | https://en.wikipedia.org/wiki/Etsy · https://developers.etsy.com/documentation/ (blocked) |
| **The RealReal** | 1M+ active buyers; "over 50 million item sales since inception"; about 50% of listed products sell within 30 days; marketplace sell-through above 80% (FY2025 10-K) [V]. | First-party affiliate program: about 5% per sale plus $5 per consignment [V-secondary]. Directories list Rakuten Advertising, Impact, Skimlinks and ShopStyle Collective [V-secondary]. Feed not confirmed [U]. | Med: fast sell-through means sold detection matters. | Low | https://www.sec.gov/Archives/edgar/data/1573221/000157322126000010/real-20251231.htm · https://affsignal.com/merchant/Therealreal |
| **ThredUp** | "Tens of millions of unique items"; distribution centers can hold 7.5M+ items; processes 100k+ unique SKUs per day (FY2025 10-K) [V]. | Affiliate program at 4–30%, run through VigLink/Sovrn (Lasso) and FlexOffers [V-secondary]. ThredUp also runs **Resale-as-a-Service** for brands [V]. | Med | Low | https://www.sec.gov/Archives/edgar/data/1484778/000148477826000007/tdup-20251231.htm · https://getlasso.co/affiliate/thredup-inc/ |
| **Vestiaire Collective** (owns Tradesy) | About 6M curated items and about 30k new per day (undated) [V-Wikipedia]. | Affiliate program on CJ: 10%, 15-day cookie [V-secondary]. Also listed on FlexOffers. Feed not confirmed [U]. | Med | Low | https://en.wikipedia.org/wiki/Vestiaire_Collective · https://getlasso.co/affiliate/vestiaire-collective-uk/ |
| **1stDibs** | About **1.9M listings** and 5,700 sellers (year-end 2025, 10-K) [V]. | Affiliate program through Ascend [V]. Also appears in Channel3's product-graph API [V]. | Low–Med | Low | https://www.sec.gov/Archives/edgar/data/1600641/000160064126000007/dibs-20251231.htm · https://www.1stdibs.com/answers/does-1stdibs-have-an-affiliate-program |
| **Chairish** | 1M+ items sold since launch; about 85% of listings are US-located (June 2025) [V]. Live count not published [U: around 1M]. | Affiliate program; listed in Channel3 [V]. Crawl as an option. | Low–Med | Low | https://www.uschamber.com/co/good-company/the-leap/chairish-vintage-furniture-marketplace |
| **Facebook Marketplace** | About 1.1–1.2B monthly users and "4B+ listings (estimated)" from a poorly sourced stats site [U]. | No API. Much of it requires login. Logged-off public scraping survived Meta's contract claim in *Meta v. Bright Data* (2024-01-23) [V]. | Very high | **High**: Meta litigates, and login walls rule out logged-in scraping. | https://www.sci-tech-today.com/stats/facebook-marketplace-statistics/ · https://www.fbm.com/post/102kqw7/ |
| **OfferUp** (merged Letgo in 2020) | About 20M MAU (2021) [V]. Listings not published. | Crawl only. | High | Med–High | https://en.wikipedia.org/wiki/OfferUp |
| **Craigslist** | Not published. | Crawl. **Avoid**: in *Craigslist v. 3Taps* (2013), continuing to scrape through proxies after a cease-and-desist letter and an IP block was held to be access "without authorization" under the CFAA. 3Taps paid $1M in the 2015 settlement [V]. | High | **Very high** | https://en.wikipedia.org/wiki/Craigslist_Inc._v._3Taps_Inc. |
| **Catawiki** | 3.7M objects sold in FY2025, about 71k per week [calc]. Lots listed grew about 30% YoY in Q1 2026 [V]. EU-centric. | Crawl or partnership. | Low: auction end times are known in advance. | Med | https://www.catawiki.com/en/press/1949-catawiki-delivers-profitable-growth-in-2025-driven-by-strong-business-performance |
| **LiveAuctioneers / Invaluable / HiBid** | Not verified [U: low millions of live lots across thousands of auction houses]. | Affiliate or partnership, or a crawl. Gem already indexes LiveAuctioneers [V]. | Low–Med: end times known. | Med | https://www.defunkd.com/gem-app/ |
| **Long tail: independent vintage and consignment stores** (Shopify, Squarespace, Wix, BigCommerce, WooCommerce) | About 3.3M websites carried schema.org Product markup in the 2024 Web Data Commons extraction [V-secondary]. The secondhand subset is not published [U: about 20–60k US vintage, consignment and resale stores with roughly 10–40M items]. | Shopify exposes a public `/products.json?limit=250&page=N` endpoint with no authentication. It returns variants, price and `available`; some stores block it (403) or rate-limit it [V]. Other platforms: sitemap.xml plus schema.org Product JSON-LD [V for the general practice]. | **Low**: cheap to sweep daily. | Low (honor robots.txt and blocks) | https://dev.to/shan_yun_ab0c7ad30b46ad2d/shopifys-open-secret-every-store-exposes-productsjson-30ni · https://www.netsolutions.com/?p=114016 |
| **Brand resale programs** (Patagonia Worn Wear, Treet-powered sites, ThredUp RaaS, Trove) | Small individually; there are hundreds of them [U]. | Often run on Shopify, so `/products.json` works. Partnerships are easy because brands want distribution. Beni partners with Worn Wear and Treet sites [V]. | Low | Low | https://fashionunited.com/news/business/resale-browser-extension-beni-launches-ios-app-announces-new-partnerships/2024020658268 |

**Takeaways**
- In the US, **eBay plus Poshmark plus Etsy already exceed 300M listings** on paper. Phia's "300M+" is therefore credible at a raw-listing level, but probably includes a large stale and duplicate fraction [U].
- The real differentiator is not raw count. It is the number of **live, de-duplicated items**, together with freshness.
- Data vendors and aggregation tools:
  - **Bright Data** sells per-domain datasets with no public pricing, priced per 1k records [V-secondary].
  - **Apify** actors exist for eBay, Mercari, Grailed, Depop and Catawiki, priced at roughly $1.50–$3.40 per 1k results [V].
  - **Channel3** sells a "product graph" API for AI shopping agents, covering 1stDibs and Chairish, with 1,000 free searches per month [V]. It is worth a trial.
  - **Diffbot's** Knowledge Graph extracts product fields, but pricing and counts were not verified [U].
- **Google Shopping / Merchant data:** there is no public API for querying Google's index. Scraping Google results is now litigated (*Google v. SerpApi*, below). Google's index is a competitor's asset, not a source.
- **Common Crawl:** the August 2026 crawl has 2.14B pages (360 TiB uncompressed), of which 0.7B are new URLs [V]. It is useful for **discovering** long-tail store domains (Shopify fingerprints, Product JSON-LD). It is useless for freshness, because it runs monthly and is sampled.

---

## 2. Access methods and their limits

### Official APIs

**eBay**
- **Browse API**
  - Defaults: 5,000 calls/day, 200 items per call, 10,000 results per query [V].
  - Throughput ceiling: 5,000 × 200 = **at most 1M item-results per day** [calc]. That is enough for query-time federation or a small mirror, but not for indexing more than 100M items.
  - Production use requires EPN membership, affiliate tracking (`itemAffiliateWebUrl` and the `X-EBAY-C-ENDUSERCTX` header) and business-model approval [V].
- **Feed API:** the right tool for mirroring. It provides category feed files plus item snapshots, at 75k calls/day [V]. It requires an EPN affiliate and approval, and the commercial terms depend on your contract [V].

**Etsy Open API v3**
- Uses an API key plus OAuth 2.
- I could not verify the rate limits from the documentation (blocked). The working assumption from memory is about 10 QPS and 10k QPD by default, raisable on request [U].
- At 100 listings per call, 10k QPD gives about 1M listing reads per day [calc, U].

### Affiliate networks and feeds

Programs found:

| Platform | Program / network | Terms |
|---|---|---|
| The RealReal | Own program plus Rakuten, Impact and Skimlinks (per directory) | About 5% |
| ThredUp | VigLink/Sovrn and FlexOffers | 4–30% |
| Vestiaire | CJ | 10% |
| Grailed | FlexOffers | 8.8% |
| 1stDibs | Ascend | — |
| eBay | EPN | Mandatory for the Buy APIs |
| Poshmark | Influencer campaigns only | — |

All of these are [V-secondary] except eBay EPN [V].

Caveats:
- **Product datafeeds were not confirmed for any of the resale sites** [U]. Networks such as CJ, Rakuten, Impact and Awin offer feed products, but whether a merchant publishes one is the merchant's choice. Ask each program manager directly.
- **Skimlinks and Sovrn** give you monetization (link rewriting) across thousands of merchants, but not catalog data.

### Open web
- **Shopify `/products.json`:** 250 products per page, paginate until empty. No authentication. Some stores block it [V]. Whether it includes `updated_at` was not verified [U]; from memory it does, along with `created_at` and `published_at`.
- **Sitemaps plus schema.org Product/Offer JSON-LD:**
  - This is the same signal Google uses for its automatic website-crawl listings: title, price, availability and image are required [V].
  - About 3.3M sites used Product markup in 2024 [V-secondary]. On HTTP Archive's 2024 mobile crawl, Product appeared on about 1.5% of pages via Microdata and 0.77% via JSON-LD [V-secondary].

### Data vendors and crawl infrastructure, unit prices

| Vendor / tier | Price |
|---|---|
| Zyte API, HTTP | $0.06–$1.27 per 1k successful responses (tier 1 "Simple" to tier 5 "Advanced"; pay-as-you-go to $500/mo plans) [V] |
| Zyte API, browser-rendered | $0.48–$16.08 per 1k [V] |
| Bright Data Web Unlocker | About $3.00 per 1k successes, pay-as-you-go [V-secondary] |
| Bright Data Scraping Browser | About $8 per 1k sessions [V-secondary] |
| Bright Data residential proxies | $8.40/GB pay-as-you-go, from $3/GB with commitment [V-secondary] |
| Bright Data datacenter proxies | $0.60–0.90/GB [V-secondary] |
| Apify marketplace actors | About $1.50–$3.40 per 1k listings [V] |

### Partnerships
- Beni grew to "50+ partners", including Poshmark, ThredUp, Grailed, TRR, Vestiaire, eBay, Worn Wear and Treet sites, and ingests their **partner data feeds** [V].
- This shows that resale platforms will give feeds to a traffic-sending aggregator. Pay-per-sale makes the aggregator cheap customer acquisition for them.

### Legal and ToS risk (US)

**CFAA and public data**
- *hiQ v. LinkedIn* (9th Cir.): automated collection of **public** data is not "without authorization" under the CFAA [V-secondary].
- hiQ was later liable on contract and fake-account grounds [U: from memory, 2022 district ruling and settlement].
- Rule: **never use fake or logged-in accounts.**

**Contract (ToS)**
- *Meta v. Bright Data* (N.D. Cal., 2024-01-23): **logged-off** scraping of public Facebook and Instagram data was not "use" under Meta's terms, so there was no breach. A tortious-interference claim remained [V].
- *X v. Bright Data* was also dismissed. The court warned of "information monopolies" [V-secondary].

**Revocation**
- *Craigslist v. 3Taps* (2013): a cease-and-desist letter plus an IP block revokes authorization, and **evading the block with proxies is a CFAA violation** [V].
- Rule: when a site blocks you or sends a C&D, stop or negotiate.

**Anti-bot circumvention as DMCA §1201**
- *Google v. SerpApi*, filed 2025-12-19. The theory is that bypassing SearchGuard (JS challenges, CAPTCHAs, IP rotation, fake browser profiles) is circumvention of an access control [V]. These are allegations only, but the theory directly threatens "unblocker" vendors and CAPTCHA solving.
- Treat heavy anti-bot bypass on hostile sites as a legal risk, not just a cost.

**AI agents**
- *Amazon v. Perplexity (Comet)*: a district-court preliminary injunction under the CFAA (March 2026) was vacated 3-0 by the 9th Circuit (about 2026-08-04). The court held that the **user**, not the agent, accesses Amazon when the agent acts on the user's behalf [V-secondary].
- This favors **user-side, query-time fetching** (for example, a browser extension) over server-side crawling of logged-in surfaces.

**Infrastructure gatekeepers**
- Cloudflare, which carries about 20% of web traffic, has blocked AI crawlers by default since July 2025. From **2026-09-15** it also blocks "mixed-use" crawlers from monetized pages, and it is piloting pay-per-crawl [V].
- Expect more sites to require identified, verified, or paid crawlers.

**Images and copyright**
- Store embeddings, perceptual hashes and URLs. Link out, and hotlink or proxy thumbnails rather than re-hosting galleries [U: standard practice; get counsel].

---

## 3. How others build and maintain their indexes

**Phia**
- Item count claims over time:

  | Date | Claim | Status | Source |
  |---|---|---|---|
  | April 2025 | 250M+ secondhand items | Retail-expert quote | Digital Commerce 360 |
  | October 2025 | **350M+ items "in its in-house search database"**, "integrates with more than 150 second-hand platforms" | [V] | TechCrunch |
  | January 2026 | 300M+ products | [V] | Forbes AU |

- Site coverage: "40,000+ retail and resale sites" (company) [V].
- Origin: started as a browser extension that "searched the web for resale comparables" [V]. Uses AI to detect exact image, price, brand, color and shape [V]. Partnerships with TRR, ThredUp, Poshmark and eBay are reported second-hand [V-secondary].
- Funding: $35M Series A at a $185M valuation, total funding above $43M. Hiring for "ML infrastructure, sourcing models, personalization" [V]. Has staff with eBay and Pinterest backgrounds [V].
- No engineering posts found.
- My read [U]: Phia combines partner and affiliate feeds for the big platforms, a crawl of retail sites (the 40k number is mostly *new* retail, for price comparison), and extension-side signals.
- Sources: https://techcrunch.com/2025/10/29/phias-founders-on-how-ai-is-changing-online-shopping/ · https://www.digitalcommerce360.com/2025/04/28/phia-ecommerce-startup-phoebe-gates/ · https://www.forbes.com.au/?p=175573 · https://pulse2.com/phia-30-million-in-funding-at-180-million-valuation/amp/

**Google Shopping Graph**
- 60B+ listings (May 2026). "2B+ listings updated every hour", a figure cited since November 2025 [V].
- At that rate a full cycle takes about 30 hours [calc, from ppc.land].
- Built mostly from **Merchant Center feeds**, plus automatic import from site crawl and structured data (since about June 2024). Automatic import is said to refresh every 24 hours, but a January 2026 check found products 9–10 days stale [V].
- Lesson: even Google cannot get uniform freshness from crawl. Feeds plus prioritized refresh win.
- Sources: https://ppc.land/googles-heiko-hotz-pitches-60-billion-listings-as-fuel-for-shopping-agents/ · https://searchengineland.com/google-product-listings-website-crawl-443243

**Lyst**
- 2018 figures: about 12k brands, 5M products, commission-based model. Brands bid higher commission for placement. Half of its 150 staff were data scientists or engineers [V].
- Feed and affiliate based, with no resale focus.
- Source: https://www.glossy.co/fashion/how-the-lvmh-backed-aggregator-lyst-does-business/

**ShopStyle, Klarna/PriceRunner**
- Not researched because the search budget was exhausted.
- From memory [U]: both are affiliate-feed and merchant-feed aggregators with offer-to-product matching. ShopStyle is owned by Rakuten (ShopStyle Collective).

**Beni**
- Ingests partner feeds from 40–50+ marketplaces and claims about four-fifths of online resale listings [V].
- Normalizes messy sizing: one eBay feed search returned about 100k size variants, which needed a dedicated model [V].
- Moved from Google Vision Product Search to its own reverse-image search [V].
- Sources: https://startup.google.com/alumni/stories/beni/ · https://fashionunited.com/news/business/resale-browser-extension-beni-launches-ios-app-announces-new-partnerships/2024020658268

**Gem (vintage search)**
- Federated search across eBay, Etsy, Grailed, Poshmark, TRR, Vestiaire, Ruby Lane, LiveAuctioneers and others, plus hundreds of indie stores that ask to be included.
- Asked Depop for permission. Affiliate revenue [V].
- Source: https://www.defunkd.com/gem-app/

**Vinted (the marketplace itself, as a scale benchmark)**
- About 1B searchable items on **Vespa**, with 60 content nodes, 12 container nodes and 3 config nodes. The previous setup was 6 Elasticsearch clusters with 120+ nodes.
- Performance: 20k QPS at p99 under 150 ms; 10.3k update/remove operations per second (tested up to 50k); about 5 s from write to visibility; 200k-candidate ranking depth.
- Hybrid "triangle of search": lexical, vector and structured filters in one query [V].
- Source: https://www.zenml.io/llmops-database/migrating-from-elasticsearch-to-vespa-for-large-scale-search-platform

**eBay**
- Multimodal recommendations: BERT text plus ResNet-50 image embeddings, fused in a two-tower model. Image-title mismatch is used as a quality signal. Up to +15.9% CTR [V].
- Source: https://innovation.ebayinc.com/stories/beyond-words-how-multimodal-embeddings-elevate-ebays-product-recommendations/

**Deduplication reference**
- arXiv 2509.15858: BERT text plus MAE image embeddings reduced to 128 dimensions, with a decider model on top. Runs on **Milvus** for catalogs of 200M+ items in about 100 GB of RAM, reaching macro-F1 0.90 versus 0.83 for third-party tools [V]. The authors' affiliation is not shown on the abstract page.
- Source: https://arxiv.org/abs/2509.15858v1

### Crawling at scale: practical patterns
These are a synthesis [U], grounded where cited.

- **Discovery versus refresh are separate pipelines.**
  - Discovery reads search or category pages sorted by newest, plus sitemaps. Each page yields 24–250 items.
  - Refresh re-checks known items, and is the expensive part.
  - Never crawl every item page to detect new items.
- **Sold detection, cheapest to most expensive:**
  1. Explicit status in list or search JSON (Mercari exposes `on_sale`/`trading` [V]; Shopify exposes `available` [V]).
  2. Absence from a full category sweep, marked "likely sold" after 2 consecutive misses.
  3. Per-item HEAD/GET (404, "sold" badge).
  4. **Lazy validation at query time** of the top-k results shown to a user.
  - Auctions carry end times, so schedule a check at end time plus a buffer.
- **Politeness:** per-host concurrency budgets, honoring robots.txt and `Crawl-delay`, an identifiable user agent and contact page for friendly hosts, and exponential backoff on 429/403. Stop entirely on a cease-and-desist letter (because of *3Taps*).
- **Headless browsers are 10–30× the cost of HTTP.** For example, Zyte tier 4 is $0.34 per 1k for HTTP versus $3.84 per 1k for browser rendering on the $500 plan [V]. Reverse-engineer the site's own JSON endpoints and render only as a fallback.
- **Pagination caps:** eBay's cap is 10k results per query [V], and others are similar [U]. Slice by category × price band × size × condition until each slice is under the cap.

---

## 4. Infrastructure and cost for multimodal search at 100M–1B items

### Per-item assumptions [U, stated so they can be changed]
- One primary image embedded (other images are only perceptually hashed for dedupe), at about 512×512 = 262,144 pixels.
- Text of about 200 tokens: title, brand, size, condition, short description.
- One fused vector of 1,024 dimensions.
- About 1.5 KB of stored attributes (URL, price, size, status, seller ID, hashes).
- **Churn: 2% of the index is new each day.** Vestiaire adds about 30k items per day to about 6M, or 0.5%/day [V-calc]. TRR sells about 50% of items within 30 days [V]. Peer-to-peer apps churn faster [U].

### Embedding cost

Unit prices:

| Model | Image | Text | Batch |
|---|---|---|---|
| Voyage multimodal-3/3.5 | $0.60 per billion pixels, per-image min $0.00003 / max $0.0012 | $0.12 per M tokens | 33% off [V] |
| Gemini Embedding 2 (released 2026-05-20, 128–3,072 dims) | $0.45 per M | $0.20 per M tokens | text $0.10 per M [V] |
| Cohere Embed v4 | $0.47 per M image tokens | $0.12 per M tokens | — [V-secondary] |
| voyage-3.5-lite (text only) | — | $0.02 per M tokens | [V] |

[calc] Per item, using Voyage multimodal:
- Image: 262,144 px × $0.60 / 1e9 = **$0.000157**
- Text: 200 tok × $0.12 / 1e6 = **$0.000024**
- Total: **about $0.00018 per item**, or **about $0.00012 per item** with the batch discount.

[calc] Gemini Embedding 2, *if* an image costs about 258 tokens [U: tokens per image not verified]:
- Image: 258 × $0.45 / 1e6 = $0.000116
- Text, batch rate: 200 × $0.10 / 1e6 = $0.00002
- Total: **about $0.000136 per item**

| Index size | One-time API embed (Voyage, batch) | Daily new at 2% churn | Monthly API re-embed for churn | Self-hosted open model (e.g. SigLIP-2 or a fashion-tuned CLIP/SigLIP) |
|---|---|---|---|---|
| 10M | 10M × $0.00012 = **$1.2k** | 200k | 200k × 30 × $0.00012 = **$720/mo** | ≈$5 one-time; <$50/mo |
| 100M | **$12k** | 2M | **$7.2k/mo** | ≈$45 one-time; ≈$100/mo |
| 500M | **$60k** | 10M | **$36k/mo** | ≈$220 one-time; ≈$400/mo |
| 1B | **$120k** | 20M | **$72k/mo** | ≈$450 one-time; ≈$800/mo |

How the self-hosted column was estimated [U]:
- Assume about 1,000 images/s per L4/A10-class GPU at about $0.80/hour, including decode.
- 1B images ÷ 1,000/s = 1M GPU-seconds = **278 GPU-hours ≈ $222**. I doubled that for overhead to get about $450.
- Churn at 1B: 20M per day ÷ 1,000/s = 5.6 GPU-hours/day, about $4.50/day. I padded that to about $800/mo.
- Verify throughput with a benchmark before relying on it.

Implications:
- **Self-host the image encoder.** API embedding costs dominate the bill at more than 100M items with churn. Use API models only for evaluation or for the query side: queries are about 1k–100k per day, which costs a few dollars.
- **Image fetch bandwidth** is the hidden cost.
  - At about 50 KB per image, 1B images is about 50 TB [calc].
  - From image CDNs over normal cloud ingress, this is cheap.
  - Through residential proxies at $3/GB it would cost **$150k** [calc]. So fetch images directly from the CDNs, which are rarely behind anti-bot protection [U], and never through unblockers.

### Vector, lexical and attribute storage

[calc] Bytes per item:

| Component | Bytes per item | At 1B items |
|---|---|---|
| float32 vector, 1,024 dims | 4,096 B | 4.1 TB |
| int8 scalar-quantized vector | 1,024 B | 1.0 TB |
| Binary-quantized vector | 128 B | 128 GB |
| HNSW graph (M=16, about 2 × M × 4 B at layer 0) | about 128 B | 128 GB |
| Attributes plus lexical fields | about 1.5 KB | 1.5 TB |

A RAM-light design keeps binary vectors and the graph in RAM, holds int8 or float32 vectors on SSD for rescoring, and keeps the lexical index on SSD.

| Scale | RAM-resident needs (binary vectors + graph) | SSD needs (int8 + attributes + inverted index) |
|---|---|---|
| 10M | ≈2.6 GB | ≈30 GB |
| 100M | ≈26 GB | ≈300 GB |
| 500M | ≈128 GB | ≈1.5 TB |
| 1B | ≈256 GB | ≈3 TB |

### Engine options at this scale
- **Vespa:** proven on 1B secondhand items at Vinted, hybrid in a single query, with real-time partial updates for price and status [V]. Best fit at 500M and above. The cost is operational complexity.
- **Elastic/OpenSearch kNN:** familiar. Vinted left it at 1B items because of node count and latency [V].
- **Milvus/Zilliz:** proven for 200M+ dedupe [V]. Lexical search is weaker, so pair it with Elastic/OpenSearch.
- **Qdrant / Weaviate:** good to about 100–500M with quantization [U]. Both have hybrid and sparse vectors.
- **Turbopuffer:** object-storage-backed, low cost.
  - Prices: storage up to $0.33/GB [V; the per-month unit is unclear on the page], writes up to $2/GB (50% off for batches of 3.2 MB or more; 10 KB minimum per write), queries billed per data scanned, Enterprise from $4,096/mo [V].
  - [calc] At 500M items × 5.6 KB (float32 vector plus attributes) = 2.8 TB:
    - Storage: about **$920/mo**
    - Initial load: 2.8 TB × $1/GB batched = **$2.8k**
    - Churn: 10M/day × 5.6 KB = 56 GB/day × $1 = **about $1.7k/mo**
    - Total: about **$3–6k/mo**, plus query charges.
  - The pricing table seemed to show namespaces of about 100K documents, so check namespace limits and plan to shard by category [U].
- **LanceDB:** good for offline and batch work (dedupe, evaluation, training sets) on S3. Less proven for low-latency serving at 1B [U].

Rough monthly serving cost, self-managed [U: cloud instance prices not verified]:

| Scale | Setup | Cost |
|---|---|---|
| 100M | 2 × (64–128 GB RAM, 1 TB NVMe) nodes with replication | ≈$1–2k/mo |
| 500M | Vespa or Qdrant on 3 shards × 2 replicas of 256 GB nodes | ≈$7–10k/mo |
| 1B | 6 shards × 2 replicas | ≈$15–20k/mo |

- Vinted's 60 content nodes are sized for 20k QPS. A startup at under 200 QPS needs a fraction of that [V/U].
- Thumbnail cache (optional): 1B × 30 KB = 30 TB × $0.023 per GB-month = **about $690/mo** [calc; S3 price from memory, U].

### Crawl cost model at 500M items (the dominant variable cost)

Assume about 180M items come from hostile peer-to-peer sites: Poshmark, Mercari, Depop, Grailed and OfferUp [U mix].

Requests per day [calc]:
- **Discovery:** 2% × 180M = 3.6M new items per day ÷ about 48 items per search page = **75k pages/day**. This assumes the search-result JSON includes title, price, brand, size and image URL; otherwise add 3.6M detail fetches.
- **Weekly sold sweep:** 180M ÷ 48 ÷ 7 = **536k pages/day**.
- **Query-time validation:** 50k queries/day × 10 results from hostile sources = **500k checks/day**.
- **Total:** about **1.1M requests/day**. If detail pages are needed, about 4.7M/day.

Daily cost by method, at 1.1M requests/day (and at 4.7M/day where it applies):

| Method | 1.1M/day | 4.7M/day |
|---|---|---|
| Zyte HTTP tier 4 at $0.34/1k | **$375/day ≈ $11k/mo** | $1.6k/day ≈ $48k/mo |
| Browser-rendered at $3.84/1k | **$127k/mo** | Not computed; prohibitive |
| Own crawler + residential proxies at $3/GB, ~30 KB JSON per response (33 GB/day) | ≈$100/day ≈ **$3k/mo** + ~$2k compute | — |

- **Friendly sources** cost about $0 in fetch fees: eBay and Etsy APIs, affiliate feeds, and Shopify (for example, 25M items ÷ 250 per page = 100k requests per daily sweep on datacenter IPs).
- **Conclusion:** coverage of the friendly 70% is cheap. Each hostile marketplace costs **$1–4k/mo plus legal risk**, so a partnership with any one of them pays for itself.

---

## 5. Recommended index strategy for us

### Guiding principles
- **Live, de-duplicated items** are the metric, not raw listings.
- Publish "live-verified within X hours" as a product feature. Phia publishes only counts.
- Use feeds and APIs first, crawl politely second, and partner for anything hostile.
- **Never** use logged-in scraping, fake accounts, CAPTCHA solving, or proxy evasion after a block. This follows from *3Taps*, *SerpApi* and *hiQ*.

### Phase 1: 0–3 months, about 10–30M live items ("prove search quality in two verticals")
Focus on fashion and home/vintage furniture.

Sources:
- **eBay:** join EPN, use the Browse API for query-time federation, and apply for the Feed API in fashion, home and collectibles. Start the Growth Check immediately.
- **Etsy:** v3 API, vintage only.
- **Shopify and indie stores:**
  - Seed list: Common Crawl or Store Leads filtered for vintage/consignment/resale keywords plus Shopify fingerprints, plus inbound submissions. Gem's model of letting stores email in to be included works.
  - Sweep `/products.json` daily.
  - Target 5–10k stores holding about 5–10M items.
- **Affiliate programs:** TRR, ThredUp (Sovrn), Vestiaire (CJ), Grailed (FlexOffers), 1stDibs (Ascend), Chairish. Ask each for a product feed; crawl the public catalog where no feed exists and the ToS allows.
- **Evaluate vendors:** Channel3 (1stDibs/Chairish coverage), plus Bright Data or Apify samples for Poshmark, Mercari and Depop to measure coverage. Do not depend on them yet.

Infrastructure:
- One self-hosted multimodal encoder.
- Qdrant or Turbopuffer, plus OpenSearch/BM25 (or Vespa from day one if the team can run it).
- Postgres for the listing ledger, an object store for raw snapshots, and a queue-based crawler (Scrapy-style HTTP first).

Freshness SLAs:

| Source | New items | Sold/delisted |
|---|---|---|
| eBay/Etsy/Shopify | Visible within 6 h | Detected within 12 h |
| Affiliate sources | Within 24 h | — |

Query-time validation applies to the top 10 results for every source without a feed.

### Phase 2: 3–9 months, about 50–150M live items ("coverage parity with Phia on the big five")
- **eBay Feed API across all used-condition categories.** This is the largest single cheap block, about 50–100M US pre-owned items [U].
- **Pursue partnerships:**
  - **Depop:** now inside eBay, so pitch it as an extension of the eBay relationship.
  - **Poshmark (Naver):** has a precedent of feed deals with Beni and Phia [V-secondary].
  - **Mercari US**, **Vinted US:** Vinted is new to the US and needs traffic.
  - Offer CPA traffic plus seller-side benefits. If you also run a seller-side crosslisting agent, the combination of listing supply and buyer traffic is a stronger pitch than traffic alone [U].
- **Polite crawl as a bridge** for any of these without a deal:
  - Search-JSON discovery and weekly category sweeps only. No detail pages unless needed.
  - Budget about $1–4k/mo per site (§4).
  - Hard stop on a cease-and-desist letter or a block.
- **Auctions:** LiveAuctioneers, Invaluable, HiBid and Catawiki through partnerships or affiliates. Schedule refreshes from known end times.
- **Brand resale programs:** Worn Wear, Treet-powered sites, Trove and ThredUp RaaS sites, through Shopify or direct feeds.

Freshness SLAs:

| Source | New items | Sold |
|---|---|---|
| Feeds | Within 2 h | Within 6 h |
| Crawled peer-to-peer sites | Within 24 h | Within 72 h in the background, **≤15 min at display** through lazy validation |

Target **dead-link rate in the top 10 results under 2%.**

### Phase 3: 9–18 months, 200–500M+ live items ("best freshness in market")
- **Local pickup inventory:** OfferUp, plus Facebook Marketplace only through an official program or a user-side, extension-mediated fetch. The Perplexity 9th Circuit reasoning is more favorable to user-agent access [V-secondary], but get counsel first. **Do not crawl Craigslist** at all.
- **Long tail at full scale:** 30–60k stores across Shopify, Squarespace, Wix, WooCommerce and BigCommerce via sitemap plus JSON-LD. Use Common Crawl monthly to discover new domains.
- **International**, if the market widens: Vinted EU (1B items), Vestiaire, Catawiki, and Kaidee-style regional sites through partnerships. EU database rights make crawling riskier.
- **Prioritized refresh scheduler.** Refresh rate per item is a function of:
  - P(sold): from category, price relative to comparables, age and seller velocity.
  - Item popularity: impressions and clicks.
  - Source cost.

  Popular, underpriced items get refreshed hourly. Long-tail antiques get refreshed weekly.
- **Engine:** move to Vespa (or Vespa Cloud) for 500M–1B items with real-time partial updates (Vinted pattern) [V].

### What to crawl versus license versus partner (summary)

| Approach | Sources |
|---|---|
| **License / API** | eBay (Browse plus Feed), Etsy, affiliate feeds (TRR, ThredUp, Vestiaire, 1stDibs, Chairish, Grailed), Channel3 for gaps |
| **Crawl (low risk)** | Shopify and indie sites (`/products.json`, sitemaps, JSON-LD); consignment-store sites; auction catalogs that allow it |
| **Partner (crawl only as a bridge)** | Poshmark, Mercari, Depop (via eBay), Vinted US, OfferUp, LiveAuctioneers, Invaluable |
| **Avoid** | Craigslist; logged-in Facebook Marketplace; anything requiring anti-bot circumvention; scraping Google Shopping |

### Deduplication and entity-resolution design

**Level 0: listing ledger.** One record per (source, source_listing_id). It holds raw snapshots, first-seen and last-seen timestamps, a status history, and a price history (useful for comparables).

**Level 1: physical-item clusters (cross-listing dedupe).** The same seller posts the same jacket on Poshmark, Mercari, eBay and Depop, usually with identical photos, especially when using crosslisting tools such as Vendoo and List Perfectly.

- **Signals:**
  - pHash/dHash of every image (64-bit, Hamming distance ≤ 8).
  - Embedding cosine above 0.95 within the same block.
  - Normalized title Jaccard similarity.
  - Brand, size and condition equality.
  - Price within ±15%.
  - Seller-handle similarity across platforms.
  - Listing-time proximity.
- **Candidate generation:**
  - Multi-index hashing (LSH) on pHashes.
  - ANN top-20 within the block (brand × category).
  - Cost at 500M items × 3 images × 8 B = **12 GB of hashes** [calc]. This is trivial.
- **Classifier:**
  - A gradient-boosted pairwise model trained on labeled pairs, with an LLM adjudicating the uncertain band.
  - A multimodal decider of the arXiv 2509.15858 kind is the upgrade path, with F1 around 0.90 [V].
- **Clustering:**
  - Union-find with a guard against transitive "chaining" (cap cluster diameter).
  - Each cluster shows as **one item with multiple offers**.
  - The item stays live if any offer is live. When one offer sells, check its siblings sooner, since one sold copy implies the others are stale.
- **Stock-photo trap:**
  - An image hash that appears across more than N distinct sellers is flagged as a stock/catalog image and does not count as identity evidence.
  - Require at least one non-stock image match, or a strong combination of text and seller signals.

**Level 2: canonical products (model/SKU entity resolution).** For example, "Arc'teryx Beta LT, men's, 2022, black".

- **Uses:** price comparables, "new versus used" comparisons, "find this exact thing", and alerts.
- **Seed the catalog** from new-retail affiliate feeds and brand catalogs.
- **Keys:** GTIN/MPN or style codes where present (luxury style numbers, Nike style codes on tags), extracted by an LLM or vision model from titles and tag photos.
- **Process:** block on brand × category, match by embedding, adjudicate with an LLM above a threshold, and keep human review for high-value categories (luxury bags, watches).
- **Store** item→product links with confidence scores. Search can then collapse or expand by product.

**Attribute normalization.** Size systems, condition scales, colors and materials into one taxonomy. Beni needed a dedicated model for sizing chaos [V]. Use an LLM at ingest, cache the output by source and template, and re-run only on change.

### Search stack
- Hybrid retrieval: BM25 over normalized fields, plus a multimodal vector (text→image and image→image), plus hard filters (size, price, location/shipping, live status).
- Fuse with RRF, then a cross-encoder or LLM reranker on the top 200.
- Photo queries: embed with the same encoder, optionally detect and crop the garment first.
- Text queries: LLM query parsing into filters plus free text.
- Freshness boost, and a "verified live N min ago" badge from lazy validation.

### Budget snapshot at 500M items, steady state [calc/U]

| Line item | Monthly cost |
|---|---|
| Embeddings, self-hosted | ≈$0.5k |
| Vector and lexical serving | ≈$7–10k (or Turbopuffer ≈$3–6k plus a lexical engine) |
| Crawl (hostile sites, polite, own infra) | ≈$5–15k |
| Feeds and APIs | ≈$0 (revenue-share) |
| Storage and snapshots | ≈$1–2k |
| LLM attribute extraction for 10M new items/day | ≈$4.5k/day ≈ **$135k/mo** at $0.00045 per item [U, small-model pricing guess] |
| **Total** | **≈$15–30k/mo** before LLM enrichment |

The LLM line is the real cost driver, so:
- Use a small distilled extractor (self-hosted) to bring it to about $1–3k/mo [U].
- Apply LLMs only to items without structured attributes.

*Uncertainty: the volume, partnership and feed-availability claims marked [U] or [V-secondary] should be confirmed directly with each platform's partner or affiliate team before being used in planning.*
