# Trust & Transactions: how resale marketplaces handle payments, shipping, protection, authentication, scams

Research date: 2026-10-23. Scope: US launch, EU later. Built for an AI resale agent that lists across eBay / Depop / Vinted / Poshmark / FB Marketplace plus our own shop, which will later run its own checkout.

**Labels used below**
- **[O]** comes from an official help, policy or docs page that I fetched.
- **[TP]** comes from trade press I fetched, such as Value Added Resource, TechCrunch, FashionUnited or the FTC consumer blog.
- **[3P]** comes from a third-party seller blog (Vendoo, Crosslist, Nifty, Underpriced, Closo, OneShop). Treat these as likely but unconfirmed.
- **[U]** is unverified: from memory, or I couldn't open the source. Check it before relying on it.

**Research limits:** these official help centers blocked fetching: Poshmark support, Mercari help (except two articles), Facebook Help, Whatnot help, and Depop help search. The shared web-search budget also ran out near the end, so the Whatnot, Depop-payout and Facebook rows lean on [3P] sources and [U] notes.

---

## 1. When the seller gets paid

| Product | How it works | Strengths / weaknesses | Source |
|---|---|---|---|
| eBay | Proceeds are "processing," then usually available in 1–2 days unless a hold applies. Daily payout is the default. Weekly, biweekly and monthly payouts go out on Tuesdays. Banks take 1–3 business days. Express payout takes about 30 minutes for a flat $2. **[O]** | Fast for established sellers, with clear schedule options. Holds for risky sellers are stacked on top (see section 2). | https://www.ebay.com/help/fees-billing/payouts-payments-paid/get-paid-managed-payments-seller?id=4814 |
| Poshmark | Funds are released when the buyer taps "accept," or automatically 3 days (72 hours) after delivery if no case is opened. After release, "all sales are final." **[O]** Payout methods: direct deposit is free and takes 1–3 business days; Instant Transfer costs $2 (up to $1k/day); Venmo or PayPal costs $0.35. **[3P]** | Simple, and the buyer-accept step closes the dispute window cleanly. The seller waits about 5–10 days in total. | https://poshmark.com/posh_protect ; https://blog.vendoo.co/how-to-get-paid-on-poshmark |
| Mercari | Mercari holds payment until delivery plus the buyer's rating. If the buyer doesn't rate within 72 hours of carrier-confirmed delivery, the order auto-completes and the seller is paid. **[O]** Withdrawal: bank transfer is free and takes up to 5 business days; Instant Pay costs $3 (limit $600/month). **[3P]** A September auto-rating outage stalled payouts. **[TP]** | Same rating-gated model as Poshmark. It depends on one fragile automated job. | https://www.mercari.com/help_center/article/235 ; https://crosslist.com/blog/mercari-seller-fees ; https://www.valueaddedresource.net/mercari-us-outage-problems-automated-ratings/ |
| Depop | Payments run through Depop Payments (Stripe) or PayPal. From **September 2026**, US sellers can keep proceeds in a Stripe-backed "Depop Balance." **[O]** In 2024 there were weeks-long automated payout failures. **[TP]** I couldn't confirm exact payout timing or delivery gating. **[U]** | Stripe-native, which is close to what we'd build. History of payout reliability problems. | https://depophelp.zendesk.com/hc/en-gb/articles/360001773148 (ToS) ; https://techcrunch.com/2024/03/13/depop-sellers-faced-ongoing-payment-delays-due-to-tech-issue-company-admits |
| Vinted | Escrow-style. Funds are pending until the buyer taps "Everything is OK," or automatically 2 days after Vinted's "should have arrived" notice. Pro sellers wait 14 days (EU right of withdrawal) with no early-OK button. After completion, payment reaches the seller within 2 days. **[O]** | Cleanest model: a short, explicit window that sits right next to buyer protection. The Pro variant already handles EU consumer law. | https://www.vinted.co.uk/help/460-pending-balance ; https://www.vinted.co.uk/help/1268 |
| FB Marketplace | Checkout payouts are withheld, and refunds are taken from the withheld payout. **[3P]** I couldn't confirm the exact schedule. **[U]** | Opaque. | https://oneshop.com/blog/facebook-marketplace-purchase-protection |
| Grailed | Moving to Grailed Payments on Stripe. Fee is 3.49% + $0.49, matching PayPal. **[3P]** No timing found. **[U]** | — | https://listperfectly.com/selling/what-is-grailed-payments/ |
| StockX | Standard sellers are paid after the item **passes verification**. Early Seller Payout was dropped for non-Flex sales on 2026-03-01. Flex (pre-verified inventory in StockX's warehouse) pays almost immediately. **[O]** | Payment is gated on authentication. Pre-verified inventory earns instant pay. | https://stockx.com/news/en-us/updates-to-the-stockx-seller-program/ |
| GOAT | Earnings become available to cash out once GOAT has authenticated the item, usually 1–2 business days after it arrives. **[O]** Cash-out fee is about $5. **[3P]** | Same model as StockX. | https://support.goat.com/hc/en-us/articles/360015785072--How-long-does-the-verification-process-take- |
| Vestiaire | Authenticated route: paid the next business day after the check, arriving within 5 business days. Direct-ship route: the sale completes 72 hours after delivery or on buyer acceptance. **[3P]** | Two paths, chosen by price and region. | https://www.underpriced.app/blog/vestiaire-collective-selling-guide-2026 |
| The RealReal | Consignment. The consignor is paid a commission (20–70% by price and tier) when the item sells, by site credit, check or direct deposit. **[O]** | The seller does nothing but waits for the sale. | https://resources.therealreal.com/how-to-sell-on-the-real-real/ |
| Whatnot | Funds reach the balance about 4 hours after carrier-confirmed delivery (US/CA). Outside North America it's 96 hours after delivery. Early Payout at label creation for top sellers: $100k lifetime sales or 1,000 orders, 10 shows, and a 4.8+ rating. **[3P]** | The fastest delivery-gated payout. A clear reward for trusted sellers. | https://www.nifty.ai/post/whatnot-fees |

**Best in class: Vinted's confirm-or-auto-release, with Whatnot/eBay-style speed-ups for trusted sellers.** Release funds when the buyer confirms, or automatically 48–72 hours after delivery. That one timer doubles as the buyer-protection window, so it's easy to explain. *Borrow:* a single "order completes" state machine (delivered, then a 48–72h window or buyer OK, then available). Add an "early payout at label scan" tier for proven sellers.

---

## 2. Holds for new or risky sellers

| Product | How it works | Strengths / weaknesses | Source |
|---|---|---|---|
| eBay | The most explicit published table. **[O]**<br>New private sellers: released 2 days after delivery with an eBay label, 7 days with a third-party label, 31 days with no tracking.<br>New business sellers: 24 hours after delivery with an eBay label, 15 days otherwise.<br>Occasional sellers: 24 hours after delivery.<br>High-priced items: about 31 days.<br>After a suspension: holds apply for 30 days.<br>Faster funds unlock at ≥10 sales, ≥$150 total, and ≤2 defects or cases in 12 months.<br>Payments ToS (Dec 2024 / Feb 2025) allows release only after delivery "for some sellers." **[TP]** | Transparent, and it rewards using the platform's label and tracking. Sellers report it as complex and inconsistent. | https://www.ebay.com/help/selling/getting-paid/getting-paid-items-youve-sold/payments-hold?id=4816 ; https://www.valueaddedresource.net/ebay-us-funds-held-until-after-delivery-for-some-sellers/ |
| Poshmark / Mercari / Vinted | No separate new-seller hold found. Every order is already delivery- and confirmation-gated. **[U]** Mercari has a **$2,000 listing/purchase cap**, rising to $5,000 for authenticated items after SSN and ID verification, because Mercari is a regulated Money Service Business. **[O]** | Delivery gating replaces tiered holds. Mercari uses a price cap plus KYC as its risk lever. | https://mercari.com/us/help_center/article/515 |
| Depop | May withhold amounts for up to 180 days after a suspension. **[O]** | Long tail after a suspension. | Depop ToS (above) |
| Stripe Connect (our rails) | Stripe recommends delaying payouts to new businesses for a set period, e.g. **2 weeks**, and requiring **Stripe Identity** before granting faster payouts. Manual payouts can hold funds up to **2 years for US** accounts and **90 days for most other countries, including the EU**. Stripe says plainly that it "doesn't provide escrow." **[O]** | Gives us every tool to copy eBay's tiers. The EU 90-day cap matters for long return windows. | https://docs.stripe.com/connect/marketplace/tasks/refunds-disputes ; https://docs.stripe.com/connect/manual-payouts |

**Best in class: eBay's tier table.** It's keyed on label type, tracking and track record. *Borrow:* default new sellers to "delivery + 2 days," shorten that for platform labels, and use 31 days only for untracked or high-value orders. Graduate sellers automatically, e.g. after 10 sales, $150 and a clean record. Our agent generates the label, so almost every order will be tracked, and the fast tier becomes the default.

---

## 3. Shipping label model, who pays, weight tiers

| Product | How it works | Strengths / weaknesses | Source |
|---|---|---|---|
| Poshmark | One prepaid label for everything. The buyer pays a flat **$6.49** for up to 5 lb (USPS Ground Advantage since September 2025; it was $8.27 on Priority). The seller pays upgrades: 5–10 lb $5, 10–15 lb $10 (15 lb max). **From 2026-10-26** the seller is charged automatically if they ship overweight without upgrading: $5, $10, $15 for 15–25 lb, or full USPS cost over 25 lb. From 2026-10-19 sellers also pay the full $50 USPS hazmat penalty. **[TP]** | Very simple for buyers. Subsidized shipping became a cost problem, so Poshmark is pushing overweight costs back to sellers. | https://www.valueaddedresource.net/poshmark-new-shipping-rates-heavier-items/ ; https://www.valueaddedresource.net/poshmark-ends-overweight-shipping-protection/ |
| Mercari | Prepaid USPS or UPS labels bought in the app, with tiers by weight and box size: envelope up to 3 oz, about 2 lb, about 10 lb, about 20 lb (UPS). The seller toggles who pays at listing. Ship-on-your-own is allowed but loses shipping protection. **[3P]** | Flexible, but there are more choices to make. Protection only covers Mercari labels. | https://blog.vendoo.co/mercari-shipping |
| Depop | Prepaid USPS label in size tiers, re-priced mid-2026: **XS/S/M $1.99 (<1 lb), L $3.99 (<2 lb), XL $5.99 (≤10 lb)**. The buyer usually pays, or the seller offers free shipping. QR code drop-off at USPS. **[3P]** | Cheapest tiers for apparel. Probably subsidized. | https://www.nifty.ai/post/depop-shipping-prices |
| Vinted | The buyer always pays shipping on "Buy now." Vinted generates a prepaid label, or the seller can use custom shipping, paid upfront and reimbursed later. US uses **SpeedX via Vinted Go** shops and pick-up points, with QR or barcode handover. The EU has lockers and pick-up points. Lost or damaged parcels are compensated if packed properly. **[O]** Sellers must ship within 5 days. **[3P]** | The buyer pays, so the seller's price is clean. The pick-up and locker network cuts cost and fraud. US network coverage is unverified. | https://www.vinted.com/help/458 ; https://www.vinted.com/help/1549 |
| FB Marketplace | Prepaid labels were dropped for new listings on 2025-02-24, then restored in September 2025 for "select" sellers only. Access is revoked for repeated weight or size mismatches; the USPS box limit is 12x12x12 in. **[TP]** | Unstable policy. Shows how much carrier adjustment fraud and abuse costs. | https://valueaddedresource.net/facebook-marketplace-ends-pre-paid-shipping |
| eBay | eBay labels (discounted). The seller sets the shipping charge. The Authenticity Guarantee sneaker flow uses a free prepaid FedEx label to the authenticator, and the buyer pays $14.95. **[O]** Using an eBay label earns seller protection (section 5). | Labels act as both a trust signal and a hold reducer. | eBay AG page (section 6) |
| Shippo (API) | 30 free labels a month, then **$0.07/label**. Tracking costs $0.02, US address validation $0.02, insurance 1.25% of value. "Marketplaces & Platforms" plan is custom. **[O]** Pay-on-scan return labels. **[U]** | Cheap to start, with a platform plan. | https://goshippo.com/pricing/api |
| EasyPost (API) | Free up to 3,000 labels, then a per-label fee. Insurance is 1% (minimum $1). "Forge" is for platforms, contact sales. **[O]** A 3% fee on USPS spend via PC Postage from 2026-06-01, per a Shippo (competitor) blog. **[TP, biased]** | Strong address validation. Check the USPS fee. | https://www.easypost.com/pricing ; https://goshippo.com/blog/what-easyposts-new-3-fee-means-for-your-usps-shipping-costs |

**Best in class: Vinted's buyer-pays, platform-generated label tied to the order, with Depop-style size tiers.** *Borrow:* the buyer pays shipping by size tier (XS–XL), and the platform label is the only way to get protection. Pass carrier weight adjustments back to the seller, as Poshmark now does. Our agent can **estimate weight and size from photos and the category**, which cuts adjustments: a real differentiator. Use Shippo's or EasyPost's platform plans to generate labels.

---

## 4. Buyer protection window and claims

| Product | How it works | Strengths / weaknesses | Source |
|---|---|---|---|
| eBay Money Back Guarantee | Item not received (INR): report after the estimated delivery date, up to 30 days. Not as described (INAD): 30 days from delivery, or longer if the seller's return policy allows. 3-day windows for cards, coins and bullion if the seller accepts no returns. The seller has 3 business days to respond. eBay can step in from day 3. Off-eBay payment is excluded. **[O]** | The broadest protection and the most buyer trust. It's also the main channel for not-as-described abuse, and it's slow. | https://www.ebay.com/help/policies/ebay-money-back-guarantee-policy/ebay-money-back-guarantee-policy?id=4210 |
| Posh Protect | 72 hours from delivery to open a case in the app, with photos. Covers not-as-described, damage, wrong or missing item, counterfeit, and never shipped. Doesn't cover fit or buyer's remorse. Return ships within 5 days of approval. **[O]** | Short and clear, and tied to payout. Buyers who miss the window lose out. | https://poshmark.com/posh_protect |
| Mercari Buyer Protection | 72 hours after delivery. The buyer pays a **3.6% fee**. Free return label if approved. Return ships within 3 days. **[O]** | Monetized protection, paid by the buyer. | https://www.mercari.com/help_center/article/235 |
| Vinted Buyer Protection | 2 days after the delivery notice (14 days for Pro sellers). "I have an issue" suspends the order. The buyer pays a mandatory Buyer Protection fee: UK "Vinted fee" 3–8% plus £0.30–0.80 **[O]**; US 5% + $0.70 **[3P]**. Free for sellers. | Protection is the business model: sellers pay nothing. | https://www.vinted.co.uk/pricelist ; https://exportyourstore.com/blog/vinted-us |
| Depop | Buyers in the US, UK and AU pay a marketplace fee (US up to 5% + $1 since July 2024), and the 10% seller fee was removed. **[O]** Purchase Protection details are unconfirmed. **[U]** | Same fee shift as Vinted. | https://blog.depop.com/articles/us-depop-fee-change |
| FB Purchase Protection | Only for shield-badged items bought through onsite checkout. 45 days from delivery; 60 for unauthorized purchases. Excludes local pickup, items ≥$2,000, vehicles and collectibles. The seller has 10 days to respond and one appeal. **[3P]** | Long window, but it doesn't cover local deals, which are most FB sales. | https://oneshop.com/blog/facebook-marketplace-purchase-protection |
| Grailed | 3 calendar days from receipt. Covers counterfeit, materially different, or wrong item. "Only applies to buyers." **[O]** | Short window. | https://support.grailed.com/hc/en-us/articles/30282097906189-Grailed-s-Purchase-Protection |
| StockX / GOAT | Every item is verified before the buyer receives it, so there are few post-delivery claims. **[O]** | Protection happens before delivery. | sections 1 and 6 |

**Best in class: Vinted / Posh / Mercari's short window that equals the payout window, paid for by a buyer fee.** Add eBay's clear step-in timelines on top. *Borrow:* a 72-hour, in-app, photo-required claim flow. Charge buyers a protection fee of about 3.6–5% plus a fixed amount, as Vinted, Mercari and Depop do, so we can keep seller fees low. For EU later, apply the 14-day Pro-seller window to business sellers.

---

## 5. Seller protection (empty box, not-as-described abuse)

| Product | How it works | Strengths / weaknesses | Source |
|---|---|---|---|
| eBay | **[O]**<br>- An eBay label with the item in transit means no refund is owed if it arrives within 21 days. Excludes orders over $5k and Authenticity Guarantee orders.<br>- Late-shipment defects are removed when the carrier scan shows the item shipped within handling time.<br>- Items returned used or damaged: the seller can **deduct up to 50%**, reporting within 2 business days.<br>- Abusive buyer reports get feedback and defects removed, and the buyer's returns limited or the buyer suspended.<br>- A false not-as-described claim is excluded from the seller's rate, but the seller still has to refund on return.<br>- Signature confirmation is required for INR protection on orders of $750 and up. **[U]** | The most complete rulebook. Sellers still say "empty box" returns are hard to win. eBay's own page doesn't directly address empty or switched returns. | https://www.ebay.com/help/policies/selling-policies/seller-protections?id=4345 ; https://www.ebay.com/help/seller-protections-abuse-policy/default/seller-protections-abuse-policy?id=5008 |
| Poshmark / Mercari | Release is final after accept or 72 hours. Returns go back to the seller with a tracked label, and the case is reviewed. Explicit seller-protection policy pages weren't found. **[U]** | Short windows shrink the room for abuse. | Posh Protect / Mercari pages above |
| Grailed | Buyer-only protection. Seller fraud concerns are reviewed case by case. **[O]** | Weak for sellers. | Grailed page above |
| Vinted | Seller protection only for in-app payments. Lost or damaged parcels are compensated if properly packed. "Empty parcel" claims are a known abuse that's "difficult to prove." **[3P]** | — | https://us.norton.com/blog/online-scams/vinted-scams |
| Authenticity Guarantee returns (eBay) | AG returns go back to the **authenticator for re-inspection** before the seller is debited. **[O]** | Stops the "swap in a fake" return scam for high-value items. | eBay AG page |
| Stripe (our liability) | The platform is **ultimately liable for chargebacks** with destination charges and separate charges-and-transfers. We recover by reversing transfers. Enable `debit_negative_balances`. Card network dispute-rate programs apply to us as merchant of record. **[O]** | We take the risk and need the holds in section 2. | https://docs.stripe.com/connect/marketplace/tasks/refunds-disputes |

**Best in class: eBay's label-based in-transit protection, plus authenticator re-inspection for high-value returns.** *Borrow:*
- Require platform labels.
- Have the agent prompt the seller for an automatic **pack-out photo or short video** with the tracking label visible, kept as evidence. Many sellers already do this; none of these platforms builds it in.
- Weigh at drop-off: the carrier's acceptance weight is evidence against empty-box claims.
- Route returns on high-value items through inspection.
- Score abusive buyers across our channels.

---

## 6. Authentication model and thresholds

| Product | How it works | Strengths / weaknesses | Source |
|---|---|---|---|
| eBay Authenticity Guarantee | Auto-enrolled, no seller fee, and sellers can't opt out. The seller ships to a third-party authenticator, which checks within about 2 business days and forwards to the buyer. **[O]**<br>US thresholds:<br>- Sneakers **$100+**<br>- Other shoes $500+<br>- Apparel $200+ (eligible brands)<br>- Handbags $500+ (optional for the buyer at $200–499.99 for $40)<br>- Jewelry $500+ (optional for $40)<br>- Watches **$2,000+** (optional at $500–1,999.99 for $80)<br>- Graded trading cards $200+<br>- Coins $500+<br>Items $750+ need signature confirmation to the authenticator. Backlog note: "delays of 7+ days." | Covers the most categories and scales thresholds by category. Adds days and a capacity risk. | https://www.ebay.com/help/selling/selling-tools/ebay-authenticity-guarantee?id=4644 |
| Posh Authenticate | Free for buyer and seller on select luxury brands **$500+**. Items go to Poshmark's facility, take 1–3 business days, then ship to the buyer. Fails get an instant refund, and the item returns to the seller and **can't be relisted**. **[O]** | Free, and blocks relisting of fakes. Only one threshold. | https://poshmark.com/posh_authenticate |
| Mercari Authenticate | Covers handbags, wallets, eyewear, jewelry, watches and designer shoes. It raises the price cap to $5k after ID verification. **[O]** Applies over $100, with a $5 fee paid by the seller. **[3P]** | Cheap, but opt-in. | https://mercari.com/us/help_center/article/515 ; https://crosslist.com/blog/mercari-seller-fees |
| Vinted Item Verification | **Optional, paid by the buyer.** £10 for designer items £85+ on eligible brands; £5 for electronics. The seller gets a prepaid label to the hub and has 5 business days to ship. Check takes 1–2 days. The buyer gets a hangtag and a digital report. Fails get a full refund; the seller can't relist, and repeat offenders are blocked. **[O]** Not confirmed for the US. **[U]** | Monetized and opt-in, with a low threshold. | https://www.vinted.co.uk/help/1147 ; https://www.vinted.co.uk/pricelist |
| Vestiaire | Hub route is buyer-selected. Items **$1,000+ always go via the hub**; under $1k in the same region can go direct. A failed authentication cancels the sale, and the seller pays a fee to get the item back. **[3P]** Fees: 17% from 2026-10-15. **[3P/U]** | Threshold-gated, buyer-choice hybrid. | https://www.underpriced.app/blog/vestiaire-collective-selling-guide-2026 |
| The RealReal | Consignment: everything is inspected in-house by 90+ experts, with AI and metal testing. **[O]** | Highest trust, highest take rate (20–70%). | https://resources.therealreal.com/how-to-sell-on-the-real-real/ |
| StockX / GOAT | Every sale ships to a verification center first. Ship within 2 business days (StockX) or 3 (GOAT). Failed authentication: $15 plus a level demotion on StockX; return shipping and a warning on GOAT. **[3P]** | Highest buyer trust for sneakers and streetwear. Slow, and puts strict condition rules on the seller. | https://www.underpriced.app/blog/stockx-goat-selling-guide-2026 ; https://stockx.com/news/en-us/updates-to-the-stockx-seller-program/ |

**Best in class: eBay's category-specific automatic thresholds, plus Vinted's and eBay's optional buyer-paid add-on below the threshold.** Also copy Poshmark's "fail = can't relist" rule. *Borrow:* don't build authentication in-house at launch. Partner with third-party authenticators and route by category and price, e.g. sneakers $150+, bags $500+, watches $2k+. Offer optional buyer-paid verification below that. For pre-verified inventory, copy StockX Flex: authenticate once, then allow instant payout and re-listing across channels.

---

## 7. Top scams and platform defenses

| Scam | How it works | Who defends best / how | Source |
|---|---|---|---|
| Off-platform payment | Buyer or seller pushes Venmo, Zelle, PayPal Friends & Family, a bank transfer, or a move to WhatsApp or Instagram. | Every platform voids protection for off-platform payment: eBay MBG **[O]**, Posh Protect **[O]**, FB **[3P]**. Depop's ToS bans out-of-app payments **[O]**. Vinted warns when a phone number is typed in chat **[3P]**. | https://depophelp.zendesk.com/hc/en-gb/articles/360001773148 ; https://us.norton.com/blog/online-scams/vinted-scams |
| Fake payment emails / "upgrade your account" | A fake Zelle or Venmo "payment held, pay $X to upgrade to a business account" email. Reported on FB Marketplace in **August 2026**. | Mitigation: payments only show in the app. Tell sellers that "money isn't real until it's in your in-app balance." | https://www.wrdw.com/2026/08/17/what-tech-facebook-marketplace-scam-tricks-sellers-into-refunds/ ; https://consumer.ftc.gov/consumer-alerts/2022/07/selling-stuff-online-heres-how-avoid-scam |
| Fake tracking / phishing links | Spoofed Vinted or carrier emails, or links sent in DMs that harvest logins or cards. | Vinted's advice is to turn off emails and check "My Orders." **[3P]** Common in the EU: fake "receive payment" or "delivery" pages, often with a QR code. **[U]** | https://us.norton.com/blog/online-scams/vinted-scams ; https://www.bitdefender.com/en-us/blog/hotforsecurity/depop-scams |
| QR code scams | A QR code that leads to malware or a payment-collection page, sometimes at an in-person meet. **[3P]** | No platform-level defense found. | Norton (above) |
| Verification-code scam | The "buyer" asks for a Google Voice or SMS code to "prove you're real," then hijacks the number or account. | FTC: never share codes. Block-listing phone numbers in chat helps. **[O, FTC]** | https://consumer.ftc.gov/consumer-alerts/2022/07/selling-stuff-online-heres-how-avoid-scam ; https://www.keepersecurity.com/blog/2024/09/30/facebook-marketplace-scams-to-avoid-in-2024/ |
| Overpayment / fake check | The buyer "overpays" by check or stolen card and asks for the difference back. The original payment later reverses. | Structural fix: the buyer pays the exact amount through checkout, and the platform never lets money go back from seller to buyer. **[O, FTC]** | FTC (above) |
| Empty box / item swap / false not-as-described | The buyer claims an empty box, or returns a fake or worn item. | eBay: authenticator re-inspects Authenticity Guarantee returns, 50% damaged-return deduction, abusive-buyer reporting. **[O]** Posh: a failed item can't be relisted. **[O]** | section 5 |
| Fake listings / bait-and-switch / account takeover | Stolen photos, or compromised accounts used to scam others. | 2FA (Depop ToS recommends it **[O]**). Authentication hubs. Reviews. | https://www.bitdefender.com/en-us/blog/hotforsecurity/depop-scams |

**Best in class: no single winner.** The strongest stack is **in-app-only payments, chat filters on contact details and links (Vinted), and "money only counts in your balance."** *Borrow, and our edge:* **the AI agent handles buyer conversations for the seller.** It never leaves the platform, never shares codes or phone numbers, never acts on payment emails (it checks payment through the platform API), and refuses overpayment or refund-the-difference requests. That makes the agent a built-in scam firewall, which is a strong marketing claim. Log flagged messages to train a cross-platform buyer-risk score.

---

## 8. Local pickup safety

| Product | How it works | Strengths / weaknesses | Source |
|---|---|---|---|
| eBay | Local pickup is paid on eBay. The seller scans the **buyer's QR code or enters a 6-digit pickup code**, which confirms the handover and releases funds. **[O]** | Proof of handover, no cash, no fake-payment risk. | https://www.ebay.com/help/selling/getting-paid/getting-paid-items-youve-sold/payments-hold?id=4816 |
| FB Marketplace | Local pickup and meet-ups are **excluded** from Purchase Protection. **[3P]** Most deals are cash, Zelle or Venmo, which is where the scams in section 7 happen. | Weakest. | https://oneshop.com/blog/facebook-marketplace-purchase-protection |
| Vinted | Advice: in-person deals in cash. The QR code risk is noted. **[3P]** Vinted Go pick-up points and lockers are an alternative to meeting strangers. **[O]** | Lockers remove the meet-up entirely. | https://www.vinted.com/help/1549 |
| FTC guidance | Sell locally and take cash where possible. Don't accept mobile payments from strangers. **[O, FTC]** | — | FTC (above) |
| General practice | Public "safe exchange zones" (e.g. police station lots), daytime meets, bringing a friend. **[U]** | — | — |

**Best in class: eBay's prepaid local pickup with a QR or 6-digit handover code.** *Borrow:* in-app payment for local deals, released on code scan. Default the meeting to safe public spots or carrier pick-up points. Have the agent handle scheduling so phone numbers are never shared.

---

## 9. US regulations (plus EU notes)

| Rule | What a marketplace must do | Source |
|---|---|---|
| **Form 1099-K** | The One Big Beautiful Bill (2025) **retroactively restored the $20,000 and 200-transaction** threshold for payment processors (both must be exceeded). The IRS issued FAQs on 2025-10-23. **[O]** Some states set lower thresholds of their own. **[U]** If we're the payment processor and merchant of record, we (or Stripe, as filer for Connect accounts **[U]**) file. Collect TIN/W-9 from sellers. | https://irs.gov/newsroom/irs-issues-faqs-on-form-1099-k-threshold-under-the-one-big-beautiful-bill-dollar-limit-reverts-to-20000 |
| **INFORM Consumers Act** (in force 2023-06-27) | A high-volume seller has **200+ sales and $5,000+** in any 12-month period within the last 24 months, counting **new or unused** products sold through our payment processing.<br>- Within **10 days** of a seller qualifying, collect and verify their bank account, tax ID and contact details.<br>- Have sellers re-certify annually.<br>- For sellers with **$20k+**, show their name, address and contact details (home sellers may show only state and country).<br>- Show a suspicious-activity reporting channel on listings.<br>- Suspend sellers who don't respond within 10 days.<br>- Penalty: about $53k per violation.<br>Note: used goods may not count toward the threshold, but resale "new with tags" items do. **[O]** | https://www.ftc.gov/business-guidance/resources/informing-businesses-about-inform-consumers-act |
| Money transmission | Mercari says it is a regulated Money Service Business. **[O]** Using Stripe Connect (Stripe as the licensed party) generally avoids our needing money-transmitter licenses. **[U, get legal advice]** | https://mercari.com/us/help_center/article/515 |
| EU later | DAC7 seller income reporting (thresholds of about 30 sales or €2,000), DSA trader traceability (KYBC), a 14-day consumer right of withdrawal for business sellers (Vinted Pro shows this), and Stripe's 90-day manual payout cap outside the US. **[U, except the Stripe cap: O]** | https://docs.stripe.com/connect/manual-payouts |

---

## 10. Implementation notes for our checkout (Stripe Connect)

- **Charge type:** use separate charges and transfers. Charge the buyer on the platform, then transfer to the seller with `source_transaction` once the order completes. This gives us full control of the hold. Refunds don't reverse transfers automatically, so we have to reconcile them ourselves. With ACH or other async payments, wait for `charge.succeeded`. **[O]** https://docs.stripe.com/connect/separate-charges-and-transfers
- **Alternative:** manual payouts on connected accounts. US funds can be held up to 2 years; most other countries 90 days. **[O]**
- **Our liability:** the platform carries chargeback liability under both charge models, so turn on `debit_negative_balances` and Radar, and hold new sellers for about 2 weeks or until delivery. **[O]**
- **Order state machine to copy:** paid → label created (agent) → in transit → delivered → 72-hour window (or buyer OK) → available. Variants: early release at label scan for trusted sellers, and an authentication-hub detour above category thresholds.
- **Fee structure to copy:** charge the buyer a protection fee (Vinted, Mercari, Depop) instead of a high seller commission. That's consistent with a seller-side agent pitch.
