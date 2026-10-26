# Find it: secondhand and retail source map (as of 2026-10-26)

Tags: **[V]** verified from the primary or official source this session · **[S]** secondary source (aggregator, press, vendor comparison) · **[U]** unverified, from memory or inference. Several official pages (developers.etsy.com, etsy.com/legal/api) could not be fetched this session, so their facts are tagged [S] or [U].

## Summary: recommended stack

**v0 on-demand lookup (build now, low volume, user-initiated):**
1. **Shopify Global Catalog (Catalog API / MCP).** Since Spring '26 (June 2026) it needs only an API key, with no approval. It covers "millions of Shopify merchants" and supports text search, **image search**, multimodal search, and URL-to-product lookup. It fits both "new at retail" (DTC brands) and Shopify-based vintage shops. Two rules: no caching of results, and images may only be shown live and tied to the listing. [V] ([Shopify Spring '26](https://www.shopify.com/news/spring-26-edition-dev), [Catalog usage guidelines](https://shopify.dev/docs/agents/catalog))
2. **eBay Browse API** (`search`, `search_by_image` [experimental], `getItem`) at the default 5,000 calls/day [V]. Two constraints matter for the UI. First, eBay content in a public display "may not be co-mingled or combined with non-eBay Content". Second, listing data may be at most 6 hours stale. Both mean the eBay results need their own visually separate module. [V] ([API License Agreement, updated 2025-09-03](https://www.edp.ebay.com/join/api-license-agreement)). Depop is now eBay-owned, but Depop has no buyer-side search API.
3. **Brave Search API** as the main `site:`-query engine for platforms without APIs (Poshmark, Mercari, Grailed, Chairish, 1stDibs, TRR, Vestiaire and others). It costs $5 per 1,000 requests and has its own independent index plus image search. Its terms allow transient storage only. [S]
4. **Exa** as a second, semantic engine, useful for "find similar" queries and domain-restricted queries. It costs $4–7 per 1,000. [V]
5. **Google Cloud Vision Web Detection** for reverse-image search. It returns `pagesWithMatchingImages`, `fullMatchingImages`, `visuallySimilarImages` and `bestGuessLabels`, at $3.50 per 1,000 after the first 1,000 free each month. Filter its results down to marketplace domains. [V]
6. **Fetch and parse each candidate listing page** when the user asks (OpenGraph `product:price:*` meta plus JSON-LD when present) to confirm price and availability, then link out through affiliate links.

**Apply for now:**
- eBay Partner Network, followed by Buy API production access (EPN replies within about 10 business days, then eBay Developer Support issues a contract) [V]. Ask for Feed API access at the same time; it is the only realistic way to build a pre-built eBay index.
- Affiliate networks:
  - **Awin**: Etsy, GOAT, ThredUp
  - **Rakuten**: Fashionphile, Vestiaire US, ThredUp, Rebag
  - **Impact**: StockX, The RealReal (applications "limited"), Grailed
  - **CJ**: Poshmark
  - **Sovrn Commerce or Skimlinks** as a catch-all that monetizes the long tail without separate approvals
- StockX Developer Program (Catalog API with market data).
- Etsy Open API v3 commercial access (needed for Etsy-wide listing search).

**Avoid:**
- **Google Custom Search JSON API.** Closed to new customers and shutting down on **2027-01-01** [S].
- **Bing Search APIs.** Retired 2025-08-11, Visual Search included [V].
- Building on SerpApi or Serper as core infrastructure. Google's DMCA suit against SerpApi was mostly dismissed on 2026-07-20, but scraping Google still breaches Google's ToS and the Reddit suit is ongoing [S]. Use them only as an optional, swappable Google Lens and Shopping adapter.
- Facebook Marketplace scraping (login wall; Meta litigates).
- Craigslist scraping (ToS bans it; it has won large judgments).
- Crawling Poshmark, eBay or Etsy to build a pre-built index (their ToS prohibit it; eBay explicitly bans "LLM-driven bots" from 2026-02-20 [S]).

## Per-platform table

Column key:
- **(a) API**: official API or data feed, and whether a new small company can get access
- **(b) Affiliate**: affiliate program, network, and whether it provides a product feed
- **(c) Indexed / markup**: whether listing pages are indexed by search engines and carry Product/Offer structured data
- **(d) ToS / legal**: stance on automated access, plus notable lawsuits
- **(e) Route**: recommended access route for on-demand lookup vs. a pre-built index

"Spot check" in column (c) means `site:` queries run this session through the built-in search tool; this is a weak signal. JSON-LD could not be observed because the fetch tool strips `<script>` tags, so every JSON-LD claim is [U].

| Platform | (a) API | (b) Affiliate | (c) Indexed / markup | (d) ToS / legal | (e) Route |
|---|---|---|---|---|---|
| **eBay** | Browse API (search, `search_by_image` "(Experimental)", getItem) at 5k/day [V]. Production Buy API access requires an EPN application, an MNDA or contract, and "no guarantee" of approval [V] ([buy-requirements](https://developer.ebay.com/api-docs/buy/static/buy-requirements.html), [call limits](https://developer.ebay.com/develop/get-started/api-call-limits)). Feed v1 allows 75k/day once licensed [V]. Marketplace Insights (sold items) is "Limited Release" [V], and developers in 2025–26 report denials outside major partners [S] ([thread](https://community.ebay.com/t5/eBay-APIs-Talk-to-your-fellow/Marketplace-Insights-API-access/m-p/34838736)). | eBay Partner Network (its own network) [V]. | Heavily indexed [V spot check]. | User Agreement bans robots, scrapers and "LLM-driven bots" without permission, effective 2026-02-20 [S] ([VAR](https://www.valueaddedresource.net/ebay-bans-ai-agents-updates-arbitration-user-agreement-feb-2026/)). API terms add: no co-mingling, 6-hour freshness, no price modeling (§9.5), no AI training (§9.10) [V]. | On-demand: Browse API. Index: Feed API, after approval. |
| **Depop** (eBay-owned; deal completed July 2026 at about $1.2B headline [S] ([Dealroom](https://dealroom.co/news/126026-ebay-completes-1-4b-acquisition-of-depop-from-etsy/))) | Selling API only: partner-only, by invite (developers@depop.com), covers seller listings and orders, no search endpoint [S] ([apis.io](https://apis.io/providers/depop/)). | Has an affiliate team [S]; network unconfirmed [U]. | Indexed well [V spot check]. Pages expose og:title and og:image; price was not in meta [V]. | Assume scraping is prohibited [U]. | On-demand: `site:depop.com/products` through the search API, then fetch the page. Watch whether eBay folds Depop into Browse [U]. |
| **Etsy** | Open API v3 includes public listing search. Commercial apps reportedly start at 10 QPS and 10k requests/day; higher limits are requested by email [S] ([apis.io](https://apis.io/rate-limits/etsy/etsy-rate-limits/)). Current terms page not fetched. The archived 2020 terms required listing data to be at most 6 hours stale, banned scraping, and banned using the API "primarily to drive traffic to other non-Etsy websites" [S] ([archived](https://www.etsy.com/legal/api-archived/)). | Awin, 30-day cookie [V] ([Etsy help](https://help.etsy.com/hc/en-gb/articles/360000335987-The-Affiliate-Programme)). No datafeed is mentioned [V]. | Indexed, with Product JSON-LD [U]. | Scraping banned [S]. | On-demand: Open API, then deep-link through Awin. Index: API sync within the 6-hour rule [S]. |
| **Poshmark** | No public API [U]. | CJ, 1.25% (page dated 2024) [S] ([LinkClicky](https://linkclicky.com/affiliate-program/poshmark/)). | Indexed (spot check returned a listing) [V]. Pages carry `product:price:amount`, `product:price:currency`, `product:availability` (e.g. "oos") and `og:image` meta [V]. | ToS §4(b) bans "copy, scrape, harvest, crawl… automated systems" (v4.6, June 2025) [V] ([terms](https://poshmark.com/terms)). | On-demand: search API with `site:poshmark.com/listing`, plus one page fetch per result to read the meta. Index: no. |
| **Mercari US** | No public API [U]. | No US program found; affi.io lists only Sovrn and non-US programs [S] ([affi.io](https://affi.io/m/mercari)). | Spot check returned no item pages [V], so indexing may be weak [U]. | Assume scraping is banned [U]. | On-demand: search API with `site:mercari.com/us/item`; coverage is uncertain. |
| **Grailed** | No public API [U]. | Impact, Sovrn, FlexOffers and others [S] ([affi.io](https://affi.io/m/grailed)). | Spot check returned no listings [V], so indexing is uncertain [U]. | [U] | On-demand: search API; monetize through Impact. |
| **Vinted (US)** | No public API [U]. | [U] | [U] | [U] | Vinted relaunched in the US, starting with NYC, in January 2026 [V] ([FashionUnited](https://fashionunited.com/news/business/vinted-announces-major-us-expansion-to-address-growing-demand/2026012270176)). US inventory is still small, so this is low priority. |
| **ThredUp** | No public API [U]. | Awin and Rakuten open; Impact and ShareASale closed. LinkConnector lists a product feed [S] ([affi.io](https://affi.io/m/thredup)). | [U] | [U] | Affiliate feed (if it can be obtained) for the index; search API on-demand. |
| **The RealReal** | No public API [U]. | Impact ("applications currently limited") and FlexOffers [S] ([affi.io](https://affi.io/m/the-realreal)). | [U] | [U] | Search API, plus an Impact catalog if one is granted. |
| **Vestiaire Collective** | No public API [U]. | Rakuten (US) open [S] ([affi.io](https://affi.io/m/vestiaire-collective-us)). | [U] | [U] | Search API, plus a Rakuten product feed (ask the advertiser). |
| **Rebag / Fashionphile** | No public API [U]. | Rebag: Rakuten or Impact, 5–10%. Fashionphile: Rakuten, about 5% [S] ([ucompares](https://ucompares.com/affiliate/programs/handbag/)). | [U] | [U] | Rakuten feeds for the index; search API on-demand. |
| **StockX** | StockX Public API v2 includes a Catalog API with search and live bids/asks, for "approved developers in the StockX Developer Program" [S] ([apievangelist](https://providers.apievangelist.com/providers/stockx/)). It is mostly seller-oriented [U]. | Impact, 15-day window [S] ([makeinfluence](https://www.makeinfluence.com/en/academy/stockx-and-goat-sneaker-resale-marketplace-affiliate-programs-compared)). | Indexed [V spot check: a StockX page appeared]. | [U] | Apply to the Developer Program; meanwhile use the search API. |
| **GOAT** | No public API [U]. | Awin ("GOAT USA"), 30 days [S]. | [U] | [U] | Awin feed or search API. |
| **1stDibs** | No public API [U]. | In-house program for creators, application form pointing to ascendpartner.com (Partnerize) [V] ([1stDibs](https://www.1stdibs.com/answers/does-1stdibs-have-an-affiliate-program)). | [U] | [U] | Search API on-demand. |
| **Chairish** | No public API [U]. | Partnerize and ShareASale closed; Sovrn, Sale Gains and BlueAff listed [S] ([affi.io](https://affi.io/m/chairish)). | Strongly indexed: 10 of 10 spot-check results were product pages [V]. | [U] | `site:chairish.com/product` through the search API. |
| **Kaiyo** | No public API [U]. | Not found [U]. | [U] | [U] | Search API. |
| **AptDeco** | No public API [U]. | ShareASale program (listing and purchase commissions) [V] ([Awin profile](https://ui.awin.com/merchant-profile-terms/93197)); another aggregator says it is inactive [S]. | [U] | [U] | Search API. |
| **Facebook Marketplace** | No API for third parties [U]. | None. | Not indexed (spot check returned 0) [V]. Listings are mostly behind a login. | Meta ToS bans automated collection. In *Meta v. Bright Data* (January 2024) the court held that logged-out scraping of public data did not breach Meta's terms, but Meta remains litigious [S] ([Zyte](https://www.zyte.com/blog/california-court-meta-ruling)). | Exclude. At most, a "search Marketplace" deep link the user opens themselves. |
| **Craigslist** | No API [U]. | None. | Partially indexed [U]. | ToS bans robots and scrapers. Craigslist won against RadPad (2017) and settled with 3Taps [S] ([Apify](https://blog.apify.com/craigslist-v-radpad/)). | Exclude, or a user-opened deep link only. |
| **OfferUp** | No API; only third-party scrapers exist [S]. | [U] | [U] | Assume banned [U]. | Exclude in v0, or search API only. |
| **Shopify vintage stores** | Global Catalog: approval-free, image search, no caching [V]. `/products.json` is a widely used unauthenticated public endpoint [S] ([dev.to](https://dev.to/shan_yun_ab0c7ad30b46ad2d/shopifys-open-secret-every-store-exposes-productsjson-30ni)), but it is undocumented and rate-limited [U]. | Per store, or via Sovrn/Skimlinks; Catalog "promoted placements" commission is planned [V]. | Shopify themes emit Product JSON-LD by default [U]. | Catalog terms forbid caching [V]. | On-demand: Catalog API. Index of curated vintage stores: `/products.json` polling, at low rate and only with permission from the stores [U]. |
| **LiveAuctioneers / Invaluable** | No public API found [U]. | [U] | Lots are indexed [U]. | [U] | Search API (`site:liveauctioneers.com/item`). Auction listings are time-bound. |
| **Long tail** (Ruby Lane, Etsy-like sites, consignment shops) | None. | Sovrn Commerce / Skimlinks auto-affiliate [U]. | Varies. | Varies. | Open-web search plus Cloud Vision Web Detection. |

**New at retail:**
- **Google Shopping has no third-party offer-search API.** The Content API for Shopping was sunset on 2026-08-18 (410 errors from 2026-09-01), and its replacement, the Merchant API, is for managing merchant accounts [V] ([Google](https://developers.google.com/shopping-content/guides/sunset)). Google's new Web Search Service API is partner-only [S] ([SEJ](https://www.searchenginejournal.com/google-documents-partner-only-api-for-full-web-search-results/)). UCP (Google and Shopify) is an agent-commerce protocol, used through the Shopify Catalog [S].
- **Affiliate catalogs** are the legitimate bulk source. Examples: CJ Product Search (REST; returns image-url, price, retail-price, UPC, buy-url) [S] ([Nagel](https://ericnagel.com/resources/cj-product-datafeed.html/amp)), and Impact Catalogs API [S]. Rakuten and Awin feeds are granted per advertiser after approval [U].
- **Brand sites**: through the Shopify Catalog when the brand runs on Shopify, otherwise through the search API plus a page fetch.

## Web search APIs (for `site:` queries)

| API | Status (2026) | `site:` / domain filter | Images | Price | Commercial use / storing results | Latency |
|---|---|---|---|---|---|---|
| **Brave Search** | Active; free tier dropped Feb 2026; $5/month credit kept if you attribute Brave [S] ([implicator](https://www.implicator.ai/brave-drops-free-search-api-tier-puts-all-developers-on-metered-billing.md)) | `site:` in the query string; Goggles for re-ranking [U] | Yes, image endpoint on the same plan [S] | $5/1k; 50 rps [S] ([Brave](https://brave.com/learn/google-api-shutdown/)) | AI inference rights included; **transient storage only**; no training [S] ([Parallel](https://parallel.ai/ai/articles/brave-search-api-vs-parallel)) | ~0.6 s measured mean (LLM Context) [S] |
| **Exa** | Active | `includeDomains` [U] | Result image fields [U] | $4/1k (instant/lite), $7 (auto/fast), $12–15 (deep); $10/month free [V] ([pricing](https://exa.ai/docs/reference/pricing)) | Zero data retention on Enterprise [V]; standard terms not checked | Deep 4–40 s [V]; standard sub-second [U] |
| **Tavily** | Acquired by Nebius (announced 2026-02-10, reportedly $275M+) [S] ([usagepricing](https://usagepricing.com/blueprint/activity/2026-02-10-tavily-nebius-acquisition)) | `include_domains` [U] | `include_images` [U] | 1 credit basic, 2 advanced, $0.008/credit, 1k free/month [V] ([docs](https://docs.tavily.com/guides/api-credits)) | [U] | [U] |
| **Google Custom Search JSON API** | **Closed to new customers; discontinued 2027-01-01**. Programmable Search Element limited to 50 domains or fewer [S] ([Brave](https://brave.com/learn/google-api-shutdown/), [SEJ](https://www.searchenginejournal.com/google-documents-partner-only-api-for-full-web-search-results/)) | n/a | n/a | n/a | n/a | n/a |
| **Bing Web / Visual Search** | **Retired 2025-08-11**; the replacement, "Grounding with Bing," only works inside Azure AI Agents [V] ([Microsoft](https://learn.microsoft.com/en-us/lifecycle/announcements/bing-search-api-retirement)) | n/a | n/a | n/a | n/a | n/a |
| **SerpApi** | Active. Google sued on 2025-12-19 (DMCA §1201); most claims dismissed 2026-07-20, with leave to amend only on Knowledge Panel images. Reddit v. SerpApi (SDNY) still pending [S] ([PPC Land](https://ppc.land/google-loses-dmca-bid-to-treat-search-scraping-like-dvd-piracy/)) | Full Google syntax | Google Images and **Google Lens** (visual_matches with price, exact_matches). `type=product` broken as of 2026-10-09 [V] ([release notes](https://serpapi.com/google-lens-api/release-notes)) | ~$10/1k, $50/month minimum [S] ([cloro](https://cloro.dev/blog/cheapest-serp-api/)) | Scrapes Google against Google's ToS; reliability incidents logged [V] | Several seconds [U] |
| **Serper** | Active; same legal category as SerpApi (not sued) [U] | Full Google syntax | Images, Lens, Shopping [U] | ~$1–3/1k [S] | Same as SerpApi | ~1–2 s [U] |
| **You.com** | Active | [U] | [U] | $5/1k, 100 free calls/day [S] ([usagepricing](https://usagepricing.com/blueprint/activity/you-com-2026-06-01-price-change)) | [U] | [U] |
| **Perplexity Search API** | Active since September 2025 | Domain filter [U] | [U] | $5/1k; $1/1k "fast" [V] ([docs](https://docs.perplexity.ai/guides/pricing?country=20)) | [U] | [U] |

**Reverse-image search options:**

| Option | Status and what it returns | Price | Fit |
|---|---|---|---|
| **Cloud Vision Web Detection** | Available. Returns webEntities, full and partial matching images, `pagesWithMatchingImages` (url, pageTitle), visuallySimilarImages and bestGuessLabels. No deprecation notice [V] ([docs](https://docs.cloud.google.com/vision/docs/detecting-web?hl=de)). | $3.50/1k after 1k free/month [V] ([pricing](https://cloud.google.com/vision/pricing?hl=uk)) | The only official Google route to "pages containing this image". Good for finding a known stock photo; weak for a user's own snapshot of a used item. |
| **Google Lens** | No official API; only reachable through SerpApi or Serper scraping [S]. | See SerpApi / Serper above | Best for retail product matching. |
| **Bing Visual Search** | Retired with the other Bing APIs [V]. | n/a | n/a |
| **TinEye** | Exact or near-duplicate matching only. | Bundle pricing from 2015: $200 for 5k searches down to $0.01/search at volume [S] ([TinEye](https://blog.tineye.com/new-image-search-pricing/)) | Poor for "similar". |
| **Marketplace-native image search** | eBay `search_by_image` [V] and the Shopify Catalog image search [V]. | Included in API access | The highest-precision routes for v0. |

## Key risks

- eBay's no co-mingling rule (§8.1(b)(2)) affects the core blended-results UI. Get legal review, or show eBay in a separate visual module.
- Most platforms forbid caching (Shopify, eBay, Brave). A pre-built index therefore has to come from licensed feeds (eBay Feed API, affiliate catalogs), not from stored search results.
- Coverage of Mercari, Grailed and Facebook Marketplace through search engines looked poor in spot checks. Re-test with Brave and Exa directly before promising "all of the secondhand internet".
