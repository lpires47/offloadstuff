# Offers, Discovery & Shopping: Competitive Teardown

Researched 2026-10-23 for a US launch of an AI resale agent and marketplace (seller agent negotiates within a floor and cross-lists, plus a shop with camera try-on and a buyer agent).

**How sourcing is marked**
- **[O]**: official help page, newsroom or developer docs, fetched directly.
- **[P]**: trade press (TechCrunch, Retail Dive, ValueAddedResource and similar), fetched directly.
- **[3P]**: a reseller-tool blog (Vendoo, OneShop, Nifty, Crosslist). These are usually accurate but are not the platform's own words.
- **[UNVERIFIED]**: from background knowledge, or a source that was not fetched or did not confirm it. Check before relying on it.

Poshmark's support site blocks automated fetching, so every Poshmark mechanic below comes from [3P] or [P] sources.

---

## 1. Offer mechanics and auto-accept rules

| Product | How it works | Strengths / weaknesses | Source |
|---|---|---|---|
| **eBay Best Offer** | The seller turns on "Allow offers". They can set a hidden auto-accept ceiling (must be below the Buy It Now price) and a hidden auto-decline floor. Offers between the two need a manual reply. The seller has 24h to accept, counter or decline. Multiple counters are allowed, and the first buyer to accept wins. Buyers get up to 3 offers per item. The window for a buyer to answer a counteroffer went from 24h to **96h on 2026-03-24** (US/UK). Auto-responses are off when an offer adds terms, and during Sale events. An auction bid auto-declines open offers. | **S:** the hidden two-threshold band is the simplest correct automation model, and buyers never see the limits. Programmatic access exists through the APIs. **W:** it is rigid. There is no counter strategy, just accept, decline or a manual counter. There is no context on the buyer. If a Promoted Listings ad was clicked, an ad fee applies to Best Offer sales. | [O](https://www.ebay.ca/help/selling/listings/buy-now-format/add-best-offer?id=4144), [P](https://www.valueaddedresource.net/ebay-best-offers-4-day-counteroffers/) |
| **Poshmark offers + Smart Sell** | Buyers send offers, and the seller accepts, counters or declines. **Smart Sell** (testing since about June 2025): the seller sets a floor on the listing's Share page, and Poshmark auto-accepts offers at or above it and auto-counters below it. At PoshFest (2025-09-14), Poshmark announced Smart Sell for Offers to Likers, which sends an offer when someone likes the item and "keeps negotiating". It also announced raising the minimum offer sellers see from 20% to 40% of list price. | **S:** Smart Sell is the closest existing analog to our seller agent, with platform-run negotiation to a floor. **W:** it is in beta with a patchy rollout and an undisclosed counter logic. Our sources disagree on whether buyer offers expire after 24h or 48h [3P]. | [P](https://www.valueaddedresource.net/poshmark-smart-sell-automate-offers-minimum-prices/), [P](https://valueaddedresource.net/poshmark-poshfest-2025-hackathon), [3P](https://blog.vendoo.co/a-guide-to-poshmark-offers-etiquette-offering-canceling) |
| **Mercari** | Buyer offers are **binding**: on acceptance the buyer's payment method is charged automatically. The seller has 24h to respond. An offer doesn't hold the item. Reportedly the maximum discount is 25% below list [3P]. **Smart Offers** (auto-accept at or above the floor, one auto-counter at the floor) was reportedly **discontinued on 2024-11-04**. | **S:** binding offers remove flakiness. **W:** Mercari removed its automation. Its help page still described Smart Offers when ValueAddedResource checked. | [3P](https://blog.vendoo.co/how-do-you-make-an-offer-on-mercari-reseller-guide-to-mercari-offers), [P](https://valueaddedresource.net/mercari-discontinues-smart-offers-changes-promotions) |
| **Depop** | Make Offer for buyers launched in 2022, and buyers can counter. Depop reported that **over 40% of items sold via offers**, with an average 23% discount, and 62M offers made in a year (as of 2024-01). | **S:** proof that offers are the default buying path in Gen-Z resale. **W:** no seller automation is documented. | [O](https://news.depop.com/depop-community-embraces-offers-as-suite-of-negotiation-tools-expands/) |
| **Vinted** | Make an offer happens inside the chat, including for bundles. Reportedly buyers can ask for up to 40% off and sellers can send 5 private offers per day [3P]. The buyer must then click Buy. | **S:** keeping negotiation inside the conversation feels natural. **W:** offers are non-binding. No auto-accept rules are documented. | [O](https://www.vinted.co.uk/help/260), [3P](https://oneshop.com/blog/vinted-discounts) |
| **Grailed** | **Binding offers** (payment captured on acceptance) sit alongside non-binding ones. The seller has 24h to respond. Editing a listing cancels its open binding offers. | **S:** the binding/non-binding choice lets buyers signal how serious they are. **W:** no auto-accept. | [3P](https://oneshop.com/blog/grailed-offers) |
| **Vestiaire Collective** | Offers must be at least **70% of price**. The seller has 48h to accept, decline or counter. After agreement the buyer has 24h to order, and the item stays buyable by others in the meantime. The buyer fee is included in the offer. | **S:** a hard floor on lowballs, and fee-inclusive offers avoid surprises. **W:** slow, and there is no automation. | [O](https://faq.vestiairecollective.com/hc/en-us/articles/360000809218-Buyer-Making-an-Offer) |
| **StockX (bid/ask)** | Buyers place bids and sellers place asks, and a matching price executes instantly. **Smart Bidding** (iOS beta): the buyer sets a min and max, a step (default $1) and a frequency (default daily). The bid auto-raises until it matches the lowest ask or hits the max. Ties go to whoever reached the ask first. A bid expires one month after reaching the max. StockX says updated bids convert at **2x** the rate of untouched bids. | **S:** the best existing *buyer-side* auto-negotiation primitive. **W:** it needs fungible SKUs, so it doesn't map directly to one-of-a-kind used items. | [O](https://stockx.com/help/articles/what-is-smart-bidding) |
| **Whatnot** | Live auctions with a counter-bid timer, or optional "sudden death". **Max Bid** proxy-bids up to the buyer's limit. Buy It Now listings can allow offers (custom price or % off), and the seller accepts, rejects or counters. Flash sales run 50s live or about 5h on Quality BIN listings. | **S:** urgency plus proxy bidding. **W:** it needs a live host, so it doesn't scale to a closet of one-offs. | [3P](https://crosslist.com/blog/how-does-whatnot-work) |
| **The RealReal** | No buyer offers. Pricing is consignor/platform-set with markdowns. A 20-minute cart hold. | **W:** no negotiation at all. Consignment uses price drops instead. | [3P](https://www.topbubbleindex.com/blog/buying-tips-realreal/). "No offers" is [UNVERIFIED] beyond that source. |
| **Facebook Marketplace** | Haggling is free-form in Messenger. There are no structured offers or floors [UNVERIFIED]. | **W:** no structure, which is why "is this available" spam exists. | [UNVERIFIED] |

**Best in class: eBay (rules) + StockX Smart Bidding (buyer-side algorithm).**
- **Why:** eBay's hidden accept/decline band with a manual middle zone, a 3-offer cap and counteroffer timers is the cleanest seller rule set. StockX is the only platform that lets a buyer pre-authorize "raise by X every Y up to Z".
- **Borrow:** model the seller agent's floor as eBay's two thresholds, plus an "agent zone" in the middle where our agent counters instead of a human. Model the buyer agent on Smart Bidding: min, max, step and cadence, with pre-authorized payment like Mercari and Grailed binding offers so an accepted deal clears instantly.
- **Watch:** Poshmark's Smart Sell, which is the most direct incumbent threat.

---

## 2. Seller-initiated offers to interested buyers

| Product | How it works | Strengths / weaknesses | Source |
|---|---|---|---|
| **eBay Send Offers / Negotiation API** | **Who gets them:** watchers and cart holders (in cart for at least 2 days). **Discount:** at least 5% below Buy It Now for single offers, excluding shipping. Bulk offers are tiered at 5%, 3% or 2% by price band. **Reach:** a single offer goes to the 30 most recent interested buyers and lasts 96h. A bulk offer goes to 10 buyers and lasts 48h. **Automated offers:** go to 30 buyers every 48h until every interested buyer is reached. They keep their % when the price changes and pause if the price drops below the offer. Store subscribers can run Buyer Groups rules for up to 150 days. The seller can disable counters. **API:** `findEligibleItems` and `sendOfferToInterestedBuyers` take an offer duration, a price or % off, a message and a quantity, and buyer names are masked. | **S:** the most complete and the only one with an **official API**, which is what our cross-platform agent needs. Automation persists across price changes. **W:** caps on recipients, and the minimum discounts are small. | [O](https://www.ebay.ca/help/selling/listings/buy-now-format/add-best-offer?id=4144), [O](https://developer.ebay.com/api-docs/sell/static/marketing/offers-to-buyers.html), [O](https://innovation.ebayinc.com/stories/ebay-makes-it-easier-with-three-new-ways-for-sellers-to-send-offers-to-buyers/) |
| **Poshmark Offer to Likers (OTL)** | A private offer to everyone who liked the item. It must be at least 10% off, and each new OTL must be 10% below any offer from the prior 90 days. It optionally includes a discounted or free shipping upgrade, paid by the seller. It lasts 24h and can't be cancelled directly. Third-party bots auto-send on each new like, with a delay of 5 minutes to 3 hours. | **S:** the like-to-offer loop is the core resale sales motion. **W:** forced 10% steps erode price quickly, and there's no official API, so tools rely on automation. Whether Poshmark has a public API is [UNVERIFIED]. | [3P](https://blog.vendoo.co/a-guide-to-poshmark-offers-etiquette-offering-canceling), [3P](https://docs.nifty.ai/automation/automatic-offers/automatic-offers-poshmark) |
| **Mercari Offer to Likers** | Goes to the last 50 likers. It must be at least 10% below the lowest historical price and lasts 24h. | **S:** simple. **W:** a ratchet: each price can only go lower. | [3P](https://blog.vendoo.co/how-do-you-make-an-offer-on-mercari-reseller-guide-to-mercari-offers) |
| **Depop Send Offer** | The seller sends a discount to likers. Buyers have 24h to buy or counter. Sellers send about 2M offers per week. Fully rolled out in 2024-01. | **S:** buyers can counter a seller's offer, so it's a real two-way negotiation. | [O](https://news.depop.com/depop-community-embraces-offers-as-suite-of-negotiation-tools-expands/) |
| **Grailed** | Goes to the last 100 favoriters by email. It must be at least 10% below the current price, and at least 10% below any prior offer. Limits: 2 per listing, 1 per 24h, and 10 per day per account. | **W:** tight throttles. | [3P](https://oneshop.com/blog/grailed-seller-initiated-offers) |
| **Vinted** | The seller is notified of a favourite and can open a chat and send an offer. | **W:** manual, one buyer at a time. | [O](https://www.vinted.co.uk/help/267) |

**Best in class: eBay automated offers to interested buyers.**
- **Why:** the triggers are broadest (watch plus abandoned cart), the automation keeps running across price changes, and it's exposed through an official API.
- **Borrow:**
  - Interest triggers: like, save, cart abandon and dwell.
  - Rolling cohorts with a delay.
  - Offers that track the current price.
  - Masked buyer identity.
  - Depop-style counters on seller offers, run by our seller agent against the floor.
- **Avoid:** the forced 10% ratchet. Let the agent personalize discounts per buyer instead of one price drop for everyone.

---

## 3. Bundles

| Product | How it works | Strengths / weaknesses | Source |
|---|---|---|---|
| **eBay bundle discounts** | The seller sets tiered % off for 2, 3 and 4+ items (for example 10/15/20%). It's opt-in, all listings are included by default, and exclusions are allowed. Shown on listing, cart and store pages. If a buyer returns part of a bundle, the remaining items are **repriced to the tier they still qualify for** and the refund is auto-calculated. It doesn't stack with other seller discounts; the best one wins. | **S:** the most rigorous, including the returns math and visible tiers. **W:** set once per store, not per buyer. | [O](https://www.ebay.com/help/selling/selling-tools/selling-bundle-discounts?id=5842) |
| **Poshmark bundles** | The buyer adds items to a bundle and they ship in one package. The seller sets one closet-wide bundle %. The seller can **build a bundle for a liker** and send a private bundle offer, which the buyer can accept, counter or pass. | **S:** seller-built bundles for likers are a great outbound motion. **W:** one discount level only. | [3P](https://crosslist.com/blog/how-to-bundle-on-poshmark) |
| **Depop bundles** | The seller sets a % off for 2+ items and/or free shipping on bundles. A "Create Bundle" multi-select is at the top of the shop, and the shipping label is resized to the combined weight. | **S:** combined shipping math. **W:** essentially one discount level [3P]. | [3P](https://blog.vendoo.co/how-to-bundle-on-depop) |
| **Vinted bundles** | The seller sets a discount per item count. Bundles hold up to 100 items, and buyers can make an offer on the bundle. Pro sellers can't offer bundle discounts. | **S:** per-count tiers plus negotiating the bundle. | [O](https://www.vinted.com/help/422), [O](https://www.vinted.co.uk/help/260) |
| **Poshmark Posh Shows** | Sellers can merge multiple orders from one show into a single shipment, so the buyer pays shipping once (announced 2025-09). | **S:** an automatic bundle after impulse live buys. | [P](https://valueaddedresource.net/poshmark-poshfest-2025-hackathon) |

**Best in class: eBay tiers + Poshmark's "seller builds a bundle for a liker".**
- **Borrow:**
  - Tiered rules from eBay, including the partial-return repricing.
  - Have the seller agent assemble bundles from what a buyer has liked across the closet, and price them against the per-item floors.
  - Have the buyer agent propose cross-seller "virtual bundles" for an outfit. Combined shipping only works for a single seller.

---

## 4. Price-drop notifications and saved searches

| Product | How it works | Strengths / weaknesses | Source |
|---|---|---|---|
| **Mercari Promote** | A price cut of at least 5% (below the lowest price ever set, never below $1) **boosts the listing in search and notifies likers**. Up to 10 a day, once per item per 24h. The drop is permanent. | **S:** ties the seller's action to buyer reach. **W:** each promotion is a permanent cut. | [P](https://valueaddedresource.net/mercari-discontinues-smart-offers-changes-promotions) |
| **Poshmark Closet Clear Out** | A cut of at least 10% from the lowest historical price notifies the people who had liked the item before, with a **Poshmark-funded** shipping discount of about $2 for about 6h. | **S:** a platform subsidy creates urgency. **W:** limited to existing likers. | [3P](https://blog.vendoo.co/your-guide-to-a-poshmark-closet-clear-out) |
| **Vinted notifications** | Push or email for price drops on favourited items, a favourited item selling, and new items from followed members. Non-priority alerts can have a daily cap. | **S:** a clean, buyer-controlled set. **W:** no saved-search alerts are documented on that page. | [O](https://www.vinted.com/help/433) |
| **Amazon Rufus Auto Buy** | The buyer says "buy when 30% off" or sets a price alert from the price history. Rufus checks every 30 minutes and buys when the target is met. It requires an "Auto Buy" checkbox to confirm, and the buyer has 24h to cancel before shipping. Launched 2025-11 for US Prime members. | **S:** **turns an alert into a purchase**, which is a buyer agent in production. **W:** works on Amazon's catalog only. | [P](https://www.modernretail.co/technology/marketplace-briefing-amazons-shopping-bot-rufus-can-now-automatically-buy-products-for-you-when-prices-drop/) |
| **Google price tracking + agentic checkout** | The buyer tracks a price with a budget, and when it drops Google offers to buy through Google Pay, after explicit confirmation. Launched 2025-11-13 with Wayfair, Chewy, Quince and some Shopify stores. | **S:** the same alert-to-purchase loop at web scale. | [P](https://techcrunch.com/2025/11/13/google-expands-ai-shopping-with-conversational-search-agentic-checkout-and-an-ai-that-calls-stores-for-you) |
| **The RealReal Obsessions** | A wishlist that tracks price drops and items returning to stock, plus an "On Sale Now" sort. New inventory drops twice a day. First Look costs $10/mo for 24h early access. | **S:** paid early access is monetizable. | [3P](https://www.topbubbleindex.com/blog/buying-tips-realreal/) |
| **eBay saved searches / watchlist** | Saved-search alerts for new listings, and price-drop notices to watchers. | Standard, but present. | [UNVERIFIED] (no official page was fetched) |

**Best in class: Amazon Rufus Auto Buy for buyers; Mercari Promote for the seller-side loop.**
- **Borrow:**
  - A "standing order" for the buyer agent: watch for X in my size under $Y, then negotiate and buy, with a confirm box and a cancel window.
  - On the seller side, any agent price move should notify every interested buyer and boost the listing at the same time.

---

## 5. Feed, personalization and discovery

| Product | How it works | Strengths / weaknesses | Source |
|---|---|---|---|
| **Depop feed** | A personalized feed based on size, style and preferences. The model takes the user's **last 300 views**, narrows to **600 ranked listings**, and refreshes several times a day (2025-01). AI "Outfits" styles combinations from live listings (about 2025-09). | **S:** the most specific published resale recommender. Outfit framing works well for one-off items. | [O](https://www.depop.com/blog/depop-product-release-jan-2025/), [P](https://www.netguru.com/newsletter/ai-applied/depops-ai-stylist-etsys-seller-boost-targets-genai-search) |
| **Vinted Showcase** (formerly Wardrobe Spotlight) | A paid 7-day boost that features up to 15 listings to likely buyers. Each buyer sees the one item that best matches their feed or search filters. Requires at least 5 listings. Vinted says followers are 3x more likely to buy. | **S:** per-buyer matching inside a paid boost. A good monetization template. | [O](https://www.vinted.co.uk/help/452-using-wardrobe-spotlight) |
| **Poshmark sharing / Posh Party Live** | Sharing pushes listings into followers' feeds and theme parties [UNVERIFIED for ranking effects]. A daily live theme event runs at 2pm PT with 10 hosts and Host Picks, combining Posh Shows and Parties (2024-06). Posh Lens visual search, plus Apple Visual Intelligence camera search on iOS 26 (2025-09). | **S:** community curation. **W:** sharing is manual busywork that sellers automate with bots. | [P](https://www.retailtouchpoints.com/features/news-briefs/poshmark-turns-livestreams-into-community-selling-events-with-new-live-posh-parties), [P](https://valueaddedresource.net/poshmark-poshfest-2025-hackathon) |
| **Whatnot** | A "For You" feed plus category feeds. Sellers can buy placements (an hourly budget, or a 15-minute boost). A "Community Boost" lets past buyers chip in to promote a show. | **S:** a social boost mechanic. | [3P](https://crosslist.com/blog/how-does-whatnot-work) |
| **eBay** | Explore and Shop the Look (2024), plus a conversational AI shopping agent piloted with a small share of US users (2025-05). eBay is testing agentic search more broadly. | **W:** it's still a pilot. | [P](https://www.retaildive.com/news/ebay-conversational-ai-shopping-agent/747530/), [P](https://www.digitalcommerce360.com/2025/10/31/ebay-agentic-ai-commerce-openai/) |
| **Daydream** | Chat-first fashion discovery covering 8,000+ brands. Onboarding builds a "**style passport**" from price range, brands and feedback. "Say More" refines a result, image upload is supported, and items can be saved to collections. | **S:** the best onboarding for taste. **W:** new retail only, and checkout redirects to the merchant. | [P](https://techcrunch.com/2025/06/25/julie-bornsteins-daydream-is-releasing-an-ai-powered-chatbot-for-fashion-related-shopping) |
| **Google Doppl** | A try-on app with a shoppable feed of AI-generated try-on videos of real products, personalized by style (added 2025-12). | **S:** discovery delivered as try-on. | [P](https://techcrunch.com/2025/12/11/googles-ai-try-on-feature-for-clothes-now-works-with-just-a-selfie/) |
| **The RealReal** | Personalized feeds filtered by brand, size, color and price. Twice-daily drops. | **S:** scarcity cadence. | [3P](https://www.topbubbleindex.com/blog/buying-tips-realreal/) |

**Best in class: Depop's feed for resale fashion; Daydream for onboarding.**
- **Borrow:**
  - Depop's size-aware recent-views recommender and outfit assembly.
  - Daydream's style passport, seeded at signup and refined by feedback.
  - Doppl's idea: render the feed *on the buyer's avatar*. That's the camera try-on hook.
  - Vinted Showcase's per-buyer matching as the paid-boost format.

---

## 6. Messaging: canned and AI replies

| Product | How it works | Strengths / weaknesses | Source |
|---|---|---|---|
| **eBay AI Responses** | Drafts suggested replies from listing and order data, for **shipping and item-detail questions only, never price or offers**. It is never auto-sent: the seller edits and sends, and buyers see no AI label. Rolled out sitewide around 2025-08. eBay also has "Reply with offer": up to 3 custom offers per buyer, valid 48h, which can be above or below the BIN price. | **S:** safe scoping, and offers can be made from inside a message thread. **W:** the seller still reviews every reply, so time savings are modest, and the seller is liable if the AI is wrong. | [P](https://www.valueaddedresource.net/ebay-expands-ai-responses-messaging/), [O](https://www.ebay.ca/help/selling/listings/buy-now-format/add-best-offer?id=4144) |
| **Facebook Marketplace Meta AI** | Meta AI **auto-drafts and sends** replies to availability and other questions using the listing's description, price and pickup location. The seller enables, previews and edits it when listing (2026-03-12). The same launch added AI listing drafts with local price suggestions, and an AI seller-profile summary for buyers. The prefilled "Is this still available?" first message is [UNVERIFIED]. | **S:** truly autonomous, aimed at the biggest pain in local selling. **W:** stale-state risk: it can keep answering "yes" after the item sells. No negotiation. | [O](https://about.fb.com/news/2026/03/facebook-marketplace-new-meta-ai-tools-make-selling-faster-and-easier/), [P](https://www.shopifreaks.com/meta-introduces-new-ai-selling-tools-for-facebook-marketplace/) |
| **Google Business Agent** | A branded "Chat" sales associate on Search, which answers product questions in the brand's voice. Partners include **Poshmark**, Lowe's and Reebok (from 2026-01-12). Checkout and deals are coming. | **S:** brand-trained. | [P](https://9to5google.com/2026/01/11/gemini-ai-mode-checkout/) |
| **Vinted / Depop** | Chat with offers built in (Vinted). | **S:** negotiation lives inside the conversation. | [O](https://www.vinted.co.uk/help/267) |
| **Poshmark** | No direct messages; buyers and sellers talk in listing comments. Sellers asked for messaging at PoshFest 2025. | **W:** a gap. | [P](https://valueaddedresource.net/poshmark-poshfest-2025-hackathon). Exact DM status is [UNVERIFIED]. |

**Best in class: Facebook Marketplace for autonomy; eBay for safety and scoping.**
- **Borrow:**
  - Let the agent auto-send factual answers, gated on live inventory state. This avoids Facebook's stale "yes" problem, which is easy for us because we control delisting.
  - Route price questions to the negotiation engine, never to free text.
  - Use eBay's "offer inside the message" format.

---

## 7. Agentic buying, AI shopping assistants and checkout

| Product | How it works | Strengths / weaknesses | Source |
|---|---|---|---|
| **Amazon Rufus Auto Buy / Buy for Me** | Auto Buy: conditional autonomous purchase with a confirm box and a 24h cancel window (2025-11). Buy for Me: buys from third-party sites from inside the Amazon app with encrypted payment and shipping details, and the user approves the purchase (2025-02). | **S:** the clearest consent model for autonomous buying. | [P](https://www.modernretail.co/technology/marketplace-briefing-amazons-shopping-bot-rufus-can-now-automatically-buy-products-for-you-when-prices-drop/) |
| **Google AI Mode / Gemini + UCP** | Agentic checkout with price tracking (2025-11). A "Buy" button in AI Mode and Gemini with Google Pay and Wallet, where the retailer stays merchant of record (2026-01-11). The **Universal Commerce Protocol** is an open standard co-developed with Shopify, Etsy, Wayfair and Target and endorsed by Visa, Mastercard, Stripe and others. "Let Google Call" phones local stores. "Direct Offers" are sponsored deals. | **S:** an open protocol and huge distribution. Being UCP-listable is a channel for our shop. **W:** fixed-price only, with no negotiation. | [P](https://9to5google.com/2026/01/11/gemini-ai-mode-checkout/), [P](https://techcrunch.com/2025/11/13/google-expands-ai-shopping-with-conversational-search-agentic-checkout-and-an-ai-that-calls-stores-for-you) |
| **OpenAI Instant Checkout / ACP** | Launched 2025-09 with Etsy and Shopify on the Agentic Commerce Protocol, built with Stripe. **Scaled back around 2026-03** after weak uptake. ChatGPT now focuses on discovery and comparison, with merchant checkout or in-ChatGPT apps (Walmart, Target, Instacart). | **Lesson:** checkout inside a chatbot underperformed. The problems were merchant onboarding, catalog accuracy, multi-item carts and loyalty programs. | [P](https://www.retailgazette.co.uk/blog/2026/03/openai-pivots-chatgpt-shopping-strategy-after-instant-checkout-underwhelms/) |
| **Perplexity + PayPal Instant Buy** | In-chat checkout with PayPal merchants (Abercrombie, Fabletics, Newegg and others). PayPal buyer protection applies, and the merchant stays merchant of record (2025-11-25). | **S:** payments-led trust. | [O](https://newsroom.paypal-corp.com/2025-11-PayPal-and-Perplexity-Launch-Instant-Buy) |
| **eBay** | A conversational shopping agent pilot (2025-05). eBay is testing in-house and third-party agents. **The eBay user agreement (2026-01) bans "buy-for-me agents, LLM-driven bots, or any end-to-end flow that attempts to place orders without human review" unless eBay approves them.** OpenAI is cited as permitted. | **Critical constraint:** our buyer agent can't autonomously buy on eBay. The seller agent should use the official Sell APIs. | [P](https://www.shopifreaks.com/ebay-bans-unapproved-agentic-shopping-bots-from-its-platform-set-stage-for-more-partnerships/), [P](https://www.retaildive.com/news/ebay-conversational-ai-shopping-agent/747530/) |
| **Phia** | An app and browser extension agent that compares new and resale prices across 40k+ sites and 300M+ indexed secondhand items. It rates a price high, typical or fair, estimates **resale value**, and tracks price drops. About 500k users, and an $8M seed from Kleiner Perkins (2025-09). | **S:** the closest buyer-side resale agent, covering cross-market price intelligence. **W:** no negotiation and no checkout. | [P](https://www.digitalcommerce360.com/2025/04/28/phia-ecommerce-startup-phoebe-gates/), [P](https://fashionunited.uk/news/business/phia-raises-8-million-dollars-for-ai-shopping-agent/2025091984020) |
| **Daydream** | A fashion chat agent with a style passport. It takes a commission per sale and redirects to merchants for checkout. | **W:** no resale, no checkout. | [P](https://techcrunch.com/2025/06/25/julie-bornsteins-daydream-is-releasing-an-ai-powered-chatbot-for-fashion-related-shopping) |
| **Mercari Merchat AI** | A ChatGPT-powered shopping assistant (2023). | An early attempt; current status [UNVERIFIED]. | [P](https://www.retaildive.com/news/mercari-chatgpt-chatbot-merchat-artificial-intelligence-search-recommendations/648032/) |

**Best in class: Amazon Rufus Auto Buy for the consent UX; Google UCP for the protocol.**
- **White space:** none of these agents negotiates price for the buyer. Poshmark Smart Sell and eBay auto-rules negotiate only for the seller.
- **Borrow:**
  - Rufus's "condition, then confirm box, then cancel window" for buyer-agent mandates.
  - Publish the catalog through UCP and ACP so outside agents can discover our inventory.
  - Learn from OpenAI's pullback: own the checkout inside *our* marketplace, not inside someone else's chat.

---

## 8. Virtual try-on

| Product | How it works | Strengths / weaknesses | Source |
|---|---|---|---|
| **Google Search try-on** | A "try it on" icon on apparel results across the Shopping Graph, US-wide since 2025-07. Since 2025-12-11 it works from **just a selfie**: Nano Banana (Gemini 2.5 Flash Image) generates full-body images at the user's chosen size, and the user picks a default. A full-body photo or a range of models also works. | **S:** the lowest friction, at a scale of billions of SKUs. **W:** new retail SKUs only, and it can't show fit. | [P](https://techcrunch.com/2025/12/11/googles-ai-try-on-feature-for-clothes-now-works-with-just-a-selfie/), [P](https://techcrunch.com/2025/07/24/googles-new-ai-feature-lets-you-virtually-try-on-clothes) |
| **Google Doppl** | A separate app for animated try-on videos, plus a shoppable discovery feed (2025-12). | **S:** try-on as entertainment and discovery. | [P](https://techcrunch.com/2025/12/11/googles-ai-try-on-feature-for-clothes-now-works-with-just-a-selfie/) |
| **Doji** | 6 selfies and 2 full-body photos produce an avatar in about 30 minutes, using in-house diffusion models. Users can browse looks, mix tops and bottoms, and **paste any product link** to try it on. Purchases happen off-app. Invite-only; $14M raised (2025-05). | **S:** fun, social, works with any link. **W:** some avatars come out slimmer or taller than the user, there's no fit or size signal, and the slow setup is a barrier. | [P](https://techcrunch.com/2025/05/15/doji-raises-14m-to-make-virtual-try-ons-fun-through-ai-avatars) |
| **Zalando** | A 3D avatar from the shopper's own measurements, with Levi's, in 14 European countries (2024-10). More than 80k users since 2022. Jeans tests cut **returns by up to 40%**. Its AI assistant runs in all 25 markets (2024-10). | **S:** the only one with measured fit and returns data. **W:** a few SKUs, and it requires a 3D garment asset per item. | [P](https://www.retaildetail.eu/news/fashion/how-zalando-uses-ai-to-inspire-fashion-shoppers/) |
| **Resale marketplaces** (eBay, Poshmark, Depop, Vinted, Mercari) | No clothing try-on was found. | **A gap:** one-off used items have no studio or 3D assets, so image-generation try-on (Google- or Doji-style) is the only viable path. | [UNVERIFIED]: absence not exhaustively confirmed |

**Best in class: Google selfie try-on for friction; Zalando for fit and returns proof.**
- **Borrow:**
  - Google's selfie-to-full-body flow with a size picker as the onboarding.
  - Doji's paste-any-link so try-on works on cross-listed items and on looks that mix our closets with outside items.
  - Pair it with resale-specific fit data, such as seller-measured garment dimensions compared with the buyer's measurements, to target Zalando-style return reduction.
- **Note:** generative try-on of *used* items must not hide flaws. Show the original condition photos side by side.

---

## 9. Price-fairness signals for buyers

| Product | How it works | Strengths / weaknesses | Source |
|---|---|---|---|
| **Phia** | Labels a price high, typical or fair against new and resale comparables, surfaces cheaper exact matches, and shows resale value. | **S:** the only cross-market resale price-fairness signal. | [P](https://www.digitalcommerce360.com/2025/04/28/phia-ecommerce-startup-phoebe-gates/) |
| **Poshmark price suggestions + "Hot deal"** | Two suggested prices per listing: one to sell fast, one as an estimated sale price for sellers willing to wait. Listings priced at the fast price get a "hot deal" badge in search and on listings (previewed 2025-09; launch [UNVERIFIED]). | **S:** a seller tool doubles as a buyer trust badge. | [P](https://valueaddedresource.net/poshmark-poshfest-2025-hackathon) |
| **StockX** | A public bid/ask spread. Last sale and price history on product pages [UNVERIFIED: not fetched]. | **S:** market transparency for fungible SKUs. | [O](https://stockx.com/help/articles/what-is-smart-bidding) |
| **Amazon Rufus** | Shows a year of price history (reported to about 50M shoppers) and price alerts that can lead to Auto Buy. | **S:** history plus action. | [P](https://www.modernretail.co/technology/marketplace-briefing-amazons-shopping-bot-rufus-can-now-automatically-buy-products-for-you-when-prices-drop/). The "1 year / 50M" figure comes from a [ppc.land headline](https://ppc.land/amazons-rufus-now-shows-a-full-year-of-price-history-to-50m-shoppers/) [UNVERIFIED]. |
| **Facebook Marketplace** | AI price suggestion from similar *local* listings, for sellers only. | **W:** buyers don't see it. | [O](https://about.fb.com/news/2026/03/facebook-marketplace-new-meta-ai-tools-make-selling-faster-and-easier/) |
| **eBay** | Sold-listings filter and Product Research (formerly Terapeak, seller-facing). | **W:** buyers have to dig for it. | [UNVERIFIED] / [community post](https://community.ebay.co.uk/t5/Announcements/Product-Research-formerly-Terapeak-is-now-on-mobile/ba-p/7607254) |
| **Vestiaire** | No fairness signal, but a hard 70% offer floor. | | [O](https://faq.vestiairecollective.com/hc/en-us/articles/360000809218-Buyer-Making-an-Offer) |

**Best in class: Phia.**
- **Why:** it rates a price against new and resale comparables across 40k+ sites.
- **Borrow:**
  - Put a Phia-style "fair / typical / high vs N comparable sold items" badge on every listing and every agent-proposed deal.
  - Have the buyer agent explain *why* its counter is fair ("3 similar sold for $42–55 in 30 days").
  - Use Poshmark's dual price (fast vs patient) as the seller agent's floor and target presets.

---

## Cross-cutting takeaways for the build

1. **Nobody runs two-sided agent negotiation.** Seller automation exists (eBay thresholds, Poshmark Smart Sell, StockX Smart Bidding for buyers), but no platform matches a buyer agent against a seller agent inside a policy.
2. **Platform access is the constraint:**
   - **eBay:** has official APIs (Negotiation, Best Offer settings) but bans unapproved buy-side agents (2026-01).
   - **Poshmark, Mercari, Depop and Vinted:** tools like Nifty and Vendoo rely on automation without official APIs [UNVERIFIED for each], which is a terms-of-service risk for cross-listing.
3. **Offers are the main way resale sells.** On Depop, 40%+ of items sold via offers at an average 23% discount. The like-to-offer loop is the highest-leverage automation.
4. **Checkout inside chat failed for OpenAI.** Keep the transaction in our app, and expose the catalog to outside agents through UCP and ACP.
5. **Try-on on resale is unclaimed.** Selfie-based generative try-on (Google's approach) plus garment measurements is the differentiator.
