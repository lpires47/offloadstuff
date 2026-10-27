# Secondhand fashion marketplaces: how logged-out website search works (research as of 2026-10-26)

**Scope:** one on-demand, logged-out query per shopper search. No logins, no CAPTCHA solving, no bot-protection bypass.

**Evidence tags**
- **[V]** verified from a primary source: the site's own ToS or API docs, fetched during this research.
- **[S]** secondary: a 2026 scraper write-up, Apify actor README, browse.sh/explainx "skill" page, Scrapfly blog, or a press article.
- **[U]** unverified: my prior knowledge or inference. Confirm in DevTools before building on it.

**Research limits**
- The environment fetches only URLs that surfaced through web search. Direct fetches of robots.txt timed out on permission for poshmark.com, depop.com, mercari.com, grailed.com, vinted.com and thredup.com.
- **No robots.txt was read first-hand.** The robots notes below are secondary, and you should pull each file yourself before launch.
- The therealreal.com/terms fetch failed (client error).
- No Depop ToS text was retrievable.

---

## 1. Summary table

| Site | Access method (what the website itself does) | Logged-out from a server? | Bot protection | Sold search | ToS risk for an automated agent | Confidence |
|---|---|---|---|---|---|---|
| **Poshmark** | `GET poshmark.com/vm-rest/posts?request=<urlencoded JSON>` (JSON). Fallback is the `/search?query=` HTML. | Yes. No cookies needed for `/vm-rest/posts`. Residential IP recommended. | Akamai. `/vm-rest/posts/search` returns 403; `/vm-rest/posts?request=` was reported un-gated. Some 403s on datacenter IPs. | Yes: `inventory_status[]=sold_out` / `availability=sold_out`. Gives sold price (= list price) and `status_changed_at` as a proxy for sale date. | **High.** ToS §4(b) bans "scrape, harvest, crawl or use any … automated systems". | Med-High [S] |
| **Depop** | SSR `www.depop.com/search/?q=` (Next.js RSC `self.__next_f.push` chunks), plus a `webapi.depop.com` XHR for paging. | Partial. HTML is fetchable; the `webapi` XHR returns 403 without Cloudflare cookies. | Cloudflare (Turnstile / `__cf_bm`) on `webapi.depop.com`. **Strict.** | Status `SOLD` appears in results. A sold-only web filter is unconfirmed; actors fetch sold items per seller. | High. Clause not retrieved; assume a standard no-scraping clause [U]. | Medium. Sources conflict on which endpoint is live. |
| **Mercari US** | `GET www.mercari.com/v1/api/search?...` (XHR). `__NEXT_DATA__` is empty, so results come only from the XHR. | **No.** Cookieless requests get 401. The SPA mints a DPoP-style token and `__cf_bm`. | Cloudflare Bot Management. Verified browser plus residential IP needed. **Strict.** | Yes: `status=sold_out`. | Medium-High. ToS bans circumventing security measures and "excessive burden"; a separate Prohibited Conduct page was not read. | Medium [S] |
| **Grailed** | Algolia: `POST https://MNRWEFSS2Q-dsn.algolia.net/1/indexes/*/queries` with the public search key from `window.PUBLIC_CONFIG`. | Yes. Algolia accepts datacenter IPs; refresh the key from the homepage on 403. | None on Algolia. Grailed's own site sits behind a CDN/WAF [U]. | **Yes, best in class:** sold index with `sold_price` and `sold_at`. | **Very high.** ToS (eff. 2026-09-03) explicitly bans AI/LLM systems, AI assistants, third-party extensions without consent, and ignoring robots.txt. | High for mechanism [S]; ToS [V] |
| **Vinted (vinted.com, US)** | `GET www.vinted.com/api/v2/catalog/items?search_text=…` | Partial. Needs the anonymous `access_token_web` cookie, set by a homepage GET; cold requests get 401. | Cloudflare (`__cf_bm`) and DataDome (cookie on cold load, reported on vinted.fr). Datacenter IPs rate-limited. | No public sold search [S/U]. | **High.** ToS §6 bans "bots, scraping programs, crawling programs, spiders" unless authorised. | Medium-High [S]; ToS [V] |
| **ThredUp** | GraphQL `www.thredup.com/api/v1/shop/graphql` (`itemsV2`), plus SSR Apollo cache in category HTML. | Mostly. Anonymous session cookie first. Reports conflict: "rarely blocks DC IPs" vs "Cloudflare challenge, residential US". | Cloudflare (reported). US-only geo. | No. Sold items drop out (some category pages show `availability: Sold`). | Medium-High. ToS not retrieved [U]. | Medium [S] |
| **The RealReal** | Category pages SSR up to 120 items in `__NEXT_DATA__`. Keyword search and deep paging use a bot-gated GraphQL API. | Category HTML only, residential IP. Keyword search is not practical logged out. | **PerimeterX / HUMAN. Strict.** | No public sold search [U]. | High [U] (terms fetch failed). | Low-Med [S] |
| **Vestiaire Collective** | Internal search API (reported `search.vestiairecollective.com/v1/product/search`, POST JSON [U]). Product pages carry `__NEXT_DATA__`. | **No.** "Cloudflare managed challenge on every route, including its own search API." | Cloudflare managed challenge. **Strict.** | Items carry `sold` / `isSold`. Sold pages 308-redirect. Sold-search filter unconfirmed. | High [U]. | Low-Med [S] |
| **Fashionphile** | Search backend appears to be Algolia (`objectID`, `nbPages`, "Algolia results list"); Next.js `__NEXT_DATA__` on product pages. | Likely yes for the search backend ("accessible without a proxy"). | Header/TLS fingerprinting on site pages; vendor unnamed. | No public sold search [U]. | Medium [U] (not retrieved). | Low-Med [S] |
| **Rebag** | Shopify storefront `shop.rebag.com`: `/search` and `/products.json`, `/collections/<handle>/products.json`, predictive search. | Yes. "No authentication or proxy required." | Light (Shopify defaults) [S]. | No. Only `available`. Rebag "Clair" gives resale estimates [U]. | Medium [U]. | Medium [S] |
| **StockX** | `stockx.com/search?s=` SSR (`__NEXT_DATA__` / `__REACT_QUERY_STATE__`) holds previews. Pricing comes from a GraphQL XHR. | Barely. Heavy blocking. | PerimeterX (per webscraping.fyi) and/or Cloudflare. **Very strict.** | Last sale, 72-hour sales and recent sales are embedded in the product-page `__NEXT_DATA__`. | **High.** ToS bans "any robot, spider, scraper, or other automated or manual means". | Medium [S]; ToS [S] |
| **GOAT** | Constructor.io: `GET ac.cnstrc.com/search/{q}?key=key_XT7bjdbvjgECO5d8&c=ciojs-client-2.29.12&...`. PDP via `__NEXT_DATA__`. | Constructor endpoint likely yes (third-party CDN) [S]. goat.com pages: Cloudflare blocks datacenter IPs. | Cloudflare Bot Management on goat.com. | No public per-listing sold data; `lowest_price_cents` only [S]. | High. ToS (2026-01-26) bans automated access/search. | Medium [S] |
| **eBay** | **Official** Browse API `GET api.ebay.com/buy/browse/v1/item_summary/search`. | Yes, via OAuth app token. | n/a (API). | Not in Browse. Marketplace Insights `item_sales/search` is Limited Release and needs approval. | Low via API. The site's User Agreement (eff. 2026-02-20) bans "LLM-driven bots", so never scrape the site. | High [V/S] |
| **Etsy** | **Official** Open API v3 `GET openapi.etsy.com/v3/application/listings/active?keywords=` (`x-api-key: keystring:shared_secret`). | Yes (API key only for public listings). | Website search: DataDome-class protection [U]; actors need residential IPs and a "challenge step". | No sold listings in the public API [U]. | Medium. API terms (updated 2026-08-18): 6-hour freshness, no AI training. Etsy rejected an LLM-based app in March 2025. | Medium-High [V/S] |

**Bottom line**
- Only three sites are both reachable logged-out from a server and protection-free on the search backend: **Grailed** (Algolia), **Poshmark** (`/vm-rest/posts`) and **Rebag** (Shopify). Fashionphile (Algolia-like) and GOAT's Constructor endpoint are probable additions.
- Mercari, Depop's API, Vinted, The RealReal, Vestiaire and StockX all gate search behind Cloudflare, PerimeterX or DataDome challenges. Under the no-bypass rule, they are effectively unavailable for server-side search.
- Nearly every ToS prohibits automated access whether or not you are logged in. Grailed and eBay now name LLM/AI agents explicitly. "Same as the website's search" is not a ToS safe harbour.
- Partnerships and affiliate feeds are the only clean path for most of these sites. Phia appears to have used that path (see §16).

---

## 2. Poshmark

**Request spec [S: explainx/browse.sh skill, updated 2026-05-18/21]**

```
GET https://poshmark.com/vm-rest/posts?request=%7B%22query%22%3A%22madewell%20jeans%22%2C%22count%22%3A48%2C%22experience%22%3A%22all%22%7D
```

The decoded `request` JSON:

```json
{"query":"madewell jeans","count":48,"experience":"all","sort_by":"price_asc","max_id":"<more.next_max_id from previous page>"}
```

- `count` must be an integer (`"48"` returns 400). Keep it at 48 or below.
- `experience` is required; omitting it returns 500.
- `sort_by`: `price_asc`, `price_desc`, `best_match`, `relevance`. Default is newest. `just_shared` and `most_popular` return 400.
- Pagination: pass `more.next_max_id` back as `max_id`.
- **Facet filters (brand, size, category, condition, price, availability) are silently ignored in this envelope** per the skill page. Use the HTML search URL for those, or put brand and size in the `query` text.
  - HTML fallback: `https://poshmark.com/search?query=...&brand[]=...&availability=available&sort_by=...`
  - Older community code also put a `filters` object inside `request` (e.g. `{"department":"Women","inventory_status":["available"]}`) [U]. Test it.
- Other endpoints: `/vm-rest/posts/{id}`, `/vm-rest/users/{username}/posts?count=&offset=`, `/vm-rest/users/{username}`.
- No headers, cookies or CSRF required [S].

**Response fields [S]**

Top level: `data[]`, `more{total,next_max_id,is_next_max_id_present}`, `suggested_filters`.

| Need | Field |
|---|---|
| id | `id` (listing URL = `https://poshmark.com/listing/<slug>-<id>`, slug from title [U]) |
| title | `title` |
| price | `price_amount{val,currency_code}`, `original_price_amount` |
| brand | `brand`, `brand_obj` |
| size | `size`, `size_obj{size_system,display_with_size_system}` |
| condition | `nwt` (new with tags) boolean. No granular condition field in search. |
| images | `cover_shot`, `pictures[]` |
| status | `inventory.status` = `available` / `sold_out` / `reserved` / `not_for_sale` |
| dates | `created_at`, `first_published_at`, `status_changed_at` |
| seller | `creator_username`, `creator_display_handle` |
| seller location | not in search results |

**Logged-out / bot protection**
- Logged-out works [S].
- Akamai sits in front: `/vm-rest/posts/search` returns an Akamai 403, while `/vm-rest/posts?request=` was reported un-gated (2026-05) [S].
- Another 2026-09 actor reports occasional 403s and PerimeterX-style pages under load. Its datacenter IP saw 0 of 24 requests blocked in a short test [S].
- One Apify README states "Poshmark has no active anti-bot" but recommends a US IP [S].
- Keep requests to 1/s or below and cache.

**Sold**
- Supported: `https://poshmark.com/search?query=coach%20bag&inventory_status[]=sold_out` [S gio21] or `availability=sold_out` [S kulqiz, modified 2026-09-14].
- Sold price equals the last list price. Poshmark does not expose the accepted-offer amount [S].
- Sale date: approximate it with `status_changed_at` [S/U].

**robots / ToS**
- robots: reported to disallow `/search` (among others), with `/vm-rest/` **not listed** [S]. Not verified first-hand.
- ToS [V] (https://poshmark.com/terms, Effective Oct 3 2024; version 4.6 effective June 3 2025):
  - §4(b): you may not "copy, scrape, harvest, crawl or use any technology, software or automated systems … to collect any information or data for the Service".
  - §4(b) also bars attempts to "decipher any transmission to or from the servers".

**Confidence:** Medium-High for the endpoint (2026-05). Do a 2-minute DevTools check before building.

---

## 3. Depop

**What the website does [S: browse.sh skill, 2026-05-18]**
- Search page: `https://www.depop.com/search/?q=carhartt+jacket&sort=newest&priceMin=20&priceMax=100&conditions=used_good&sizes=US-M&brands=1673&gender=male`. Add a locale prefix (`/us/`) to pin currency.
- Results are **server-rendered** inside Next.js RSC flight chunks (`self.__next_f.push([...])`), not in `__NEXT_DATA__`. Concatenate the chunks and locate `data.products[]` and `data.meta{result_count,cursor,has_more,total_count}`.
- The first SSR batch may embed only about 10 of 24 items.
- Detail pages carry JSON-LD `Product` (`offers.price`, `availability`, `itemCondition`).

**Query parameters on `/search/`**

| Param | Values |
|---|---|
| `q` | text (hashtags such as `%23y2k` work) |
| `brands` | numeric IDs |
| `sizes` | `US-M`, `UK-12` |
| `colours` | colour names |
| `conditions` | `brand_new`, `used_like_new`, `used_good`, `used_fair` |
| `priceMin`, `priceMax` | integers |
| `gender`, `isKids`, `isDiscounted` | flags |
| `sort` | `relevance`, `newest`, `priceAscending`, `priceDescending`, `popularity` |

`/search/` ignores pagination params.

**Paging XHR: sources conflict**
- browse.sh: `https://webapi.depop.com/api/v2/search/products/?what=…&cursor=…&country=us&currency=USD`, behind Cloudflare. Cookieless and proxy requests get 403; it needs `__cf_bm` and Turnstile state from a live browser [S].
- bovi actor (May 2026): `/api/v2/search/products/` "returns HTTP 410" (deprecated). It scrapes sellers and products instead [S].
- jongoose actor: search API is `/presentation/api/v1/search/products/` [S]. Host not stated; likely `www.depop.com` [U].
- Older `webapi.depop.com/api/v3/search/products` (used by 2024-era tools) [U].
- **Treat the XHR as unusable without bypass.** Only the first SSR page is cleanly reachable.

**Response fields (SSR `products[]`) [S]**
- `id`, `slug` (URL = `https://www.depop.com/products/<slug>/`)
- `status` = `ONSALE` / `SOLD` / `RESERVED`
- `pricing{original_price,discounted_price,currency_name,national_shipping_cost}`
- `country`, `pictures{"320","1280",…}`, `sizes`, `brand_name`, `brand_id`, `like_count`
- Listed date and seller location are not in structured data. Seller username is parsed from the slug prefix.

**Bot protection:** Cloudflare, strict on `webapi`. HTML pages are fetchable with a residential proxy [S]. Depop's agent-readiness score is 25/100 (startuphub, 2026-10-21) [S].

**Sold:** `SOLD` items can appear in results. A sold-only search filter on web is unconfirmed [U]. Actors get sold items per seller (`includeSold`, newest-sold-first, no sold date) [S].

**robots / ToS:** Neither retrieved. Expect standard no-scraping language [U].

**Confidence:** Medium-Low for the XHR, Medium for SSR parsing.

---

## 4. Mercari US

**Website mechanism [S: browse.sh skill, 2026-05-18, build r-v1.26.1613]**
- Search page `https://www.mercari.com/search/?keyword=...` hydrates from an XHR.
- `__NEXT_DATA__` holds no results.

```
GET https://www.mercari.com/v1/api/search?keyword=coach%20bag&categoryId=&brandId=&itemConditions=1,2&priceMin=20&priceMax=200&sizeId=&status=on_sale&sortBy=created_time&pageSize=120&offset=0
```

| Param | Values |
|---|---|
| `status` | `on_sale` / `trading` (on hold) / `sold_out` |
| `sortBy` | `default`, `created_time`, `price_asc`, `price_desc`, `num_likes` |
| `itemConditions` | 1 New, 2 Like New, 3 Good, 4 Fair, 5 Poor |
| `categoryId`, `brandId`, `sizeId`, `colorId` | build-versioned IDs |
| `shippingPayerId` | 1 seller pays, 2 buyer pays |
| other flags | `authenticated`, `offerable` |

- Pagination: `pageSize` 120 with `offset` in steps of 120.
- **Cookieless requests return `{"errors":[{"status":401,"message":"Unauthorized"}]}`.**
- Needs the SPA-minted DPoP-style header and the Cloudflare `cf-bm` cookie (about 30-minute TTL).
- `api.mercari.com/v2/entities/search` returns 401/500 and is described as a "trap".

**Older GraphQL path [S: mercarius 1.0.2, Aug 2023; stale]:** `www.mercari.com/v1/api` with persisted query `searchFacetQuery` (sha256 `5b7b667e…d38`), statuses ON_SALE / SOLD_OUT, 30 per page. Likely superseded.

**Response [S, field names not confirmed raw]**
- `meta{numFound,offset,hasMore}`
- `data[]`: `id` (`m123…`; URL `https://www.mercari.com/us/item/<id>/`), name/title, price, `status`, condition, brand, size, photos
- Seller: id, rating, ship-from zip
- Dates: `created`/`updated` epoch

**Bot protection:** Cloudflare Bot Management. Requires a verified browser session plus residential IP [S]. **Not usable without bypass.**

**Sold:** `status=sold_out` [S]. Mercari is a good pricing source if you obtain access through a partnership.

**robots:** not retrieved.

**ToS [V]:** https://www.mercari.com/us/help_center/topics/account/policies/terms-of-service/ (current version effective 2025-02-24; a new version takes effect 2026-11-05).
- Bans attempts to "disable or circumvent any security or other technological measure".
- Bans "any activity that provides an excessive burden on the Services".
- The separate Prohibited Conduct policy was not read.

**Confidence:** Medium.

---

## 5. Grailed

**Mechanism [S: bovi/grailed-listings key dated 2026-05-31; aurenic/grailed-scraper; pypi grailed_api 0.1.5 (Sep 2024)]**

```
POST https://MNRWEFSS2Q-dsn.algolia.net/1/indexes/*/queries
x-algolia-application-id: MNRWEFSS2Q
x-algolia-api-key: <publicSearchKey from window.PUBLIC_CONFIG on any grailed.com page>
Content-Type: application/json

{"requests":[{"indexName":"Listing_production",
  "params":"query=raf%20simons&hitsPerPage=40&page=0&facetFilters=[[\"department:menswear\"],[\"designers.name:Raf Simons\"],[\"category_size:tops.m\"]]&numericFilters=[\"price_i>=50\",\"price_i<=500\"]"}]}
```

- App ID `MNRWEFSS2Q` and main index `Listing_production` [S].
- Sort replicas and the sold index: aurenic says a "sold index" exists. Community name `Listing_sold_production` [U]. Sort replicas such as `Listing_by_low_price_production` / `Listing_by_date_production` [U].
- Facet attribute names (`designers.name`, `category_size`, `condition`, `location`, `price_i`, `strata`, `marketplace`) are [U]. Copy them from a DevTools capture.
- Max 40–48 hits per page (Algolia `paginationLimitedTo` is about 1,000). Slice by price for deeper result sets.
- The key rotates. On 403, re-fetch grailed.com and read `publicSearchKey` [S].

**Response fields (per `hit`) [S]**

| Need | Field |
|---|---|
| id | `id` (URL `https://www.grailed.com/listings/<id>`) |
| title | `title` |
| price | `price` (USD), `price_drops[]` |
| sold | `sold` (bool), `sold_price`, `sold_at` |
| brand | `designers[]` |
| category / size | `category`, `category_path`, `size` |
| condition | `condition` |
| other attributes | `color`, `marketplace`, `strata` |
| images | `cover_photo` / `photos` |
| seller | `user{username, seller_score}` |
| location | `location` |
| dates | `created_at`, `bumped_at` [U] |

**Bot protection:** None on Algolia. Datacenter IPs are accepted [S]. This is the easiest technical integration of the set.

**Sold:** Yes, with sold price and date. This is the best pricing comps source here [S].

**robots:** not retrieved. The ToS incorporates it ("Bypass or ignore instructions contained in our robots.txt file").

**ToS [V]:** https://www.grailed.com/about/terms (effective **2026-09-03**), §12 Prohibited Conduct. Do not:
- "Use any robot, spider, scraper, crawler, data mining tools … artificial intelligence or machine learning systems (including large language models), or other automated means to access, index, collect, harvest, or extract data or content from our Services".
- Use "AI-powered assistants, or any system that submits offers, makes purchases, or completes checkout without direct human initiation and review of each transaction".
- "Develop or use any applications, browser extensions, plugins, or third-party tools that interact with our Services without our prior written consent".

This is the most explicit anti-agent clause in the set. **Integrating Grailed needs written consent or a partnership.**

**Confidence:** High for the mechanism, High for the ToS.

---

## 6. Vinted (vinted.com, US)

Context: Vinted announced a "major" US expansion in Jan 2026 [S: FashionUnited].

**Mechanism [S: browse.sh vinted.fr skill 2026-06-20; jongoose/vinted-scraper supports vinted.com]**
1. `GET https://www.vinted.com/` with a browser-like client. This sets the HttpOnly `access_token_web`, `_vinted_com_session` [U name] and Cloudflare `__cf_bm`. A `datadome` cookie was observed on vinted.fr.
2. Call the API on the same cookie jar:

```
GET https://www.vinted.com/api/v2/catalog/items?search_text=levis%20501&catalog_ids[]=&brand_ids[]=&size_ids[]=&status_ids[]=&color_ids[]=&price_from=10&price_to=60&currency=USD&order=newest_first&page=1&per_page=96
```

- `order`: `relevance`, `newest_first`, `price_low_to_high`, `price_high_to_low`.
- `status_ids[]` is the **condition** filter.
- Cold requests get 401 `invalid_authentication_token` (`Www-Authenticate: Bearer realm="Vinted"`).
- Deep pagination caps at about 960 results.
- `/api/v2/items/{id}` returns 404; use the item HTML (JSON-LD) instead.

**Response [S]**
- `items[]`: `id`, `title`, `price{amount (string), currency_code}`, `total_item_price` (includes buyer protection), `service_fee`, `brand_title`, `size_title`, `status` (condition), `url`, `photo{url,thumbnails[]}`, `favourite_count`, `view_count`, `user{id,login,profile_url,business}`, `is_promoted`
- `pagination{current_page,total_pages,total_entries,per_page}`
- Upload date and seller location exist only on the item page DOM (`item-attributes-upload_date`, `seller-location`).

**Bot protection:** Cloudflare plus DataDome. Datacenter IPs rate-limited; residential recommended [S]. The cookie bootstrap is ordinary page-load behaviour, not a challenge solve. A DataDome challenge would be a hard stop under the no-bypass rule.

**Sold:** No public sold search [S/U].

**ToS [V]:** https://www.vinted.com/old-terms-and-conditions (version applicable from 2025-12-18; updated terms effective 2026-10-08 at /terms_and_conditions, not read).
- §6: users must not "use any kind of external software tools (including but not limited to: bots, scraping programs, crawling programs, spiders)" unless "authorised, offered or in any other way allowed by us".
- §6 also bans "data mine, screen scrape, crawl".

**Confidence:** Medium-High for the mechanism.

---

## 7. ThredUp

**Mechanism [S: crawlerbros/thredup-scraper; logiover/thredup-scraper; abotapi]**
- Search page (client-rendered): `https://www.thredup.com/women?search_text=levis&department_tags=...&sort=newest_first&page=2`.
- Data API: **GraphQL `POST https://www.thredup.com/api/v1/shop/graphql`** (operation backing `itemsV2`), called after an anonymous session cookie is set.
  - Filters: department, category, brands, condition tiers (e.g. `Q1_NWT`), colors, `priceMin`/`priceMax`, `clearanceOnly`.
  - Sort: `recommended`, `relevance`, `best_sellers`, `newest_first`.
  - 48 items per page; about 10k results cap.
  - Operation and variable names: capture them in DevTools [U].
- Category pages embed an SSR **Apollo GraphQL cache** in HTML (up to 120 items per page). `?search_tags` URLs render client-side, so they return zero items in SSR.

**Fields [S]**
- `itemNumber` (URL `https://www.thredup.com/product/<itemNumber>` [U pattern]), `title`, `brand`
- `price`, `originalPrice`/`msrp`
- `sizeLabel`, `condition`/`conditionLabel`, `colorNames`
- `photoIds`/`imageUrl`
- `state`/`availability` (`InStock` / `Sold`)
- `listedAt` (ISO)
- No seller (ThredUp is a managed marketplace; items ship from a warehouse)

**Bot protection:** Conflicting. One actor says Cloudflare challenge, US-only, residential needed. Another says datacenter IPs are rarely blocked [S].

**Sold:** No.

**ToS / robots:** Not retrieved. `llms.txt` exists at thredup.com but contains no agent policy [S].

**Confidence:** Medium.

---

## 8. The RealReal

**Mechanism [S: lulzasaur/therealreal-scraper]**
- Category or designer pages (e.g. `https://www.therealreal.com/designers/givenchy/women`, `/shop/women/handbags`) **server-render up to 120 products in `__NEXT_DATA__`**.
- Fields: title, brand, price, originalPrice/msrp, size, condition, availability, sku, url, images.
- **Keyword search and deep pagination use a "bot-gated GraphQL API".**
- Keyword search URL: `https://www.therealreal.com/products?keywords=...` [U].

**Bot protection:** **PerimeterX / HUMAN**, residential proxy plus fingerprint needed [S]. Under the no-bypass rule, at most occasional category-page fetches would work, and even those are fragile.

**Sold:** No public sold search [U].

**ToS:** Fetch failed. Assume a no-scraping clause [U].

**Alternative:** TRR runs an affiliate program with product feeds via an affiliate network [U]. Phia lists TRR as a partner [S].

**Confidence:** Low-Medium.

---

## 9. Vestiaire Collective

**Mechanism**
- Internal search API, reported as `POST https://search.vestiairecollective.com/v1/product/search` [U; search hits referenced it but no fetched page confirmed it].
- Body shape [U]: `{"pagination":{"offset":0,"limit":48},"fields":[...],"facets":{...},"q":"...","sortBy":"relevance","filters":{"catalogLinks.brand.id":[...],"universe.id":[...],"price":{...}},"locale":{"country":"US","currency":"USD","language":"en"}}`.
- Sort options: relevance, newest, price asc/desc. About 10k results cap [S solidcode].
- Product pages: `__NEXT_DATA__` → `props.pageProps.product` with `id`, `name`, `price{currency,cents,formatted}`, `sold`, `reserved`, `inStock`, `size`, `brand`, `condition`, `seller{…country}`, `creationDate` [S Scrapfly, 2026-10-05].
- Sold or deleted products 308-redirect [S].
- Sitemaps: `/sitemaps/https_sitemap-en.xml` [S].

**Bot protection:** "Cloudflare managed challenge on every route, including its own search API." Datacenter IPs flagged [S studio-amba, Aug 2026]. **Not usable without bypass.**

**Sold:** Records carry `sold` / `isSold` [S]. A sold-search filter is unconfirmed.

**ToS:** Not retrieved [U].

**Confidence:** Low-Medium.

---

## 10. Fashionphile

**Mechanism**
- Search, sale and category pages render an "Algolia results list" with `page` / `nbPages` [S Scrapfly, modified 2026-10-06].
- Actor output carries `objectID` (Algolia hallmark) and reads a "public product search backend accessible without a proxy" [S lulzasaur].
- App ID, key and index name are not published. Capture them from DevTools (look for `*-dsn.algolia.net` and `x-algolia-api-key` in page config) [U].
- Product pages: Next.js `__NEXT_DATA__` (`props.pageProps.initialState.productPageReducer.productData` or similar) [S].

**Fields [S]:** `sku`, `title`, `brand`, `category`, `condition`, `price`, `retailPrice`, `currency`, `availability`, `color`, `material`, `location` (showroom), `image`, `url`.

**Bot protection:** Site pages check headers and TLS fingerprint, and rate limits return 403 or empty responses. The search backend reportedly works without a proxy [S].

**Sold:** Not exposed [U].

**ToS / robots:** Not retrieved [U].

**Confidence:** Low-Medium. A quick DevTools capture would raise it to High.

---

## 11. Rebag

**Mechanism [S: lulzasaur, crawlergang]:** Shopify storefront at `shop.rebag.com`, using standard Shopify JSON:

```
GET https://shop.rebag.com/search?q=chanel%20flap&type=product&view=json   [U - theme-dependent]
GET https://shop.rebag.com/search/suggest.json?q=chanel&resources[type]=product&resources[limit]=10   [U - Shopify predictive search]
GET https://shop.rebag.com/collections/all-bags/products.json?limit=250&page=1   [S/U]
GET https://shop.rebag.com/products/<handle>.json
```

- Filters: brand and category collection handles (`louis-vuitton`, `all-bags`); condition grades (Never Worn, Excellent, Very Good, Good, Fair, Outlet).
- Fields: `title`, `vendor`/brand, `product_type`, `variants[].price`, `compare_at_price`, `available`, `images[].src` (cdn.shopify.com), `handle` (URL `/products/<handle>`), `published_at`, `updated_at`, `tags` (condition and material often live in tags or metafields [U]).

**Bot protection:** None notable. "No authentication or proxy required." Actors use 0.2–0.3 s delays [S].

**Sold:** No; only `available` [S]. Rebag's "Clair" tool gives resale value estimates [U].

**ToS:** Not retrieved [U].

**Confidence:** Medium.

---

## 12. StockX

**Mechanism [S: Scrapfly, modified 2026-10-05]**
- `https://stockx.com/search?s=jordan%204&page=2` (and `/search/apparel?s=`) embeds `__NEXT_DATA__` or `window.__REACT_QUERY_STATE__`, with `edges[].node` previews and `pageInfo{pageCount,total,limit}`.
- Pricing (`market.state.lowestAsk`, `highestBid`, `numberOfAsks`/`Bids`) loads through a GraphQL XHR (commonly `https://stockx.com/api/p/e` [U]).
- Product pages embed `salesInformation{lastSale,salesLast72Hours}` and recent sales [S dev.to crawlerbros].

**Bot protection:** PerimeterX per webscraping.fyi, and Cloudflare per other 2026 actors [S]. Very strict. **Not usable without bypass.**

**Sold:** Last sale and recent sales are on the product page. Full sales history needs a login [U].

**Official API:** StockX has a seller-oriented developer API (OAuth, approval required) [U].

**ToS [S]:** ConductAtlas capture 2026-07-03: you may not "use any robot, spider, scraper, or other automated or manual means to access our Services, or copy any information thereon".

**Confidence:** Medium for the mechanism.

---

## 13. GOAT

**Search mechanism [S: Scrapfly, modified 2026-10-05]:** Constructor.io.

```
GET https://ac.cnstrc.com/search/jordan%201?c=ciojs-client-2.29.12&key=key_XT7bjdbvjgECO5d8&i=<uuid4>&s=2&page=1&num_results_per_page=24&sort_by=relevance&sort_order=descending&fmt_options[hidden_fields]=gp_lowest_price_cents_3&fmt_options[hidden_fields]=gp_instant_ship_lowest_price_cents_3&_dt=<ms>
```

- Response: `response.results[].data{slug,sku,lowest_price_cents,…}` and `response.total_num_results`.
- Product URL: `https://www.goat.com/sneakers/<slug>`.
- PDP `__NEXT_DATA__`: `props.pageProps.productTemplate` and `offers.offerData`.
- Per-size, per-condition prices also come through the mobile-app API (`variants[]` with `shoeCondition`, `boxCondition`, price) [S rl1987].

**Bot protection:** goat.com uses Cloudflare Bot Management, which blocks datacenter IPs [S]. The Constructor endpoint is third-party infrastructure. Whether it enforces origin checks is unknown [U].

**Sold:** Not exposed per listing [S/U].

**ToS [S]:** ConductAtlas, GOAT Terms dated 2026-01-26: prohibits attempts to "access or search the Service or Collective Content, or download Collective Content from the Service" by automated means (excerpt truncated).

**Confidence:** Medium. The key and client version will rotate.

---

## 14. eBay (official API only)

**Browse API**
```
GET https://api.ebay.com/buy/browse/v1/item_summary/search?q=...&category_ids=...&filter=price:[20..200],priceCurrency:USD,conditions:{USED},buyingOptions:{FIXED_PRICE}&aspect_filter=categoryId:...,Brand:{Nike}&sort=newListing&limit=50&offset=0
```

- Headers: `Authorization: Bearer <client-credentials app token>`, `X-EBAY-C-MARKETPLACE-ID: EBAY_US`.
- Optional affiliate header: `X-EBAY-C-ENDUSERCTX: affiliateCampaignId=…` for EPN-tracked `itemAffiliateWebUrl` [U].
- From the docs [V]:
  - Keyword, category, EPID, GTIN and image search.
  - Fixed-price items by default.
  - 10,000-result cap; no wildcards.
  - `aspect_filter` for brand-style aspects.
  - Daily per-app call limits.
  - Production use requires eligibility checks, approvals and a contract.
- Param names `category_ids`, `filter`, `sort`, `limit`/`offset`, and fields `itemId`, `title`, `price{value,currency}`, `condition`, `image.imageUrl`, `itemWebUrl`, `seller`, `itemLocation`, `itemCreationDate` are [U] from prior knowledge. The overview page did not list them.

**Sold:** Not in Browse. The Marketplace Insights API (`/buy/marketplace-insights/v1_beta/item_sales/search`, last 90 days, `lastSoldPrice`, `lastSoldDate`) is **Limited Release and needs business-unit approval** [U; the doc pages failed to load].

**ToS:**
- The User Agreement (posted 2026-01-20, effective **2026-02-20**) bans "any robot, spider, scraper … or other automated means", explicitly including "buy-for-me agents, LLM-driven bots, or any end-to-end flow that attempts to place orders without human review" [S: ValueAddedResource, The Register].
- Use the API only.

**Confidence:** High.

---

## 15. Etsy (official API v3)

**API spec**
```
GET https://openapi.etsy.com/v3/application/listings/active?keywords=vintage%20levis&sort_on=score&sort_order=desc&min_price=20&max_price=100&taxonomy_id=...&limit=100&offset=0
x-api-key: <keystring>:<shared_secret>
```

- Header format [S: skills.cat, 2026].
- Public listing search needs only the API key; no OAuth.
- Param names and response fields are [U] from prior knowledge:
  - Fields: `listing_id`, `title`, `price{amount,divisor,currency_code}`, `url`, `state`, `original_creation_timestamp`, `when_made`, `shop_id`.
  - Images need `includes=Images` or a batch call to `/listings/batch`.
  - Offset cap is roughly 12k [U].
- Rate limit: 5 QPS / 5,000 QPD for unapproved apps [S: etsy/open-api discussion #1387, Mar 2025]. Increases via developer@etsy.com.

**Website search behaviour:** etsy.com search is a "protected target" that needs residential IPs and a "challenge step" [S]. The vendor is DataDome [U]. Don't scrape it.

**Sold:** Not available for other sellers' listings [U].

**API ToS [V]:** https://www.etsy.com/mx/legal/api, last updated **2026-08-18**.
- No automated systems or extensions to scrape the site.
- Don't cache "longer than reasonably necessary".
- Listing content must be no more than **6 hours old**; other content no more than 24 hours.
- No use of the API to collect content for **AI model training** without written authorization.
- Required disclaimer: "This application uses the Etsy API but is not endorsed or certified by Etsy."
- Don't divert members or sales off Etsy.
- No extra API keys to dodge limits.

**AI-app risk [S]:** In March 2025 Etsy's technical team told a developer it doesn't approve apps "that rely on AI generative content, including LLM or machine learning tools" (discussion #1387). Disclose the agent use case honestly when applying.

**Confidence:** Medium-High.

---

## 16. How Phia gets Poshmark and other resale listings

**What is public**
- **Partnerships claimed:** Digital Commerce 360 (2025-04-28) says Phia "has already been able to garner partnerships with leading resale apps", naming **The RealReal, Vestiaire Collective, ThredUp, Poshmark and eBay** [S]. The nature of the "partnership" (affiliate, feed, or API) is not described.
- **Its own index:**
  - Phia's site and extension copy: "150+ secondhand platforms like The RealReal, eBay, Poshmark", "250M+ secondhand items", "40,000+ retail and resale partners" (Chrome extension v1.10.67, 2026-09-08) [S].
  - Co-founder Sophia Kianni at TechCrunch Disrupt (Oct 2025): "over 150 secondhand platforms that we've integrated" and "over 350 million items in our in-house search database" [S].
  - Forbes Australia (2026-01-31): Phia "is building an in-house search engine" that uses AI to match the item a user is viewing against 300M+ products. It "began as a browser extension that surfed the web for resale comps," which "didn't work well" [S].
  - Together these suggest a **pre-built crawled and/or feed-ingested index, not live per-query site search** [U inference].
- **Business model:** affiliate commissions (Marketing Brew 2025-05-02: partners with retailers "to offer up inventory"; 5,000 direct brand partnerships per Kleiner Perkins, 2025-09-18) [S].
  - Affiliate networks typically supply product feeds. For TRR, Vestiaire, ThredUp and eBay (EPN), affiliate feeds or APIs are the likely source [U].
  - For Poshmark, no affiliate network or product feed is publicly documented. Its affiliate program is an influencer link program [S oneshop 2021]. **How Phia ingests Poshmark is not publicly disclosed.**
- **Extension data collection:**
  - Fortune (2025-11-15): an earlier extension version sent full-page HTML of visited pages to Phia's servers "to identify and support additional retailers". Phia says it now logs only URLs [S].
  - The extension sees product pages users visit, a possible crowd-sourced listing signal [U inference].
- **Reputational and legal context:**
  - Bloomberg (2026-07-09) and follow-ups found the extension did affiliate **cookie stuffing**: background-tab affiliate firing ("enable coupon auto drop", 2025-12-10 to 2026-07-07) and overriding other publishers' attribution.
  - impact.com suspended Phia's account. Daily revenue reportedly fell from about $80k to $10–28k after the features were disabled [S: cside, GIGAZINE, AI Weekly, The Star 2026-08-12].
- **Not found:** job posts, data-provider names, or docs naming a data vendor. No active Phia postings on Remotive; a finance role only on Duke Capital Partners.

**Takeaway:** Phia's resale coverage rests on (a) affiliate and brand partnerships with feeds, (b) an in-house index built over time, and (c) historically, extension-observed pages. It does not describe live logged-out site search, and no public source confirms a Poshmark data feed.

---

## 17. Sources

**Skill pages and how-tos**
- browse.sh / explainx skills: [Poshmark search-listings](https://explainx.ai/skills/poshmark.com/search-listings-vrg59r/search-listings) (2026-05-21), [Depop search-listings](https://www.browse.sh/skills/depop.com/search-listings-p8xawn) (2026-05-18), [Mercari search-listings](https://browse.sh/skills/mercari.com/search-listings-4ixl7y) (2026-05-18), [Vinted.fr catalog](https://browse.sh/skills/vinted.fr/scrape-products-read-posts-ywkpqh) (2026-06-20)
- Scrapfly: [GOAT](https://scrapfly.io/blog/posts/how-to-scrape-goat-com-fashion-apparel), [StockX](https://scrapfly.io/blog/how-to-scrape-stockx), [Vestiaire](https://scrapfly.io/blog/posts/how-to-scrape-vestiairecollective), [Fashionphile](https://scrapfly.io/blog/posts/how-to-scrape-fashionphile) (all modified Oct 2026); [Algolia hidden-API method](https://www.scrapingbee.com/blog/how-to-scrape-algolia-search/)
- [webscraping.fyi StockX](https://webscraping.fyi/scrapers/stockx/); [dev.to StockX data](https://dev.to/crawlerbros/stockx-data-for-sneaker-resellers-spot-trends-optimize-pricing-1gl8); [startuphub Depop agent-readiness](https://www.startuphub.ai/agent-ready-index/depop)

**Apify actor READMEs**
- Poshmark: [quine](https://apify.com/quine/poshmark-scraper.md), [gio21](https://apify.com/gio21/poshmark-scraper.md), [kulqiz sold comps](https://apify.com/kulqiz/poshmark-sold-comps)
- Grailed: [bovi](https://apify.com/bovi/grailed-listings.md), [aurenic](https://apify.com/aurenic/grailed-scraper.md), [hipersoft](https://apify.com/hipersoft/grailed-scraper.md)
- Depop: [bovi](https://apify.com/bovi/depop-scraper.md), [jongoose](https://apify.com/jongoose/depop-scraper.md)
- Vinted: [jongoose](https://apify.com/jongoose/vinted-scraper.md)
- ThredUp: [crawlerbros](https://apify.com/crawlerbros/thredup-scraper.md), [logiover](https://apify.com/logiover/thredup-scraper.md), [abotapi](https://apify.com/abotapi/thredup-scraper.md), [parseforge](https://apify.com/parseforge/thredup-scraper.md)
- The RealReal: [lulzasaur](https://apify.com/lulzasaur/therealreal-scraper.md)
- Vestiaire: [solidcode](https://apify.com/solidcode/vestiairecollective-scraper.md), [studio-amba](https://apify.com/studio-amba/vestiairecollective-scraper), [bovi](https://apify.com/bovi/vestiaire-collective-scraper.md)
- Rebag: [lulzasaur](https://apify.com/lulzasaur/rebag-scraper.md), [crawlergang](https://apify.com/crawlergang/rebag-scraper.md)
- Fashionphile: [lulzasaur](https://apify.com/lulzasaur/fashionphile-scraper.md)
- GOAT: [rl1987](https://apify.com/rl1987/goat-api-scraper.md)
- StockX: [rl1987](https://apify.com/rl1987/stockx-api-scraper.md), [xtracto sales history](https://apify.com/xtracto/stockx-sales-history-scraper/api)
- Etsy: [bovi](https://apify.com/bovi/etsy-listings.md)

**Libraries**
- [pypi mercarius](https://pypi.org/project/mercarius) (2023), [pypi grailed_api](https://pypi.org/project/grailed_api) (2024)

**ToS and official docs**
- [Poshmark terms](https://poshmark.com/terms) [V], [Grailed terms](https://www.grailed.com/about/terms) [V], [Vinted terms (archived current)](https://www.vinted.com/old-terms-and-conditions) [V], [Mercari ToS](https://www.mercari.com/us/help_center/topics/account/policies/terms-of-service/) [V], [Etsy API terms](https://www.etsy.com/mx/legal/api) [V], [eBay Browse API overview](https://developer.ebay.com/api-docs/buy/browse/overview.html) [V]
- [StockX ToS via ConductAtlas](https://conductatlas.com/platform/stockx/stockx-terms-of-use/provision/CA-P-058140/prohibition-on-automated-scraping-without-permission/) [S], [GOAT ToS via ConductAtlas](https://conductatlas.com/platform/goat/goat-terms-of-use/provision/CA-P-062899/prohibition-on-automated-scraping-or-crawling-tools/) [S]
- [eBay agent ban (ValueAddedResource)](https://www.valueaddedresource.net/ebay-bans-ai-agents-updates-arbitration-user-agreement-feb-2026/), [The Register](https://www.theregister.com/2026/01/22/ebay_updates_legalese_to_ban/)
- [Etsy open-api discussion #1387](https://github.com/etsy/open-api/discussions/1387), [skills.cat etsy-api](https://skills.cat/skills/j-dturner/etsy-api-skill/etsy-api)

**Phia**
- [Digital Commerce 360 Apr 2025](https://www.digitalcommerce360.com/2025/04/28/phia-ecommerce-startup-phoebe-gates/), [DC360 Oct 2025](https://www.digitalcommerce360.com/2025/10/29/phia-co-founders-ai-resale-at-techcrunch-disrupt/), [Forbes AU Jan 2026](https://www.forbes.com.au/news/entrepreneurs/how-phoebe-gates-and-sophia-kianni-raised-35m-to-build-an-ai-shopping-unicorn/)
- [Fortune Nov 2025](https://fortune.com/2025/11/15/phia-ai-shopping-agent-bill-gates-phoebe-gates-sophia-kianni-collecting-user-data), [Marketing Brew](https://www.marketingbrew.com/stories/2025/05/02/phia-shopping-tool-Sophia-Kianni-phoebe-gates), [Kleiner Perkins](https://www.kleinerperkins.com/perspectives/phia-the-ai-shopping-agent-for-the-next-generation/)
- [cside cookie-stuffing explainer](https://cside.com/es/blog/phia-cookie-stuffing-explained), [GIGAZINE](https://gigazine.net/gsc_news/en/20260713-gates-heir-phia-cookie-stuffing/), [AI Weekly](https://aiweekly.co/alerts/phia-claimed-affiliate-sales-it-didnt-drive-bloomberg-finds), [Chrome extension listing](https://www.chromeboard.com/extension/phia-best-price-in-one-cl-ehoknmhmadiboejdbinglmbnlghnbldc)
- [Vinted US expansion (FashionUnited)](https://fashionunited.com/news/business/vinted-announces-major-us-expansion-to-address-growing-demand/2026012270176)

**Fetches that were blocked or failed:** robots.txt for poshmark.com, depop.com, mercari.com, grailed.com, vinted.com and thredup.com (permission timeout); therealreal.com/terms (client error); eBay Marketplace Insights doc pages (redirected to sign-in).
