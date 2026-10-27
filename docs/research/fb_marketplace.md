# Facebook Marketplace data for a secondhand search startup: routes, law, vendors (as of 2026-10-26)

Tags: **[V]** checked against a primary source (court order, Meta developer docs, vendor doc or pricing page). **[S]** secondary source such as law-firm commentary or press. **[U]** unverified or inferred. This is research, not legal advice.

Blocked during research: facebook.com/terms, facebook.com/legal/terms/update and live Marketplace pages could not be fetched because the permission prompts timed out. **No one tested Marketplace logged-out directly.**

---

## 1. Official Meta routes

| Route | Direction | Who qualifies | Use for us? |
|---|---|---|---|
| **Marketplace Partnership Program** (Product Item API, Seller API) | **Inbound only.** Partners "upload, update, or delete products/sellers" so the listings appear in Marketplace search and feed. [V] [Meta docs](https://developers.secure.facebook.com/docs/marketplace/partnerships/) | "Eligible third-party partners." The EEA criteria cover C2C classifieds services with mostly consumer sellers. Applicants use an interest form, Meta charges per click after a free period, and buyers click out to the partner. [S] [VAR, Feb 2025](https://valueaddedresource.net/meta-expands-eu-facebook-marketplace-partnership). No public US criteria. [S] | It gives no read or search access. Worth applying later as a *supply* partner, if we ever host inventory. |
| **eBay → Marketplace** (Jan 2025: US, DE, FR) | Inbound. eBay listings show on Marketplace and checkout happens on eBay. [S] [Shopifreaks](https://www.shopifreaks.com/ebay-partners-with-facebook-marketplace-to-display-listings/) | eBay only | It means part of the "Marketplace" inventory is eBay inventory, which we can get legitimately through eBay's own APIs. [U] |
| **Facebook Affiliate Partnerships** (Mar 2026) | Creators tag Amazon (live), eBay or Temu (coming) products in posts and earn commission. [S] [DC360](https://www.digitalcommerce360.com/2026/03/27/meta-adds-ebay-growing-affiliate-commerce-program/) | Creators | Not tied to Marketplace C2C listings, and there's no data access. |
| **Commerce Platform / Catalog API** | Inbound. Merchants sync catalogs to Shops and ads. [U] (well known, not re-verified) | Businesses | No search access to C2C listings. |
| **Meta Content Library + API** | **Read/search.** It *does* include Marketplace listings: keyword, category, country, price min/max (single country), date and sort, with media in a secure environment. [V] [MCL docs](https://developers.facebook.com/docs/content-library-and-api/content-library), [Marketplace guide](https://developers.facebook.com/docs/content-library-and-api/content-library-api/guides/fb-marketplace) | **Researchers at not-for-profit academic or research institutions only.** CASD reviews applications, and use falls under the Research Tools Terms. [V] [Get access](https://developers.facebook.com/docs/content-library-and-api/get-access) | **Not available to a for-profit startup.** It's useful only as evidence that Meta *can* expose Marketplace search when it chooses. |
| **Automated Data Collection permission** | Meta's ADC page says programmatic access outside its platform APIs needs "prior written permission," which you request through developer support. [V] [ADC page](https://developers.facebook.com/docs/development/terms-and-policies/automated-data-collection/) | Anyone can ask | **It's a low-probability ask, but it's the only "clean" route to automated access.** Worth one BD attempt. |

**No public API gives a commercial third party Marketplace search.** [V] for the routes checked above. [U] that nothing private exists.

## 2. Legal landscape

**Meta v. Bright Data, No. 23-cv-00077-EMC (N.D. Cal. Jan. 23, 2024), Dkt. 181** [V] [order PDF](https://ia904708.us.archive.org/2/items/gov.uscourts.cand.406956/gov.uscourts.cand.406956.181.0.pdf)
- The court granted Bright Data summary judgment on breach of contract. Meta's Facebook and Instagram Terms "only prohibit logged-in scraping, and not logged-off scraping" (p. 19). "Use" means "action taken by logged-in users" (p. 21). The Terms "do not apply to… scraping of publicly available data while logged off" (p. 25).
- "Mere visitors without a Facebook or Instagram account do not see the Terms" (p. 19). Bright Data held accounts, but they were "wholly incidental" to the scraping (p. 25).
- The survival clause doesn't reach "logged-off, post-termination scraping unrelated to pre-termination breaches" (p. 34). The sale ban could cover data "obtained while the user was logged in" (p. 24).
- Meta "left the gate open" by not putting content behind a password, and defeating CAPTCHAs or anti-bot measures was not enough on its own (pp. 11–12). The court said Meta knew how to cover logged-off users, citing an old 2009 "whether or not you are a registered member" clause (p. 20).
- **Outcome:** Meta stipulated to dismissal in Feb 2024, **waived its appeal** and dropped the remaining tortious-interference claim. [S] [Goldman blog](https://blog.ericgoldman.org/archives/2024/02/facebook-drops-anti-scraping-lawsuit-against-bright-data-guest-blog-post.htm), [TechCrunch](https://techcrunch.com/2024/02/26/meta-drops-lawsuit-against-web-scraping-firm-bright-data-that-sold-millions-of-instagram-records). **This is a district court ruling, not binding precedent.**

**Meta's terms after Bright Data**
- Meta's ADC developer page quotes ToS §3.2.3 as barring automated collection without permission "**regardless of whether such automated access or collection is undertaken while logged-in to a Facebook account**." [V] [ADC page](https://developers.facebook.com/documentation/development/terms-and-policies/automated-data-collection.md) That phrase does **not** appear in the Bright Data order [V]. The date it was added is [U].
- A third-party tracker shows the current Terms (dated Jan 1, 2025) require compliance with separate "Automated Data Collection Terms" and say Meta "may restrict or revoke our permission at any time." [S] [ConductAtlas](https://conductatlas.com/platform/meta/meta-terms-of-service/automated-data-collection-restrictions/)
- **Implication:** the terms now try to reach logged-off collection *by account holders*. Under Bright Data's reasoning this still shouldn't bind true non-account visitors, but **a company or founders with Facebook accounts are exposed if their accounts are linked to the scraping.** [U] Counsel issue.
- The Oct 2026 "commercial terms" controversy concerns Meta crawling business websites, not third-party scraping of Meta. [S] [SMT](https://socialmediatoday.com/news/meta-updates-terms-of-service-amid-concerns-around-data-scraping/833305)

**Other cases**
- **Meta v. BrandTotal** (N.D. Cal. May 2024): a browser-extension "panel" company that collected data from users' *logged-in* sessions **breached §3.2.3**. Continuing after Meta revoked access violated the **CFAA and CDAFA**. BrandTotal won on non-password-protected pages. [S] [Courthouse News](https://www.courthousenews.com/judge-rules-brandtotals-data-harvesting-violates-metas-terms-of-use-and-anti-hacking-laws/) **This is the most relevant precedent for extension or agent approaches.**
- **X Corp v. Bright Data** (N.D. Cal., Alsup): in May 2024 the court dismissed X's claims. Contract claims over public data were **preempted by the Copyright Act**, with no damages shown. [S] [MediaPost](https://www.mediapost.com:443/publications/article/395944/judge-throws-out-xs-claims-against-data-scraper.html). In Nov 2024 the court revived **server-burden** theories (trespass to chattels, access-based contract, fraud UCL). [S] [Goldman blog](https://blog.ericgoldman.org/archives/2025/01/catching-up-on-the-heavyweight-scraping-battle-between-x-and-bright-data-guest-blog-post.htm). The case **settled June 2025 on confidential terms.** [S] [Bloomberg Law](https://news.bloomberglaw.com/ip-law/musks-x-settles-data-scraping-dispute-against-israeli-data-firm)
- **hiQ v. LinkedIn:** the Ninth Circuit said scraping public data likely isn't a CFAA violation. But in Nov 2022 LinkedIn won on **breach of contract** (hiQ was a registered user and used fake "turker" accounts). The consent judgment included a permanent injunction, data deletion and **$500k**. [S] [ZwillGen](https://www.zwillgen.com/alternative-data/hiq-v-linkedin-wrapped-up-web-scraping-lessons-learned/)
- **Van Buren v. US (2021):** the CFAA "gates-up-or-down" test means public pages don't involve "exceeding authorized access." [U] (well known, not re-fetched)
- **New 2026 theory, DMCA §1201 anti-circumvention against scrapers.** *Google v. SerpApi* (N.D. Cal.) mostly dismissed Google's claims in Jul 2026, but an amended complaint is pending. *Reddit v. SerpApi/Perplexity/Oxylabs* (S.D.N.Y.): §1201(a)(1) and conspiracy claims **survived** dismissal on Jul 31, 2026. [S] [Parallel summary](https://parallel.ai/articles/is-scraping-google-legal.md), [KuCoin/news](https://www.kucoin.com/news/flash/reddit-lawsuit-against-serpapi-survives-dismissal-motion). **Buying from a vendor that defeats anti-bot controls is a live risk (the conspiracy theory).**
- No 2025–26 Meta lawsuit against a logged-off scraper was found. [U]

**Privacy (CCPA/CPRA)**
- "Publicly available" now includes information the consumer made available to the general public and didn't restrict to a specific audience. That likely covers public listings, but it's untested for scraped seller names and profile IDs. [S] [TrueVault](https://www.truevault.com/learn/what-is-publicly-available-information-under-the-ccpa)
- Vendor feeds include `profile_id` and `seller_description`. [V] [Bright Data docs](https://docs.brightdata.com/api-reference/scrapers/social-media-apis/facebook-marketplace-collect-by-url)
- **Minimize:** don't store seller names, IDs or exact locations. Keep only the item, price, city-level location, a thumbnail and the outbound link, and use a short retention period.
- Displaying sellers' photos carries **copyright** risk (users own them). Prefer thumbnails and links. [U]

## 3. What Marketplace shows logged-out (US)

The evidence conflicts, so it **must be tested in-house before relying on it**.
- **Oct 23, 2026:** Scrapfly says Marketplace search returns listings logged-out behind a dismissible sign-in modal. Fields include ID, title, city/state, sold/pending status, image and delivery type. **Price is often missing in search results** and comes from the item page. Seller appears only sometimes. [S] [Scrapfly](https://scrapfly.io/blog/posts/how-to-scrape-facebook)
- **Oct 2026 (verified Jul 2026):** an open-source maintainer reports the search path "hard-redirects anonymous, cookie-less visitors to a login page." Most DIY tools now need a session. [S] [Scrapfly GitHub roundup](https://scrapfly.io/blog/posts/best-facebook-marketplace-scrapers-github)
- Several Apify actors advertise "no login" guest sessions but note **fewer results than authenticated sessions**. [S] [crawloop actor](https://apify.com/crawloop/facebook-marketplace-scraper.md), [flipper_ai](https://apify.com/flipper_ai/fb-marketplace-deals-scraper.md)
- Messaging, saving searches and alerts require login. [S] [How-To Geek](https://www.howtogeek.com/887438/you-can-browse-facebook-marketplace-without-an-account/)
- **Working assumption:** logged-out access is partial, rate-limited and changes often. Expect Meta to tighten it at any time, and if it puts Marketplace fully behind login, Bright Data's "open gate" reasoning stops applying. [U]

## 4. Data vendors

| Vendor | Marketplace product | Fields / freshness | Price | Posture |
|---|---|---|---|---|
| **Bright Data** | Dataset, plus a Scraper API with collect-by-listing-URL, discover by search or category URL, and by keyword. [V] [docs](https://docs.brightdata.com/api-reference/scrapers/social-media-apis/facebook-marketplace-discover-by-url.md), [product](https://brightdata.com/products/web-scraper/facebook/marketplace) | Title, initial/final price, condition, description, location, images/videos, brand, color, `profile_id`, `seller_description`, listing date. The dataset holds about 28.9M records refreshed monthly (daily or weekly custom). The API is described as "real-time." [V] [dataset](https://brightdata.com/products/datasets/facebook/marketplace) | API: 5k records/month free, then $1.50 per 1k PAYG, or $499/month for 384k records. Dataset: $250 minimum, $2.50 per 1k. [V] | Claims "only publicly available data" and GDPR/CCPA compliance. [V] It won against Meta and settled with X. **It's the most defensible vendor**, but it's still not Meta-authorized. |
| **Apify** (official `apify/facebook-marketplace-scraper` plus many community actors) | Input is a location, category or search URL. [V] [actor](https://apify.com/apify/facebook-marketplace-scraper) | Title, price, location, photo, **seller details**, sold/pending status, delivery. Runs are scheduled, not a live API. | About $2.60–$6.20 per 1k listings (page figures conflict). [V] | Disclaims private data and tells users to consult a lawyer. [V] Community actors vary in quality. |
| **ScrapeCreators** | Unofficial REST API: location search, Marketplace search, item. [V] [page](https://scrapecreators.com/facebookMarketplace-api) | Real-time per call | Credits: 1 per call, 100 free. [S] [blog](https://scrapecreators.com/blog/facebook-marketplace-api-tools) | Calls itself "unofficial." It's small, and its terms weren't reviewed. |
| **Scrapfly** | Managed API with logged-out search. [S] | As in §3 | n/a | Vendor's own claims |
| **Oxylabs / Zyte / Nimble** | No Marketplace-specific product found. Their general unblockers would require us to do the scraping ourselves. [V for Nimble page](https://nimbleway.com/nimble-api/web/facebook) | n/a | n/a | **Oxylabs is a defendant in Reddit's §1201 suit.** [S] |
| **Data Axle** | No Marketplace offering found. [U] | | | |

## 5. User-authorized approaches

- **An agent driving the shopper's own logged-in session (server-side or cloud browser) is high risk.** It's exactly "automated means" by a logged-in user, the conduct Bright Data said the Terms *do* cover [V]. BrandTotal shows breach plus CFAA/CDAFA liability once Meta revokes access [S]. Users also risk account or Marketplace restrictions, since Meta flags "not a genuine user" behavior [S] [Pixelscan](https://pixelscan.net/blog/marketplace-isnt-available-to-you-fix/). **Avoid.**
- **Browser extension that reads only the page the user is viewing, on demand** (for example, "find this cheaper elsewhere" on a Marketplace item page): lower risk, but **not zero**. BrandTotal's extension was a *panel* that collected data passively at scale and sent it to a server [S]. One small extension already does this: "Marketplace Deal Checker" reads FB listing titles and prices and compares them with eBay sold listings (18 users) [S] [ChromeBoard](https://chromeboard.com/extension/marketplace-deal-checker-gjfnpjkegknjchdhbegfpjllndkbppic).
  - **Design rules:** user-initiated only, no background crawling or pagination, and process locally. Send only the item title, price and photo needed for the comparison query. Never send seller identity, and keep no central database of FB listings.
- **Phia's extension** works on product pages and compares against "150+" secondhand platforms. **No evidence Phia covers FB Marketplace.** [S] [TechCrunch](https://techcrunch.com/2025/10/29/phias-founders-on-how-ai-is-changing-online-shopping/?rand=23331), [Gizmodo](https://gizmodo.com/download/phia)

## 6. Zero-risk fallback: deep links

- **Base format:** `https://www.facebook.com/marketplace/<city-slug>/search/?query=<urlencoded>` (for example `/marketplace/sanfrancisco/search/?query=crane`). [V] (format documented by Apify)
- **Filter parameters, all [U] (names match scraper inputs; test them):** `minPrice`, `maxPrice`, `daysSinceListed=1|7|30`, `sortBy=best_match|creation_time_descend|price_ascend|price_descend|distance_ascend`, `itemCondition=new,used_like_new,used_good,used_fair`, `exact=false`, `radius` (km). [S] [crawloop actor](https://apify.com/crawloop/facebook-marketplace-scraper.md)
- **Opening the app:** on mobile, a facebook.com Marketplace URL typically universal-links into the FB app when it's installed. [U]
- **UX:** show a "Search Facebook Marketplace for *<query>* near *<city>*, $X–$Y" card next to our own results, so the user's own browser or app does the search. **No data touches our servers.**

## 7. How competitors do it (reported)

- **Swoopa** (vehicle- and reseller-focused) "scans Facebook Marketplace continuously." Its method isn't disclosed, and alerts arrive 10–30 minutes after posting. [S] [mwm.ai](https://mwm.ai/apps/swoopa/6475300269)
- **Flipify** uses "cloud-based bots" for FB, eBay, Craigslist, OfferUp, Kijiji and Vinted, and mentions "Facebook auto-messaging," which suggests account automation. [S] [App Store](https://apps.apple.com/app/id6504143452)
- **Encore** covers Poshmark, The RealReal, Grailed, Etsy and eBay. No FB was mentioned, and it's affiliate-funded. [S] [TechCrunch 2024](https://techcrunch.com/2024/11/10/encore-is-an-ai-powered-search-engine-for-your-thrifting-needs)
- **Phia:** see §5. Kiwi: nothing found. [U]
- **Pattern:** reseller alert tools appear to scrape (sometimes through accounts) and accept the ToS risk. Consumer fashion-search players appear to **skip FB Marketplace**. [U]

---

## Recommended tiered plan

**Ship now (no FB data on our servers)**
1. Deep-link cards to Marketplace search with query, city and price (§6).
2. Cover the "Marketplace-adjacent" supply through licensed or official APIs: eBay (whose listings already syndicate to Marketplace), plus Poshmark, Mercari and similar via affiliate or partner feeds.
3. Optionally, an on-demand extension or share-sheet flow: a user viewing an FB item taps "compare," and we run *our* search using the title and photo. This is user-initiated, single page, with no seller data and no storage.

**Pursue**
4. A BD request to Meta for Automated Data Collection permission or a Marketplace data partnership. Pitch: we send buyers *to* Marketplace and are deep-link only.
5. Monitor the Marketplace Partnership Program for US read or partner terms, and join as a supply partner if we ever list inventory.
6. A **controlled pilot** with Bright Data's Scraper API (discover-by-search-URL, logged-off, with their compliance review), for item matching only.
   - Prerequisites: counsel sign-off; storage stripped of seller fields; short retention; show only a thumbnail, price, city and a link back to FB.
   - Keep it behind a kill switch.

**Avoid**
- Agents driving users' logged-in FB sessions, or any scraping using our own or our founders' FB accounts (BrandTotal, hiQ).
- Fake accounts, CAPTCHA or anti-bot circumvention, and vendors marketed on "bypassing" Meta (Reddit §1201 conspiracy theory).
- Building a persistent mirror of FB listings, storing seller identities, or re-hosting full-size photos.
- Continuing any collection after a Meta cease-and-desist or block, which is where the CFAA/CDAFA risk activates (BrandTotal).

**Counsel must confirm**
- Whether the current ToS §3.2.3 "regardless of whether … logged-in" language and the separate Automated Data Collection Terms bind *us* through company or founder FB or Meta Business accounts (ads, Pages), and whether we should keep scraping-related operations separated from those accounts.
- Vendor contract terms: indemnity, a representation of logged-off and no-circumvention collection, and Bright Data's AUP and KYC.
- The DMCA §1201 status after *Google v. SerpApi* (hearing Oct 13, 2026) and *Reddit v. SerpApi*.
- CCPA and state-privacy treatment of seller names, IDs and locations; copyright and fair-use exposure for displaying listing photos.
- Extension design against the BrandTotal facts, plus Chrome Web Store policy.
