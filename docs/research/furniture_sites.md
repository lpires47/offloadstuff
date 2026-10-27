# Secondhand furniture / decor / design marketplaces: connector specs

Research date: 2026-10-26. Method: WebSearch + WebFetch only (no shell internet).

**Tags:** **[V]** = verified this session from a primary source (the site's own page, official docs, or the site's live page fetched now). **[S]** = secondary source (Apify actor README, vendor page, press) or strong inference from fetched evidence. **[U]** = unverified (from memory or a guess). Confirm in browser devtools before building.

**Important caveat on robots.txt:** direct fetches of every `https://www.<site>/robots.txt` were blocked in this session (WebFetch "PROVENANCE_REQUIRED"/permission not granted): Chairish, 1stDibs, Kaiyo, AptDeco, LiveAuctioneers, Invaluable. None of the robots.txt rules below are verified. **Pull each robots.txt manually before launch.** Page-level `meta robots` was observed where noted.

**Live-fetch probe (WebFetch's fetcher acts like a plain server-side client):**
- Fetched OK: chairish.com collection/product pages, 1stdibs.com browse/user-agreement, pamono.com, invaluable.com lot pages + terms, liveauctioneers.com catalog/terms, ebth.com home/terms, offerup.com/terms, store.hermanmiller.com.
- `client_error` (likely 403 bot wall): **kaiyo.com** (every URL), **aptdeco.com/terms**, `/services` (but `/catalog/sofas` loaded), support.chairish.com (Zendesk).
- Empty body with `noindex,nofollow`: **rubylane.com** (search, item and terms pages). This looks like a JS challenge interstitial.

---

## 1. Summary table

| Site | Best access path | Logged-out server fetch | Bot protection | Sold / price history | Affiliate / feed | ToS on automation | Priority |
|---|---|---|---|---|---|---|---|
| **1stDibs** | **Official public MCP server** `https://www.1stdibs.com/soa/mcp/` (`search_items`, `browse_items`, `item_details`, `read_taxonomy`) [S] | Yes for HTML; actors use datacenter IPs OK [S] | "WAF" per one actor; others say datacenter works [S] | Sold items flagged `isSold` in data; "recent sales" price range on PDP [S] | Yes: Pepperjam/Ascend (apply link ascendpartner.com) [V], also listed on Rakuten/CJ/Sovrn [S] | No explicit robot clause. "Any commercial use of the Site is strictly prohibited… except as… approved by us" [V] | **High**: use MCP |
| **Chairish** | HTML search/collection pages + embedded `PRODUCT_ID_TO_PRODUCT_JSON_MAP` (48/page), PDP JSON-LD/OG meta [S] | Yes (fetched OK) [V] | Light; actors use residential "to avoid rate limiting" [S] | `availability` in/sold on PDP; no public sold-comps search [S] | Unknown [U]; check Sovrn/Skimlinks/Impact | ToS page unreachable this session [U] | **High** |
| **Kaiyo** | HTML `/furniture/?q=…&min_price=&max_price=&page=` [V URL shape] | **Blocked** for plain fetcher (client_error on all URLs) [V] | Likely Cloudflare or similar, strict [S] | Not public [U] | Unknown [U] | Unreachable [U] | Medium (needs a browser-grade fetch or partnership) |
| **AptDeco** | Next.js `/catalog/<category>?sort=price-asc` → parse `__NEXT_DATA__` [S] | Catalog page OK, other pages client_error [V] | Partial WAF [S] | No [U] | **Yes: Awin (ex-ShareASale), merchant 93197** [V]. Pays on purchase + on listings | Unreachable [U] | **High** (affiliate + local NYC/DC/etc.) |
| **LiveAuctioneers** | Embedded app state on server-rendered pages; internal search API (host not confirmed) [S] | Yes with care. Imperva/Incapsula [S] | **Imperva**: medium-strict [S] | Past lots show "SOLD / See Winning Bid". Aggregate "Median Hammer Price" is **locked ("Unlock")** logged out [V] | No program found [U] | **Explicit ban**: "will not use any robot, spider, scraper, or other automated means to access the sites" (8.3, rev. 2025-03-26) [V] | Medium (pricing value high, ToS risk high) |
| **Invaluable** | Algolia-backed search (app id/key not captured) [S] | Search API unproxied OK. Detail pages throttle (HTTP 202 empty after ~4 req) [S] | Cloudflare on HTML [S] | Upcoming plus archive with `priceResult`; **site shows "Sold: Log in to view"** logged out [V] | None found [U] | **Explicit ban**: "will not use any robot, spider… to monitor or copy" (5.2); "any form of data extraction or data-mining" (4.2) [V] | Medium-low (login-gated prices, strict ToS) |
| **Etsy** | **Official Open API v3** `GET https://api.etsy.com/v3/application/listings/active` [V] | Yes (API key) | n/a (API); site itself is DataDome-protected [U] | No sold data in public API [S] | **Awin** (Etsy affiliate) [S] | API terms: app approval, ≤6h ad freshness, trademark notice, no diverting sales; scraping banned [V] | **High** |
| **Pamono** | HTML category pages `?p=N` (1,488 pages furniture) [V]; JSON-LD likely [U] | Yes (fetched OK) [V] | Not observed [V] | No [U] | FlexOffers listing (4%, 60-day) **currently not offered** [V]; check Awin [U] | No automation clause in terms [V] | Medium (EU-heavy, ships US) |
| **Ruby Lane** | HTML `/search?q=`, `/furniture-lighting?cat=Furniture&f_itemtype=Vintage&pricerange=500,999&ipp=180` [V URL shape] | **Challenge/empty page** to plain fetcher [V] | JS challenge (vendor unknown) [S] | No [U] | Unknown [U] | Terms page served as challenge [U] | Low-medium |
| **Selency** | n/a | n/a | n/a | n/a | n/a | n/a | **Skip**: France/EU only, no US market [U] |
| **Herman Miller Refurbished** | SFCC grid `/on/demandware.store/Sites-herman-miller-Site/en_US/Search-UpdateGrid?cgid=herman-miller-refurbished&srule=…&start=0&sz=48` [V] | Yes [V] | Not observed [V] | n/a (new-retail-like) | HM affiliate network [U] | [U] | Low (2 SKUs: Aeron only, launched 2026-06-22) |
| **DWR / Knoll outlet** | SFCC sale/outlet categories [U] | [U] | [U] | n/a | [U] | [U] | Low |
| **EBTH** | HTML `/browse`, `/items/{id}-{slug}`, `/sales/{id}` [V] | Yes (fetched OK) [V] | Not observed [V] | Current bid only; closed prices not seen [S] | None found | **Explicit ban** on "robot, spider, scraper, data mining tools" and even "any manual process to monitor or copy" (rev. 2026-06-29) [V] | Medium (good estate inventory, ToS strict) |
| **OfferUp** | HTML `/search?q=` (search pages unchallenged); internal GraphQL [S] | Search OK from US IPs; **detail pages challenged** [S]; US-only geo [S] | Bot challenge on item pages [S] | No | No public program found | **Explicit ban** on bots/scrapers and "third-party applications that interact with the OfferUp Services without… consent" (rev. 2026-07-21) [V] | Low (ToS explicitly bans third-party apps) |
| **eBay** (missing from list) | **Official Browse API** `GET https://api.ebay.com/buy/browse/v1/item_summary/search` [V endpoint family] | Yes (OAuth app token) | n/a | Browse API: active only; sold needs Marketplace Insights (restricted) [S] | **eBay Partner Network** [S] | Production Buy API access needs approval + contract [V] | **High** |
| **Craigslist** | *Note only.* ToS bans robots/scrapers; history of litigation (3Taps) [U] | — | — | — | — | — | Don't use |
| **Nextdoor For Sale** | *Note only.* Login-walled, no public search [U] | No | — | — | — | — | Don't use |
| **Facebook Marketplace** | *Note only.* Covered by another agent | — | — | — | — | — | — |
| **Bidsquare** (add) | Server-rendered search HTML + lot JSON-LD [S] | Cloudflare [S] | Cloudflare | Sold price public for some houses, otherwise `priceGated` [S] | — | [U] | Optional (auction comps) |
| **MaxSold** (add) | "Public JSON API", unprotected per actor [S] | Yes [S] | None reported [S] | No sold field [S] | — | [U] | Optional (local estate pickup) |
| **Catawiki / Lauritz** | EU-centric; Catawiki ships to US [U] | [U] | [U] | Catawiki shows closed prices [U] | Catawiki on Awin [U] | [U] | Low |

**Recommended build order:** (1) eBay Browse API, (2) Etsy API v3, (3) 1stDibs MCP, (4) Chairish HTML, (5) AptDeco (`__NEXT_DATA__` + Awin), (6) Pamono. Pricing comps: LiveAuctioneers and Invaluable both gate realized prices behind a (free) login and ban automation in their ToS. Under the "no logins" rule they are **not** clean sources for sold prices. Consider licensed data (Invaluable/LiveAuctioneers data partnerships, or the 1stDibs "recent sales" field via MCP).

---

## 2. Per-site request specs

### 2.1 1stDibs

**Best path: official MCP server** [S: skillselion.com listing, mcpplaygroundonline.com; marked "Official", v1.0.0]
- Endpoint: `https://www.1stdibs.com/soa/mcp/` (streamable HTTP). Listing says "No Authorization header in the published server schema". One aggregator (mcpbundles) says sign-in "may" be asked. **Test it.**
- Tools:
  - `search_items(query: string, page?: number, filters?: string /* query-string format */)`
  - `browse_items(category: string, page?: number, filters?: string)`
  - `item_details(itemId: string)`
  - `read_taxonomy(category: string)`: returns next-level categories **and facets**, so use it to discover valid filter keys.
- Setup: `claude mcp add --transport http 1stdibs https://www.1stdibs.com/soa/mcp/`
- Output fields not documented. Expect title, price, creator, period, dimensions, materials, dealer location, URL (same as GraphQL). [U]
- This is the cleanest sanctioned access of any site here. Using a first-party agent endpoint arguably satisfies "approved by us" in the ToS.

**Website path (fallback)** [S: Apify actors scrapesage, lulzasaur, solidcode, saswave]
- Search: `GET https://www.1stdibs.com/search/?q=<kw>&page=N`. 60 items/page; each search caps at ~2,850 results.
- Browse: `https://www.1stdibs.com/furniture/seating/lounge-chairs/` plus path facets `/style/modern/`, `/material/upholstery/`, `/creators/<slug>/`. Query facets seen in indexed URLs: `?color=red`, `?page=3`, `?per=18th-century-and-earlier,mid-20th-century` (period). [V URL shapes from search index]
- Filter UI groups on the live page: Price, Location, Item type, Dimensions, Style, Period, Material, Color, **Availability**, Shipping Options, Creator. Page-size options 60/120. [V]
- Product URL: `/<dept>/<cat>/<type>/<slug>/id-f_<digits>/`. Images on `a.1stdibscdn.com`. [S]
- Data: actors say they read "1stDibs' internal GraphQL data" or the "embedded data store" (Relay SSR; the 1stDibs engineering blog has "Rendering Relay on the server", 2018). Prices did **not** appear in the static HTML fetched here. They are likely client-hydrated per currency or geo. [S]
- Fields available (actor outputs): `title, price, currency, convertedAmounts, priceVisibility (visible|upon_request), creator, period/productionDate, style, origin, materials, dimensions H/W/D, condition, availability, isSold, isAvailable, dealer name/city/state/country, images, url, itemId, priceRangeFromRecentSales, priceRecommendation`. [S]
- Sold: `isSold` is exposed, and an `availableOnly` filter exists in one actor. The `/buy/sold-items-furniture/` SEO pages exist but did not show sold prices. PDP "recent sales price range" is a useful comp field. [S]
- Bot: one actor says "behind a web application firewall" (residential default). Another says datacenter "works well". The plain fetch here succeeded. [S/V]
- ToS (User Agreement, modified 2025-02-26) [V]: "You may not download or save a copy of any of the Content… for any purpose"; "Any commercial use of the Site is strictly prohibited, except as allowed herein or otherwise approved by us." No explicit robots clause.
- Affiliate: yes. 1stDibs answers page links to ascendpartner.com (Pepperjam/Ascend) [V]. Affsignal also lists Rakuten, CJ, Sovrn, Linkbux and others [S].

### 2.2 Chairish

[S: Apify `lulzasaur/chairish-scraper`, `crawlergang/chairish-scraper`. V: live page fetches]
- Search: `GET https://www.chairish.com/search?q=<kw>&page=N` [S]. Collections: `https://www.chairish.com/collection/<slug>` (e.g., `sofas`, `coffee-tables`) [V].
- Params seen on live and indexed URLs [V]:
  - `page=N`
  - `sort=-num_favorites` (other sort labels: Curated, Newest, Price low→high, high→low, Near Me; the exact values are likely `-date_created`, `price`, `-price` [U])
  - `price=-100` (max price 100; format `min-max` [S])
  - `national_shipping_options=FS` (free shipping)
  - `item_type=V|N` (vintage / new & custom)
  - `misc_sales=MD` (on sale)
  - `categories=G` on shop search
  - Page size 24/48/96.
- Parse: search and collection HTML embed a JS object **`PRODUCT_ID_TO_PRODUCT_JSON_MAP`** holding title, price, original price, category and image for 48 products/page [S]. Tiles carry title, W×D×H inches, price, struck-through original, product id, badges (Free Shipping, Limited Time Sale) [V].
- PDP: `https://www.chairish.com/product/{id}/{slug}`. JSON-LD `Product` [S] plus OpenGraph meta, verified: `og:price:amount`, `product:availability=instock`, `product:brand`, `product:condition=used`, `product:category=TABLE:COCKTAIL`. Spec list gives dimensions, materials, style, period, country of origin and lead time [V].
- Discovery alternative: public XML product sitemaps (crawlergang actor), with no proxy needed per README [S].
- Fields: `id, title, url, price, originalPrice, designer/brand, period/era, style, condition, materials, color, height/width/depth (in), countryOfOrigin, seller name/location, images, availability (in stock/sold)` [S].
- Sold: PDPs of sold items remain and show sold status. There is no public sold-comps search or sold prices list [S]. Chairish runs "Chairish Auctions" (help article exists) [V].
- Bot: plain fetch OK [V]. Actors default to residential "to avoid rate limiting" [S].
- Note: one Chairish PDP had `canonical` pointing to pamono.com, so there is cross-listing between Pamono and Chairish. **Dedupe across sources.** [V]
- ToS: support.chairish.com Terms page returned client_error [U]. Affiliate: not confirmed [U].

### 2.3 Kaiyo

- URL shapes (from search-engine index) [V]:
  - `https://kaiyo.com/furniture/?q=<kw>&page=N&searchType=pos`
  - `https://kaiyo.com/furniture/?terms=sofa`
  - `https://kaiyo.com/furniture/sofas/?max_price=500`
  - `https://kaiyo.com/furniture/storage/dressers/?max_price=1000&min_price=500`
  - `https://kaiyo.com/brand/<brand>/` (e.g., `/brand/flexform/`)
- Internals (API/JSON): unknown [U]. No public scrapers found.
- **Every kaiyo.com URL returned client_error to the plain fetcher** [V]. Assume a strict bot wall (likely Cloudflare) that a logged-out server request will not pass without a browser-grade client [S]. Under "no bypassing bot protection", treat Kaiyo as **partnership / affiliate only** until a plain request is shown to work.
- Fields expected: title, price, est. retail, brand, dimensions, condition, metro (NYC/DC/Philly/Boston/LA) [U].
- Affiliate/ToS: not found [U].

### 2.4 AptDeco

- Catalog: `https://www.aptdeco.com/catalog/furniture`, `/catalog/furniture/sofas/sleeper-sofas`, `/catalog/sofas?sort=price-asc`, `?page=57` [V URL shapes].
- Stack: Next.js (`/_next/static/`, build v2.9.6) [V], so parse `<script id="__NEXT_DATA__">` → `props.pageProps` [S]. A search backend (possibly Algolia) is likely but not confirmed [U].
- Facets visible [V]: subcategory, Brand (~250), Material, Color, **Condition** (Good / New / Satisfactory / Age-worn / Floor model), Price, Height/Width/Depth, Deals (delivery discount, **self pickup available**), **Location: state, city, plus distance radius**, Sort.
- Tile fields [V]: title, price, original price, Qty, **Est. retail + % off**, badges (Great Price, Price Drop, $99 Off Delivery), slug URL.
- Bot: `/catalog/sofas` fetched OK. `/terms` and `/services` returned client_error [V], which suggests path-dependent WAF rules.
- **Affiliate: Awin merchant 93197 (AptDeco)** [V]. Commission on purchases and on referred listings. Payment "through the ShareASale affiliate network" (ShareASale merged into Awin). Bans PPC brand bidding and coupon distribution. No feed mentioned. Ask Awin for a product feed.

### 2.5 LiveAuctioneers

- Public URLs [V]:
  - search `https://www.liveauctioneers.com/search/?keyword=<kw>&category_id=4&status=online&sort=relevance` (`status=online` = upcoming; archive/sold status value likely `archive` [U])
  - category `/c/<category>/`, `/c/<cat>/creator/<name>/`, `/c/<cat>/material/<m>/`
  - catalog `/catalog/<id>_<slug>/?page=N` (24 lots/page)
  - item `/item/<id>_<slug>`
  - sold lot `/price-result/<slug>/`
  - price guide `/price-guide/<cat>/creator/<name>/`
  - results hub `/auction-results`
- Data: pages are server-rendered and an actor "reads the embedded application state directly" (historically `window.__data` Redux state [U]). The internal JSON search API host was not confirmed this session [U]. Capture it from devtools.
- Fields (actor output) [S]: `itemId, title, lotNumber, catalogId/title, auctionHouse, sellerId, lotLocation, saleDate, isLiveAuction/isTimedAuction, estimateLow/High, startPrice, currentBid, bidCount, buyNowPrice, salePrice (hammer, when sold), isSold, currency, imageUrl, itemUrl`. Detail adds category path, description, condition report and dimensions.
- **Sold prices, logged out** [V]: catalog lots show "SOLD" with a **"See Winning Bid"** link (the amount is not in the HTML). The price-guide aggregates show **"Median Hammer Price Unlock" / "Hammer Price Range Unlock"**, so they are gated behind a (free) account. The site advertises ~29M results back to 1999, updated daily.
- Bot: **Imperva/Incapsula** [S], residential recommended.
- **ToS (rev. 2025-03-26), §8.3** [V]: "The sites contain robot exclusion headers… You agree that you will not use any robot, spider, scraper, or other automated means to access the sites…" plus a ban on bypassing "robot exclusion headers or other measures". §3 limits use to "personal non-commercial use".
- Affiliate: none found [U].
- Verdict: high pricing value, but ToS-explicit and login-gated realized prices. Ask LiveAuctioneers for a data license.

### 2.6 Invaluable

- Search page `https://www.invaluable.com/search?query=<kw>&keyword=<kw>` [S]. Lot pages `/auction-lot/<slug>-<lot>-c-<ref>` are server-rendered [V]. Price archive `/catalog/advancedSearch.cfm?srchScope=p` [V].
- Backend: "public **Algolia**-backed search", with separate **upcoming** and **archive** indexes [S]. App ID, search key and index names were **not captured** [U]. Get them from devtools (`x-algolia-application-id`, `x-algolia-api-key` headers on `*-dsn.algolia.net/1/indexes/*/queries`).
- Facets (from actor inputs) [S]: keyword, categories (108), artist/maker, auction house, date from/to, country/state, price range (archive), estimate range, current bid range, bids, sale type (Live/Timed/Online), sort (8 orders), sold-only/unsold-only.
- Fields [S]: `lotRef, lotNumber, title, description, category/subcategory, artistName, auctionHouse/houseRef, catalogRef, saleType, saleDate(Unix), location, country, lat/lon, estimateLow/High, currentBid, bidCount, priceResult (hammer, sale currency), sold, resultsPosted, currencyCode, buyersPremiumPct, imageUrl, lotUrl`. Note: `priceResult = 0` can mean unsold or a house that withheld the result.
- Throttling [S]: the search API ran 35k hits from one IP unblocked. Lot/catalog **detail endpoints throttle after about 4 requests: "HTTP 202 with a zero-length body"**, with about 40s recovery. Cloudflare sits on the HTML.
- **Sold prices, logged out** [V]: a live lot page shows **"Sold: Log in to view"**. The FAQ says a free account gets 12 months of the price archive, Premium 5 years and Professional 15+ years. The Algolia index reportedly returns `priceResult` anyway [S]. Reading it would sidestep a login gate the site imposes, so treat it as **out of policy** for our rules.
- **ToS v3.11** [V]: §5.2 "You agree that you will not use any robot, spider, other automatic device, or manual process to monitor or copy our web pages or the content contained herein without our prior expressed written permission." §4.2 "…or perform any form of data extraction or data-mining whatsoever. You shall not store electronically any portion of any Services and/or Content."
- Affiliate: none found [U].

### 2.7 Etsy (official Open API v3)

- **Endpoint** [V: developer docs mirror]: `GET https://api.etsy.com/v3/application/listings/active` (findAllListingsActive).
- **Auth** [V]: header `x-api-key: <keystring>:<shared_secret>`. **Mandatory since 2026-02-09.** Bare-keystring requests are rejected (etsy/open-api discussion #1529, 2026-02-02). No OAuth needed for public reads.
- Params [V]:

  | Param | Values / notes |
  |---|---|
  | `keywords` | search text |
  | `taxonomy_id` | int; discover via `GET /v3/application/buyer-taxonomy/nodes` |
  | `min_price`, `max_price` | price range |
  | `shop_location` | must be parseable by Etsy |
  | `sort_on` | `created \| price \| updated \| score` (needs keywords) |
  | `sort_order` | `asc \| desc` (ignored for score) |
  | `limit`, `offset` | paging; max limit 100 [U] |
  | `currency` | ISO 4217 |
  | `buyer_country` | ISO 3166-1 alpha-2 |
  | `is_safe` | filters mature content |

- Response [V]: `count`, `results[]` with `listing_id, shop_id, title, description, state, url, price{amount,divisor,currency_code}, converted_price, tags, materials, style, who_made, when_made, item_length/width/height, item_dimensions_unit, item_weight, quantity, num_favorers, shipping_profile_id, taxonomy_id, creation_timestamp…`.
- Vintage: filter client-side on `when_made` (e.g., `1960s`, `before_2007`) and `who_made=someone_else` [S]. There is no server-side `when_made` filter on this endpoint [U].
- Images and shop: not in this response. Batch-hydrate with `GET /v3/application/listings/batch?listing_ids=…&includes=Images,Shop` (≤100 ids) [S].
- Limits: per-key daily quota shown in the dev portal. Creating extra keys to dodge limits is prohibited [V]. The historical default was 10 QPS / 10k QPD [U].
- **API Terms** [V]:
  - app access only "después de que Etsy apruebe la Finalidad de la aplicación" (after app approval)
  - ad content ≤ **6h** old, other content ≤ 24h; cache no longer than reasonably needed
  - must display "The term 'Etsy' is a trademark of Etsy, Inc. This application uses the Etsy API but is not endorsed or certified by Etsy, Inc."
  - may not "replicate Etsy's core functionality" or "divert sales or migrate members off Etsy"
  - no using the API to gather content for AI training
  - site scraping banned without written authorization
  - Implication: link out to Etsy for checkout. Don't cache long.
- Affiliate: Etsy Affiliate Program on **Awin** [S].

### 2.8 Pamono

- Category: `https://www.pamono.com/furniture?p=N` ("Page 1 of 1488") [V]. Product URLs are flat slugs `https://www.pamono.com/<title-slug>` [V]. Filters seen: `itmq_product_type=3655`, `style=889` (Magento-like attribute IDs) [V]. Filter groups: Vintage/New, Price, Style, Design Period, Country of Manufacture, Shop Locally (EU/Worldwide/Ships From), Color, Labels, Dimensions, Materials, Designers & Makers. Sort: Featured / Recently Added / Price ↑↓ [V].
- Fields (tile) [V]: title (often includes designer, maker, decade, origin, set size), price in $, badges (Top, Rare Find). PDP fields per Bright Data: designer, manufacturer, period, materials, dimensions, condition, price, origin, dealer, images [S]. JSON-LD presence not verified (scripts stripped by fetcher) [U].
- Bot: plain fetch OK, `meta robots INDEX,FOLLOW` [V].
- Terms: no automation clause found in `/terms` [V]. Pamono GmbH, Berlin.
- Affiliate: FlexOffers lists 4% / 60-day, but "not currently offering this program" [V]. Try Awin or Pamono direct [U].
- Cross-listing with Chairish observed. Dedupe.

### 2.9 Ruby Lane

- URL shapes (search index) [V]:
  - `https://www.rubylane.com/search?q=antique+chairs`
  - `https://www.rubylane.com/search?cat=Furniture&f_itemtype=Antique`
  - `https://www.rubylane.com/furniture-lighting?cat=Furniture&f_itemtype=Vintage&ipp=180&pricerange=500%2C999`
  - `cat=Furniture:Mirrors` (hierarchy with `:`)
  - item `https://www.rubylane.com/item/<shopid>-<sku>/<slug>`
- Fields (Bright Data list) [S]: title, price, shop name, category, era, maker, materials, condition, dimensions, item number, shop location.
- **Every page (search, item, terms) came back as an empty body with `meta robots: noindex,nofollow`** [V]. That pattern fits a JS challenge interstitial. Treat it as bot-protected. A plain logged-out server request probably won't get content without solving the challenge, which is out of policy.
- Affiliate / ToS: not retrievable [U].

### 2.10 Selency

- French marketplace (raised funding; EU delivery). No US storefront or US shipping found [U]. **Skip for a US shopper.**

### 2.11 Herman Miller / DWR / Knoll pre-owned

- **Herman Miller Refurbished** [V]:
  - launched 2026-06-22 (MillerKnoll press release). Aeron only.
  - inspected, cleaned, recalibrated; **5-year warranty**; US and Canada; final sale.
  - prices: Remastered $945–$1,015, Classic $695 (chairsfx, 2026-07) [S].
  - Store: `https://store.hermanmiller.com/herman-miller-refurbished` (Salesforce Commerce Cloud).
  - Grid endpoint [V]: `GET /on/demandware.store/Sites-herman-miller-Site/en_US/Search-UpdateGrid?cgid=herman-miller-refurbished&srule=price-low-to-high&start=0&sz=48`. Returns HTML tiles: name, color/finish, price or range.
  - Facets: designer, collection, in stock, assembled. Only about 2 results at present.
  - An earlier "Previously owned" program was not found [U].
- **DWR**: physical outlet stores and warehouse sales (Brooklyn, Leesburg Premium Outlets) [S]. No online certified pre-owned program found [U]. Likely SFCC `Search-UpdateGrid` on a sale category [U].
- **Knoll**: no consumer pre-owned program found [U].
- Affiliate: HM/DWR/Knoll programs are believed to exist on a major network (Rakuten/Impact) [U]. Feeds would cover new goods mainly.

### 2.12 EBTH (Everything But The House)

- Still operating in 2026 under "© 2026 High Road Holdings, LLC" after its 2019 ABC/sale [V]. Regional warehouses (Cincinnati, Columbus, Chicago, DC, Charlotte, Boston, Dallas) [V].
- URLs [V]: `/browse`, `/browse?sort=sale_ends_at_asc`, `/categories`, `/sales/{id}-{slug}`, `/items/{id}-{slug}`, `/regions/{id}-{city}`. Search param name not captured [U].
- Fields: title, pickup flag, location (e.g., "EBTH Columbus - Hilliard"), current bid [V]. Actor adds `numberOfBids, endTime, properties (brand/model/dimensions), itemNumber, condition` [S]. Closed-sale prices not observed [S].
- **ToS (rev. 2026-06-29)** [V]: prohibits "Use any robot, spider, scraper, data mining tools, data gathering and extraction tools… automated means to access or use the Services" and "Use any manual process to monitor or copy any of the material or data on the Services."

### 2.13 OfferUp

- Public URL shapes [S]: `https://offerup.com/search?q=<kw>`, `/c/<category>`, `/c/<category>/<kw>`, `/explore/k/<kw>`, `/item/detail/<id>`.
- Facets (actor) [S]: location, radius 1–500 mi, priceMin/Max, condition (NEW, OPEN_BOX, REFURBISHED, USED, BROKEN, OTHER), sort (`best_match, -posted, distance, price, -price`).
- Fields [S]: `listingId, title, price, conditionText, locationName, url, imageUrl`. Details add lat/lon, category L1–L3, photos, postDate, originalPrice, localPickupEnabled, shippingEnabled and seller ratings.
- Bot [S]: search and category pages load without challenge (US datacenter OK). **Item detail pages serve a bot challenge on every tier tested.** Non-US IPs are geo-blocked.
- **ToS (rev. 2026-07-21) §7** [V]: bans "any type of automated means to… collect or extract data from OfferUp… such as a harvesting bot, robot, spider, script, crawler, or scraper, not provided by OfferUp" and "Develop or use any third-party applications that interact with the OfferUp Services without OfferUp's prior written consent." Partner programs exist (about.offerup.com/partnerterms) [V]. **Ask for a partnership rather than scraping.**

### 2.14 eBay (not on the list, but it is the largest US vintage-furniture inventory)

- `GET https://api.ebay.com/buy/browse/v1/item_summary/search`
  - `q`, `category_ids`
  - `filter=price:[100..2000],priceCurrency:USD,conditions:{USED},buyingOptions:{FIXED_PRICE|AUCTION|BEST_OFFER},itemLocationCountry:US,deliveryCountry:US,pickupCountry:US,pickupPostalCode:94110,pickupRadius:50,pickupRadiusUnit:mi`
  - `aspect_filter=categoryId:…,Brand:{Herman Miller}`
  - `sort=price|-price|newlyListed|distance`
  - `limit` ≤200, `offset`; result set capped at 10,000
  - header `X-EBAY-C-MARKETPLACE-ID: EBAY_US`
  - OAuth client-credentials app token, scope `https://api.ebay.com/oauth/api_scope` [S/U on exact syntax; V on 10k cap, default BIN-only, marketplace header]
- Production Buy API access requires eligibility, approval and a contract [V].
- Sold comps: Marketplace Insights API (restricted) [S].
- Affiliate: **eBay Partner Network** (EPN tracking params on `itemAffiliateWebUrl`) [S].

### 2.15 Notes only

- **Craigslist**: ToS prohibits robots, spiders and scrapers. Craigslist has litigated against scrapers (3Taps, 2013) [U]. Not using.
- **Nextdoor For Sale & Free**: requires an account and address verification. There is no logged-out search [U]. Not using.
- **Facebook Marketplace**: covered by another agent.

### 2.16 Other US sources worth considering

- **Bidsquare** (premium auction houses): server-rendered search HTML plus lot JSON-LD, Cloudflare, sold price public only for some houses (`priceGated`) [S].
- **MaxSold** (online estate sales, local pickup): "public JSON API", unprotected per actor, current bids only [S].
- **HiBid / Proxibid** (estate and consignment auctions): Apify actors exist [S]. ToS not checked.
- **Wright, Rago, Hindman, Doyle, Toomey** (design auction houses; realized prices often public on the house's own site): Apify actors exist for Wright, Doyle and Toomey [S]. Good for designer-piece comps.
- **Vinterior** (UK, ships US), **Catawiki** (EU, ships US, closed prices visible [U]). Lauritz: EU, low US relevance [U].
- Dealer sites (e.g., **Modern Resale** in Dallas, local consignment shops): many run on Shopify, so `/<collection>/products.json` and `/search?q=…&view=json`-style endpoints apply. Assess case by case [U].

---

## 3. Sold / price-history matrix (for pricing)

| Source | Logged-out sold price? | Notes |
|---|---|---|
| LiveAuctioneers | **No** ("See Winning Bid", "Unlock") [V] | Free login reveals it; ToS bans automation |
| Invaluable | **No** ("Sold: Log in to view") [V] | Algolia index carries `priceResult` [S], but using it bypasses the gate |
| 1stDibs | Partial: `isSold` + "recent sales" price range [S] | Via MCP `item_details` [U] |
| Chairish | Sold status only [S] | No price list for sold items |
| Bidsquare | Some houses [S] | `priceGated` flag |
| eBay | Marketplace Insights (restricted) [S] | Apply |
| Auction house sites (Wright, Rago, Hindman) | Often public [U] | Per-house ToS |

---

## 4. Sources

- 1stDibs MCP: https://skillselion.com/mcp/tool/com.1stdibs/1stDibs ; https://mcpplaygroundonline.com/mcp-servers/com-1stdibs-1stdibs ; https://www.mcpbundles.com/skills/1stdibs-mcp
- 1stDibs actors: https://apify.com/scrapesage/1stdibs-scraper.md ; https://apify.com/lulzasaur/firstdibs-scraper.md ; https://apify.com/solidcode/1stdibs-com-scraper.md ; https://apify.com/saswave/advanced-1stdibs-scraper
- 1stDibs ToS: https://www.1stdibs.com/about/user-agreement/ ; affiliate: https://www.1stdibs.com/answers/does-1stdibs-have-an-affiliate-program ; https://affsignal.com/merchant/1stdibs
- 1stDibs pages: https://www.1stdibs.com/furniture/seating/lounge-chairs/?color=red ; https://www.1stdibs.com/buy/sold-items-furniture/ ; https://beautifulcode.1stdibs.com/category/cdn/
- Chairish: https://apify.com/lulzasaur/chairish-scraper.md ; https://apify.com/crawlergang/chairish-scraper.md ; https://www.chairish.com/collection/sofas ; https://www.chairish.com/collection/sofa-sets?sort=-num_favorites&page=8 ; https://www.chairish.com/product/3805236/charlotte-triple-black-coffee-tables-set-of-3
- Kaiyo URL shapes: https://kaiyo.com/furniture/storage/dressers/?max_price=1000&min_price=500 (search index; fetch blocked)
- AptDeco: https://aptdeco.com/catalog/sofas?sort=price-asc ; Awin terms https://ui.awin.com/merchant-profile-terms/93197
- LiveAuctioneers: https://www.liveauctioneers.com/termsandconditions ; https://www.liveauctioneers.com/catalog/368753_mid-century-modern-statement-pieces/ ; https://www.liveauctioneers.com/price-guide/ ; https://www.liveauctioneers.com/en-gb/price-result/please-read-terms-and-conditions-15-buyers-premium/ ; https://apify.com/lulzasaur/liveauctioneers-scraper.md ; https://apify.com/ivanvs/liveauctioneers-scraper ; https://apify.com/parseforge/liveauctioneers-scraper
- Invaluable: https://www.invaluable.com/inv/agreements/ ; https://www.invaluable.com/inv/help/faq/search-price-archive/ ; https://www.invaluable.com/auction-lot/finn-juhl-chieftain-lounge-chair-26-c-dcccf8e5ce ; https://apify.com/lulzasaur/invaluable-scraper.md ; https://apify.com/parseforge/invaluable-auctions-scraper ; https://apify.com/normdata/invaluable-scraper.md ; https://apify.com/lexis-solutions/invaluable-scraper
- Etsy: https://developer.etsy.com/documentation/essentials/authentication/ ; https://github.com/etsy/open-api/discussions/1529 ; https://www.withone.ai/knowledge/etsy/conn_mod_def%3A%3AGMUoZnuXdJA%3A%3AjmK5Bn8BQvGABXafXK52gA/md ; https://www.etsy.com/mx/legal/api
- Pamono: https://www.pamono.com/furniture ; https://www.pamono.com/terms ; https://www.flexoffers.com/affiliate-programs/pamono-affiliate-program/ ; https://brightdata.com/products/web-scraper/pamono
- Ruby Lane: https://www.rubylane.com/search?q=antique+chairs ; https://www.rubylane.com/info/termsofuse ; https://brightdata.com/products/web-scraper/ruby-lane
- Herman Miller: https://news.millerknoll.com/2026-06-22-Herman-Miller-introduces-Aeron-Refurbished,-extending-the-life-of-its-most-recognized-design ; https://store.hermanmiller.com/herman-miller-refurbished ; https://chairsfx.com/trends/official-refurbished-herman-miller/
- EBTH: https://www.ebth.com/ ; https://www.ebth.com/terms ; https://www.wcpo.com/money/local-business-news/everything-but-the-house-heads-for-liquidation-process ; https://apify.com/ivanvs/ebth-scraper
- OfferUp: https://offerup.com/terms ; https://apify.com/abotapi/offerup-scraper.md ; https://apify.com/parseforge/offerup-scraper.md
- eBay: https://developer.ebay.com/api-docs/buy/browse/overview.html
- Others: https://apify.com/lulzasaur/bidsquare-scraper.md ; https://apify.com/lulzasaur/maxsold-scraper.md ; https://www.hunker.com/13776523/best-places-to-buy-used-and-vintage-furniture-and-decor-online

**Blocked this session (re-check manually):** all `/robots.txt` files (chairish, 1stdibs, kaiyo, aptdeco, liveauctioneers, invaluable); https://www.chairish.com/pages/terms-of-service ; https://support.chairish.com/hc/en-us/articles/115007071507-Terms-of-Service ; https://www.aptdeco.com/terms ; https://kaiyo.com/legal/purchase-agreement/ ; https://pulsemcp.com/servers/1stdibs ; https://www.liveauctioneers.com/price-guide/chairs/creator/svend-skipper/ ; eBay item_summary/search reference page (server error).
