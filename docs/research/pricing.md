# Pricing one-of-a-kind used goods: research and recommended system

Prepared 2026-10-25 for a cross-platform resale product. Fashion comes first, then furniture and design.

**Evidence tags used throughout**
- **[V]**: I opened the source and the figure is taken from it.
- **[S]**: secondary source, such as a trade blog or press summary. The figure was read, but the original data was not checked.
- **[U]**: unverified. It comes from background knowledge, from a page I could not open, or is a derived estimate. Check it before relying on it.

Some sources could not be fetched in this session: the pricecharting.com FAQ, worthpoint.com, the pmc.ncbi.nlm.nih.gov article PMC11890435, and the eBay Marketplace Insights method docs (the site returned a sign-in page). Every claim about those is tagged [U].

---

## 0. Executive summary

1. **Most of the accuracy comes from retrieving comparables, not from a clever regression.** Alibaba's Xianyu C2C pricing system (LLP, 2025) raised its strict-accuracy rate from 17.4% with a vanilla LLM to 49.2% just by adding retrieval of the top 50 similar items from the last 90 days. Fine-tuning and RL then took it to 54.6% [V] (https://arxiv.org/html/2510.09347v1). Learned comps retrieval also beats geographic retrieval in real-estate appraisal [V] (https://arxiv.org/pdf/2603.12986). Identity resolution plus comps retrieval should be the core of the system.
2. **Expect large irreducible error on generic C2C items, and measure each tier separately.**
   - The Mercari Kaggle winner scored about 0.39 RMSLE on text alone [S/U].
   - Xianyu's best system has a mean absolute log error of 0.355 overall [V].
   - Zillow's off-market median error is about 7% for homes, which are far better documented than a used jacket [S].
   - Accuracy targets therefore have to be set per tier (exact SKU, model, brand/category, unique).
3. **Price and time-to-sale are one joint decision.** Overpricing lengthens time on market at an increasing rate:
   - Houses: a 1% overprice adds about 1.3% to time on market, and the effect is convex [V] (https://eres.scix.net/pdfs/eres2001_105.content.pdf).
   - Used cars: the hazard ratio is 0.836 per standard deviation of price-to-value, and time to sell rises steeply once a car is well overpriced [V] (https://real.mtak.hu/247298/1/epj_survival.pdf).
   - eBay: a higher start price sharply lowers sale probability (slope −0.64) while only modestly raising the price conditional on sale (+0.21) [V] (https://web.stanford.edu/~leinav/pubs/AEJmicro2015.pdf).
   - The product should output a curve of P(sold by day t | price), not just a single number.
4. **Unsold listings are as informative as sold ones.** Train on them as censored observations. Opendoor uses a daily hazard model [V] (https://www.datacouncil.ai/hubfs/SF%2018%20-%20Slides/DS/Xinlu%26David-Opendoor%20.pdf). Airbnb and Xianyu both use interval losses that treat an unsold price as an upper bound and a sold price as a lower bound [V] (https://blog.acolyer.org/2018//03/customized-regression-model-for-airbnb-dynamic-pricing/, https://arxiv.org/pdf/2012.06008).
5. **Most sellers overprice, so a good suggestion usually means a lower price and more revenue.** Airbnb Smart Pricing adopters cut nightly price by 5.7% and raised revenue by 8.6% [V] (https://www.informs.org/News-Room/INFORMS-Releases/News-Releases/New-Research-Finds-Algorithm-Meant-to-Eliminate-Racial-Disparities-in-Airbnb-Revenue-Fails-to-Enhance-Revenue-Equality). ThredUp says about 38% of accepted items do not sell within their consignment window [V] (https://www.thredup.com/cleanout/consignment).
6. **Zillow Offers lost money mainly through adverse selection plus the decision to override its own model, not through the Zestimate itself.**
   - It wrote down about $304M of inventory in Q3 2021 [V].
   - It bought 9,680 homes in Q3 but sold only 3,032 [V].
   - Under "Project Ketchup" it bought 74% of homes that requested an offer, against a 50–60% target [V] (https://inman.com/2021/11/09/zillow-raced-to-catch-up-with-opendoor-in-a-secret-initiative-called-project-ketchup-report).
   - iBuyers that survive buy only easy-to-value, liquid homes, where the algorithm explains more than 80% of price variation [V] (https://www.nber.org/system/files/working_papers/w28252/w28252.pdf).
   - The lesson: do not guarantee prices or buy inventory at a point estimate. If you ever offer a guaranteed price, base it on a lower quantile, and only for tight-interval, high-liquidity items. Watch the acceptance rate.
7. **Your own displayed price will shape outcomes.**
   - A 1% higher Zestimate raises list price by about 0.73% and sale price by about 0.08% [V] (https://nber.org/system/files/working_papers/w29880/w29880.pdf).
   - Models trained on outcomes they influenced become overconfident [V] (https://ar5iv.labs.arxiv.org/html/2302.09438).
   - Mitigations: keep holdouts, log the price you showed, and add small randomized perturbations to list prices.
8. **Sold-comp data is hard to get legally at scale.**
   - eBay Marketplace Insights is "Limited Release", and developers report being denied access except for major partners [V] (https://developer.ebay.com/develop/buying-apps/research-apis, https://community.ebay.com/t5/eBay-APIs-Talk-to-your-fellow/Marketplace-Insights-API-access/m-p/34838736).
   - Terapeak is free, but only in the eBay Seller Hub UI [V].
   - Your structural advantage is operating each seller's own accounts. That gives you first-party telemetry: views, watchers, likes, offers and outcomes on every platform you cross-post to. It is effectively a multi-platform pricing experiment on every item. Build the data flywheel around this.
9. **Fees and the platform change the price.**
   - On eBay, sellers bear about 80% of a shipping fee in a lower sale price [V] (Einav et al. 2015).
   - Poshmark's October 2024 move to a 5.99% buyer fee produced double-digit sales drops for power sellers, and Poshmark reverted within about three weeks [V] (https://www.modernretail.co/technology/platforms-have-to-walk-a-very-fine-line-why-2024-was-the-year-of-the-resale-fee-wars/).
   - The same item lists at very different prices across platforms (eBay cheapest in 12 of 20 cases) [S] (https://fashionunited.uk/news/fashion/ebay-is-the-cheapest-resale-platform-data-shows/2022091365118).
   - 1stDibs requires sellers' prices on 1stDibs to match or beat their other channels [V] (https://www.sec.gov/Archives/edgar/data/1600641/000160064126000007/dibs-20251231.htm).
10. **Recommended architecture** (Section 7): identity → hybrid comps retrieval (sold, active and unsold, deduplicated and time-adjusted) → hierarchical Bayesian base value → learned condition and attribute multipliers → market-state features → discrete-time sale-hazard model per channel → net-proceeds optimizer that outputs list price, hidden floor, expected price, interval and days-to-sell → Bayesian markdown engine driven by observed engagement and offers. Calibrate intervals with CQR, evaluate with time-split backtests and seller-randomized A/B tests, and keep a permanent holdout with no suggestions.

---

## 1. Theory and methods

### 1.1 Hedonic pricing
- **Origin.** Rosen (1974), "Hedonic Prices and Implicit Markets", treats a differentiated good's price as a function of its characteristics. The implicit price of each characteristic is the partial derivative of the hedonic price function (https://www.journals.uchicago.edu/doi/10.1086/260169) [V: citation].
- **Practical form for resale.** log(price) = f(brand, line/model, category, retail price, age/season, material, size, condition, completeness, authentication, channel, time) + ε. Gradient-boosted trees or neural nets on these features are the modern "hedonic" model.
- **What the evidence says about its ceiling on C2C data.**
  - Mercari Price Suggestion Challenge: 1.4M training listings with name, condition, category, brand, shipping and description. The metric was RMSLE. The winning sparse-feature MLP ensemble scored roughly 0.37–0.39 [S] (https://towardsdatascience.com/pricing-objects-in-mercari-machine-learning-deep-learning-perspectives-6aa80514b2c8/). The exact private-LB score, about 0.387, is [U].
  - Xianyu, vision only: about 1M items, MALE 0.386 and RMSLE 0.530 on the 50% of items the model judged price-able [V] (https://arxiv.org/pdf/2012.06009).
  - Xianyu, text plus image: SMLE around 0.13–0.15 on the roughly 60% of items accepted. Removing text hurt far more than removing images (0.2157 vs 0.1604) [V] (https://arxiv.org/pdf/2012.06008). For used goods, titles and descriptions (brand, model, size) carry more price signal than pixels. Images still matter for condition and for identification.
- **Implication.** A pure hedonic model is a good fallback and prior, but on its own it is too noisy for one-of-a-kind fashion. Use it as the base layer, then let comps and item-specific evidence override it.

### 1.2 Comparable-sales methods and AVMs
- **Manheim MMR**, the used-car wholesale benchmark, is the cleanest published comps recipe [V] (https://site.manheim.com/?p=44518):
  - Data is auction transactions only. It excludes salvage, title-branded vehicles, units under 50 miles, and statistical outliers.
  - The window is the past year, with recent sales weighted more heavily.
  - A trim needs at least 6 transactions in the year and at least 2 in the last 90 days to get a standard value.
  - Separate per-vehicle adjustments cover mileage depreciation, region, condition grade (AutoGrade), EV battery health and colour.
  - The "MMR Range" is the band where 70% of similar sales are expected to fall.
  - With a small sample, a flag is shown and the value is estimated from MSRP and the depreciation trends of similar vehicles. That fallback is a cold-start rule worth copying.
- **Opendoor Valuation Model.** A Siamese neural network embeds how appraisers select, adjust and weight comps. It is trained partly on the history of human pricing-expert adjustments, and experts stay in the loop for hard-to-value features. Backtests train on Jan 2015–Jan 2021 and test on Feb 2021. Data-distribution monitors raise alerts, for example when apartment share jumps from 20% to 50% in a day [V] (https://www.unite.ai/sam-stone-pm-pricing-at-opendoor-interview-series/).
- **Learned comps retrieval (2026).** The retriever and estimator are trained end to end with a bounded ±100% multiplicative adjustment. Vector retrieval found better comps than geographic retrieval on 4 of 5 datasets and needed fewer comps for the same accuracy. The paper uses MdABRE, a symmetric relative error |x−y|/min(x,y), and chronological splits so the model cannot use future sales as comps [V] (https://arxiv.org/pdf/2603.12986).
- **LLP at Xianyu (2025)**, the closest published analogue to this startup [V] (https://arxiv.org/html/2510.09347v1):
  - It retrieves the top 50 similar items from a pool of listings from the last 90 days, using generative semantic IDs and approximate nearest-neighbour search.
  - Qwen2.5-7B reasons over the retrieved items to produce a price and a rationale. It is trained with SFT and then GRPO, with a reward of price accuracy × comp recall.
  - High-entropy outputs are discarded, trading coverage for precision.
  - Offline overall: RMSLE 0.627 vs 1.090 for the prior system, and MALE 0.355 vs 0.659.
  - Online: strict accuracy 72% vs 40% at equal coverage.
  - The exact SAR/DAR accuracy thresholds are not stated in my extraction [U].

### 1.3 Repeat-sales indices
- **Method.** Case-Shiller (and Bailey-Muth-Nourse 1963 [U]) uses pairs of sales of the same unit to estimate a market index while holding quality fixed (https://en.wikipedia.org/wiki/Case-Shiller_index; https://www.stlouisfed.org/on-the-economy/2015/january/the-differences-between-house-price-indexes) [V: links].
- **How it applies here.** Unique used items rarely resell, so true repeat sales are rare. Two uses remain:
  - **Market-level indices for standardized segments** (a model, style code or designer chair). ChronoPulse is built from Chrono24's real transaction prices: 14 brands covering ≥80% of the market, 140 models, about 30k sales a month, updated daily, with weights reviewed every 6 months [V] (https://www.nationaljeweler.com/articles/12492-chrono24-debuts-the-dow-jones-for-luxury-watches). Card Ladder provides player and category card indices, which eBay's Price Guide displays [V] (https://www.cllct.com/sports-collectibles/memorabilia/ebay-to-add-card-ladder-data-to-its-price-guide; https://pages.ebay.com/price-guide/).
  - **Time-adjusting old comps.** A sale from 9 months ago is moved to today using the segment index, as housing AVMs do.
- Building **brand × category hedonic time-dummy indices** is the practical substitute for repeat-sales in fashion.

### 1.4 Auction theory: where it matters
- **Auctions vs posted prices on eBay** [V] (https://web.stanford.edu/~jdlevin/Papers/AFP.pdf):
  - Auctions sell more often but at a discount. In 2009, 42% of auction listings sold vs 25% of posted-price listings.
  - The auction discount grew from 4.7% in 2003 to 16.5% in 2009, as buyers came to value convenience.
  - Auctions remain favoured for used goods (79% of used listings vs 44% of new) and for unique items (75% of unmatched listings).
  - Implication: auctions are a **price-discovery tool for no-comps items**, not a default.
- **Start-price and demand shape** [V] (Einav, Kuchler, Levin, Sundaresan, AEJ Micro 2015, https://web.stanford.edu/~leinav/pubs/AEJmicro2015.pdf):
  - The coefficient of variation of auction prices for the same seller and item is about 0.11. That is the noise floor even for identical items.
  - Mean auction price is about 0.84 of the same seller's posted price.
  - Demand is highly convex, so marginal revenue is U-shaped and very low or very high start prices beat intermediate ones.
  - BIN prices below 0.9 of the reference value cut realised price by about 0.09–0.11 of value.
  - Secret reserves are rare (<1% of listings) and show no clear effect.
- **Bargaining and offers**, which are central to Poshmark, Mercari, eBay Best Offer and 1stDibs "Make Offer":
  - Round-number list prices get offers 6–11 days sooner and are 3–5% more likely to sell, but sell for 5–8% less. Buyers read them as a signal of an impatient seller [V] (https://www.nber.org/digest/sep15/cheap-talk-round-numbers-and-signaling-behavior).
  - Mercari Japan, used iPhone 7: about 20% of sales go through bargaining. Sale price is about 97% of list. 37.4% of accepted offers are never completed. Each extra 10 points of discount in an offer cuts acceptance by about 13.6 points [V] (https://arxiv.org/pdf/2602.13707).
  - Poshmark: in 2025 it previewed raising the offer floor from 20% to 40% of list. Offers to likers must be at least 10% below the prior lowest offer or list price [V/S] (https://www.valueaddedresource.net/poshmark-poshfest-2025-hackathon/; https://tools.oneshop.com/blog/offers-poshmark).
- **Implication.** On offer-heavy platforms, list price is an anchor. The hidden floor works like a reserve and acts as auto-accept/decline thresholds. The gap between them should be learned per platform from accepted-offer data.

### 1.5 Survival and time-to-sale models
- **Opendoor.** Each listing becomes one row per day on market, with a calibrated classifier for P(sell tomorrow). This yields hazard and survival curves and handles censoring (active or delisted homes). Time-varying covariates such as price changes are allowed. Snapshot models are interpolated over time for non-stationarity [V] (https://www.datacouncil.ai/hubfs/SF%2018%20-%20Slides/DS/Xinlu%26David-Opendoor%20.pdf).
- **Used cars (Hungary, 567k listings)** [V] (https://real.mtak.hu/247298/1/epj_survival.pdf):
  - The key covariate is price-to-value, the ask divided by a predicted market value from XGBoost (R² about 0.95).
  - Cox hazard ratio is 0.836 per standard deviation.
  - A random survival forest shows time to sell rises steeply for significantly overpriced cars, a non-linearity Cox misses.
  - Median time to sale is 11 days. Listings at or below value are predicted to sell in 12–13 days.
  - Concordance is 0.59 (Cox) to 0.63 (RSF), and relative price discriminates better than raw price.
  - Caveat: delisting is not the same as a sale.
- **Housing.** Each 1% of overpricing raises time on market by about 1.3%, with a convex effect (squared term 1.98). The discount from list to sale is almost uncorrelated with overpricing (R² 0.006). Overpricing costs time more than it costs price [V] (https://eres.scix.net/pdfs/eres2001_105.content.pdf).
- **Design rule.** Model the hazard as a function of **relative price r = p / V̂**, together with item, market and channel features. The price–speed trade-off then comes directly from the hazard model.

### 1.6 Demand and price-elasticity estimation
- **Airbnb Smart Pricing (KDD 2018)** [V] (https://blog.acolyer.org/2018//03/customized-regression-model-for-airbnb-dynamic-pricing/; https://videolectures.net/kdd2018_ye_airbnb_dynamic_pricing):
  - A GBM booking-probability model, one per market, uses listing, temporal and supply/demand features (neighbourhood listing counts, views, search and contact rates).
  - Airbnb found the demand curve it implied **too noisy to optimize revenue directly**. Direct revenue maximization "often fail[ed]" online.
  - Instead, a **strategy model** multiplies the host's price by an asymmetric exponential factor. Its parameters are fit per listing, with market and global fallbacks.
  - The loss uses ranges: booked nights have bounds [P, c2·P] and unbooked nights have [c1·P, P].
  - Offline metrics are Price Decrease Recall (on unbooked nights, did the suggestion go lower?) and Booking Regret (on booked nights, how far below the realised price was the suggestion?).
  - Field result from the INFORMS study above: adopters had −5.7% price and +8.6% revenue [V].
- **Uber surge.** A regression discontinuity on surge-multiplier rounding, using about 50M sessions, estimated demand elasticities at several points of the curve [V] (https://www.nber.org/papers/w22627). Elasticities were around −0.4 to −0.6 [U].
  - The transferable idea: **your own pricing rules create discontinuities you can use for causal identification.** Examples are rounding, step thresholds and randomized ±x% perturbations.
- **Rue La La (flash sales, first-exposure items with no history)** [V] (https://dash.harvard.edu/bitstream/1/26964422/1/ferreira,lee,simchi-levi_analytics-for-an-online-retailer.pdf):
  - It forecast demand from similar past items with bagged regression trees. Features included relative price vs competing items and discount vs MSRP.
  - It corrected for censoring on sold-out items and then optimized price.
  - Field test: +9.7% revenue (90% CI 2.3–17.8%). About 30% of the gain came from forecasting alone. The lowest-price category lost about 3.4%, a reminder to segment.
- **Deep RL on Tmall** [V] (https://ar5iv.labs.arxiv.org/html/1912.02572):
  - Reward design was decisive. Plain revenue-conversion rate was unstable. The price–conversion correlation was −0.57 for luxury items but only 0.15 for fast-moving consumer goods.
  - A difference-of-revenue-conversion-rate reward and offline pretraining on expert decisions (DQfD/DDPGfD) were needed.
  - In markdowns, DQN beat human managers, who drove profit conversion negative.
  - The lesson is less "use RL" than "use a profit-aware reward and pretrain on logged decisions".
- **Double/debiased ML** handles confounding when estimating elasticities from observational data, for example when sellers who price low are also better listers (https://arxiv.org/abs/1712.09988v2, scanner-data elasticity application) [V: abstract].
- **Strategic waiting.** Shoppers who monitor prices capture markdowns. A randomized-markdown policy beat state-contingent markdowns by about 81% in profit for a specialty retailer [V] (https://pubsonline.informs.org/doi/fpi/10.1287/mnsc.2016.2661). Predictable markdowns teach buyers to wait. Prefer **targeted private offers** (to likers and watchers) and randomized timing over fixed public schedules.

### 1.7 Quantile regression and conformal prediction intervals
- **CQR (Romano, Patterson, Candès, NeurIPS 2019)** [V] (https://ar5iv.arxiv.org/html/1905.03222):
  - Fit lower and upper quantile models, compute conformity scores on a calibration set, and widen or narrow the band by the empirical quantile.
  - It guarantees finite-sample marginal coverage under exchangeability, and the width adapts to heteroscedasticity.
  - In the paper's example, average interval length at 90% coverage was 1.99 vs 2.91 for split conformal.
- **Production caveats.**
  - Coverage is marginal. Use Mondrian, group-wise conformal (by category, price decile and comp-count tier) for conditional validity.
  - Exchangeability breaks under drift and trend shocks. Use time-weighted or adaptive conformal: Barber et al. 2023, "Conformal prediction beyond exchangeability", arXiv 2202.13415 [U]; Gibbs & Candès 2021, adaptive conformal inference, arXiv 2106.00170 [U].
- **Industry precedents.**
  - MMR shows a 70% range and suppresses it when data is thin [V].
  - Zillow shows an "estimated sales range" [V] (https://www.zillow.com/zestimate). Zillow's June 2021 update widened the displayed range (22.69% to 24.66%) while realised error fell (4.36% to 3.41%), consistent with earlier overconfidence [V] (https://ar5iv.labs.arxiv.org/html/2302.09438).

### 1.8 Bayesian approaches for sparse comps
- **Hierarchical partial pooling.** Item-level value is shrunk toward model → line → brand × category → category priors, weighted by comp count and similarity. Airbnb fits per-listing parameters with market and global fallbacks for listings with little data [V]. MMR falls back to MSRP and depreciation trends when samples are small [V].
- **Observations to update with:** sold comps (exact values), unsold or expired listings (right-censored upper bounds), active listings (weak upper bounds with no outcome yet), and offers received (lower bounds on at least one buyer's willingness to pay).
- **Thompson sampling for price exploration** with demand learning: Ferreira, Simchi-Levi, Wang (2018), "Online Network Revenue Management Using Thompson Sampling", Operations Research [U]. For one-off items it is cleaner to share the learned elasticity parameter across items in a segment.

---

## 2. Industry systems

| System | What it does | Numbers and facts | Lesson for you |
|---|---|---|---|
| **Zillow Zestimate** | Neural-network AVM using MLS, tax records, comps, days on market and listing descriptions. Shows an estimated sales range. | Median error **1.94% on-market** and **7.06% off-market**. For on-market homes, 82%/95%/99% fall within 5/10/20% (theclose.com, citing Zillow, March 2025) [S] (https://theclose.com/how-accurate-is-zillow-zestimate/). Zillow Prize winners cut error about 13% vs the benchmark (from about 4.5% to under 4%) [V] (https://venturebeat.com/ai/zillow-awards-1-million-to-team-that-reduced-home-valuation-algorithm-error-to-below-4). | The list price is a huge feature: on-market error is about 3.6× lower. Your "on-market" analogue is the seller's own ask plus engagement. |
| **Zillow Offers (failure)** | Algorithmic iBuying. | Q3 2021: inventory write-down of about **$304M**, Homes segment loss of −$422M, wind-down, about 25% layoffs. Barton: "unpredictability in forecasting home prices far exceeds what we anticipated" [V] (https://investors.zillowgroup.com/news-and-events/news/news-details/2021/Zillow-Group-Reports-Third-Quarter-2021-Financial-Results--Shares-Plan-to-Wind-Down-Zillow-Offers-Operations/default.aspx). Bought **9,680** homes and sold **3,032** in Q3, ending with 9,790 in inventory [V] (https://www.geekwire.com/2021/Zillow-shutter-home-buying-business-lay-off-2k-employees-big-real-estate-bet-falters/). "Project Ketchup" raised offers to win share: **74%** of offer requests were bought vs a 50–60% goal. Holding cost was about $225 a day, and contractor bottlenecks followed [V] (Inman link above). | Adverse selection plus deliberate overbidding plus slow liquidation. A rising acceptance rate is a warning sign. Holding cost turns model error into losses. |
| **iBuyer economics (academic)** | Buchak, Matvos, Piskorski, Seru | iBuyers pay about 3.1% below market and resell at about +1.5%. The algorithm explains more than 80% of price variation in iBuyer deals vs 68% in others. They avoid homes with under a 50% chance of selling within 3 months. Zillow accepted about 10% of offers. If iBuyers lost the ability to separate quality, their share would fall from about 5% to about 1% [V] (https://www.nber.org/system/files/working_papers/w28252/w28252.pdf). A revenue-sharing contract (lower upfront payment plus a share of resale) reduces selection [V] (https://bcf.princeton.edu/events/so-hye-on-impatience-vs-winners-curse-is-ibuying-sustainable/). | Only commit capital where items are easy to value and liquid. Consignment or revenue share is structurally safer than buying. |
| **Opendoor** | OVM Siamese comps network plus human pricing experts; daily hazard liquidity model. | See 1.2 and 1.5 [V]. | Human-in-the-loop for features the model cannot see. Liquidity is modeled as hazard. |
| **Manheim MMR / KBB / Edmunds / Carvana** | Vehicle valuation | MMR: see 1.2 [V]. KBB condition mix: **Excellent 2%, Very Good 28%, Good 50%, Fair 20%** [V] (https://www.kbb.com/honda/accord/2023/lx-sedan-4d/condition). Edmunds TMV is an average transaction price in your area, excluding some fees [V] (https://help.edmunds.com/hc/en-us/articles/206102387). Carvana's decision model weighs "quality, inventory fit, consumer desirability, relative value, expected reconditioning costs", and its filing says price volatility "can also complicate pricing algorithms, appraisal accuracy" [V] (https://www.sec.gov/Archives/edgar/data/1690820/000169082026000009/cvna-20251231.htm). | Use standardized condition grades with a known base rate. People self-grade "excellent" far more often than 2%, so the startup must grade condition from photos. |
| **StockX** | Bid/ask exchange for standardized items | Seller tools include Sell Now (meets the highest bid), Sell Faster (become the lowest ask) and Earn More (based on recent global sales) [V] (https://stockx.com/help/en-GB/articles/what-pricing-tools-are-available-for-non-us-sellers). Historical average resale is about **1.48× retail**, and **27.7%** of orders sold below retail (2016–2019) [V] (https://stockx.com/news/the-stockx-data-guide-to-resale/). | For SKU-level items (sneakers, some bags), the bid/ask book is the best "market state". Expose "sell now vs earn more" as two points on the time-to-sell curve. |
| **eBay** | Terapeak Product Research; Price Guide; Marketplace Insights API | Terapeak: 3 years of sold data, average price, range, shipping and **sell-through (≤90 days only)**. Free for Seller Hub users [V] (https://www.ebay.ca/help/selling/selling-tools/terapeak?id=4853). Price Guide is for trading cards only. It matches card and grade, **uses accepted Best Offer prices**, refreshes every 24 h, and shows 2 years of history [V] (https://pages.ebay.com/price-guide/). Marketplace Insights is "Limited Release" [V], and access is reported as denied except for major partners [V-forum]. Auto Price Reduction (fixed $ steps every 3/5/7/14/30 days, with a floor) was reportedly discontinued around 2026-02-03 [S-forum] (https://community.ebay.com/t5/Selling/New-Feature-Auto-Price-Reduction/m-p/35177508). | eBay itself treats accepted-offer price, not list price, as the truth. Its sold-data API is closed. |
| **Mercari** | Smart Pricing (auto-drops to a seller floor); Kaggle challenge | Smart Pricing adjusts "based on market demand and competitor data" down to a seller minimum [S] (https://www.nifty.ai/post/mercari-smart-pricing). Kaggle: see 1.1. Fees went from 0% in March 2024 to a 10% seller fee plus a 3.6% buyer fee from January 2025 [V] (Modern Retail link above). | A "floor plus automatic drops" UX is accepted by sellers. |
| **Poshmark** | Price Suggester (previewed 2025), offers | Two suggestions, "sell faster" (with a "hot deal" badge) and "estimated sale price"; offer floor raised to 40% [V] (https://www.valueaddedresource.net/poshmark-poshfest-2025-hackathon/). Fee experiment on 2024-10-02: 20% seller fee changed to 5.99% seller plus 5.99% buyer plus $1–3. Sales fell by double digits for power sellers, and it reverted around 2024-10-21 [V] (Modern Retail). | Two-point suggestions are now the norm. Buyer-visible fees are highly elastic. |
| **Depop** | Pricing Inspiration | A three-point range (lower bound sells fast, prediction, upper bound may take longer) plus similar sold items sorted by price and similarity. Inputs are description, product type, department, condition and brand. UK/US only, **no luxury brands** [V] (https://partnerapi.depop.com/api-docs/concepts/pricing-inspiration/). US selling fee was removed on 2024-07-15, with a buyer fee of up to 5% + $1 [V] (https://news.depop.com/depop-removes-selling-fees-in-the-united-states-evolves-fee-structure/). | The low/mid/high framing tied to speed is good UX. Note the luxury exclusion: it is hard (authentication and price variance). The doc sits on a partner API domain, which suggests partner access may be possible [U]. |
| **Vinted** | No seller fees; guidance by condition | Help page suggests **New/Like-new 60–80% of retail, Very good 40–60%, Good/Satisfactory 20–40%** [V] (https://www.vinted.co.uk/help/376). | A ready-made cold-start prior on percent of retail by condition. |
| **ThredUp** | Managed consignment | Initial price is set by algorithm from "past sales, brand, and item quality". Prices are lowered gradually. Consignment windows are 30–45 days (Standard) or 60–90 days (Premium). **About 38% of accepted items don't sell in their window**. Payout share ranges from 3% at $5 to 80% at $200 [V] (https://www.thredup.com/cleanout/consignment). It processes more than 100k unique SKUs a day and uses third-party ML to set "optimal list price" [V] (https://www.sec.gov/Archives/edgar/data/1484778/000148477826000007/tdup-20251231.htm). Job posting: RL agents for dynamic pricing, contextual bandits and marketplace simulation [V] (https://hire.thredup.com/9657323/remote-staff-applied-scientist-marketplace-optimization). | Even a large operator leaves about 38% unsold in-window. Markdowns are essential, and RL plus bandits is where they are heading. |
| **The RealReal** | Managed luxury consignment | Pricing algorithm "evaluates more than 100 data points per item to set and adjust prices without human override", including page views and favorites, and manages markdowns. Athena AI intake handles nearly half of items by end of 2026. Q2 2026 GMV $617M (+22%), AOV $659 [S] (https://www.pymnts.com/?p=4050142). | Engagement (views, favorites) drives markdowns at scale. Prices are set without human override. |
| **Xianyu (Alibaba)** | C2C price suggestions | See 1.1 and 1.2. These are the best-documented C2C systems, including an image/text "qualified for suggestion" gate [V]. | Gate suggestions by confidence. Don't price what you can't identify. |
| **Airbnb** | Smart Pricing | See 1.6 [V]. | Use a strategy model on top of a noisy demand model, an asymmetric loss and PDR/BR metrics. |
| **Uber/Lyft** | Surge | See 1.6. Only instructive for causal identification via discontinuities. | Same. |
| **Rebag Clair** | Handbag appraisal | Six years of data across 50+ brands; scan to identify the model and show a typical resale price; humans still authenticate [V] (https://retailbrew.com/stories/2021/02/03/rebag-develops-resale-appraisal-tool-powered-artificial-intelligence). | A precedent for a camera-to-price flow. |
| **1stDibs** | High-end design and furniture | About 1.9M listings, MOV about $1,300, AOV about $2,600 (2025). "Make Offer" and Private Offers are common. The "1stDibs Insider" pricing index gives sellers historical pricing context. AI/ML pricing guidance. **Price-parity requirement** [V] (https://www.sec.gov/Archives/edgar/data/1600641/000160064126000007/dibs-20251231.htm). | Cross-platform price differentiation can breach platform rules. The channel module must enforce parity. |
| **Chairish** | Vintage furniture | Commission of 20–40% by plan. Elite/Platinum tiers: 20% up to $2,500, 12% from $2,501 to $25k, 3% above [V] (https://support.chairish.com/hc/en-us/articles/115006460407). Chairish listing prices were "flat" while new-goods prices rose (2022 report) [V] (https://www.chairish.com/blog/viva-la-vintage-check-out-our-2022-home-furnishings-resale-report). | Fees vary 10× across channels, so net-proceeds optimization matters. |
| **WorthPoint** | Aggregated sold prices for antiques and collectibles from eBay and auction houses | Could not fetch. Subscription product with hundreds of millions of records [U]. | Candidate licensed source for vintage and collectibles. |
| **Chrono24 ChronoPulse** | Watch index | See 1.3 [V]. | Template for transaction-based segment indices. |
| **Card Ladder / eBay Price Guide** | Card indices and comps | See 1.3 [V]. | Same. |
| **PriceCharting** | Games and cards price guide by condition tier (loose, CIB, new, graded) from completed sales | Could not fetch. Paid API and CSV downloads [U]. | Condition tiers × completeness as separate price series. |

---

## 3. Supply and demand signals

| Signal | Definition and use | Observable publicly? | How to get it |
|---|---|---|---|
| Active listing count (supply) | Live listings matching the item identity or cluster. Used for months-of-supply = active ÷ monthly sales. | Yes, through on-platform search on all major platforms and the eBay Browse API (active only) | Periodic search snapshots. Deduplicate cross-posts with image hashes and embeddings. |
| New-listing rate | Inflow of supply per day | Partly, as a difference between snapshots | Snapshots |
| Sell-through rate (STR) | Sold ÷ (sold + unsold) over a window, or sold ÷ listed | eBay: Terapeak (UI) for ≤90 days [V]. Others: inferred from status changes, which is error-prone because delisting is not a sale [V, car study] | Terapeak manual or seller-account access. Own telemetry. |
| Days on market / time to sale | Listing date to sale date | Partly: sold date is visible on some platforms, listing date less often | Snapshots plus own listings |
| Views, likes, watchers, offers | Engagement intensity, the best leading indicator of demand **for a specific listing** | Like and favourite counts are publicly visible on some platforms [U: per-platform check needed]. Views, watchers and offer amounts are **seller-only** | **First-party via the users' own accounts**, the startup's key advantage. TRR and Airbnb both use views and favourites [V]. |
| Accepted-offer prices | True transaction price on offer-heavy platforms | Hidden on eBay, which shows a strikethrough list price. 130point and the "Alt" extension reveal it for US sales [V] (https://help.hobbydb.com/support/solutions/articles/36000343715-adding-ebay-best-offer-price-points) | Own accounts for your own sales. Third-party tools for others. |
| Search volume (web) | Google Trends | Yes. The **Google Trends API (alpha, July 2025)** offers a consistently scaled 1,800-day window, daily to yearly granularity, ISO-3166-2 regions, and access by application [V] (https://ppc.land/google-opens-alpha-testing-for-new-trends-api-targeting-developers-and-journalists/; https://developers.google.com/search/blog/2025/07/trends-api) | Apply for alpha access. |
| Platform search volume | Searches on Depop, eBay and others | No (internal). eBay sourcing insights show high-demand, low-supply categories for Store subscribers [V] | Your own app's search logs once the shop side exists |
| Seasonality | Week of year and weather (coats, swim) | Yes, derived | Learn from history; Airbnb trains with recency weighting for seasonality [V] |
| Trend shocks (TikTok, celebrity, creative-director change) | Sudden demand jumps. Examples: the Dior Saddle "Y2K revival", and interest in dead brands and pre-creative-change collections (TRR 2025) [S] (https://fashionunited.uk/news/business/between-attraction-and-speculation-the-real-return-on-it-bags-on-the-secondhand-market/2025092084015; https://realstyle.therealreal.com/the-real-real-2025-resale-report) | Partly (Trends; TikTok Creative Center hashtags [U]) | Anomaly detection on search and engagement z-scores per brand or model |
| Retail price and retail discounting | Original MSRP anchors the value. A current retail sale (for example 40% off in-season) caps resale for current-season items. ThredUp's merchants "periodically monitor market prices" to set estimated retail [V, 10-K] | Yes, from retailer sites, Google Shopping and affiliate feeds | Affiliate networks (CJ, Rakuten, Impact, Awin) and product feeds [U]. Chanel raised in-store prices 54% from 2019 to 2024, which lifts the resale anchor [S]. |
| Brand heat | Composite of search, engagement and price-index momentum | Third-party indices such as Lyst [U] | Build internally from the items above |
| Bid/ask depth (standardized SKUs) | Highest bid, lowest ask, last sale | Displayed on StockX and GOAT. No general public API [U]. Scraping is against their terms [U] | Partnership. Treat as a market-state feature for SKU items. |

**Takeaway.** The highest-value demand signals (views, watchers, likes, offers, accepted-offer prices) are seller-private. Because the agent operates each user's own accounts, you accumulate them across platforms. Few competitors can, apart from the platforms themselves.

---

## 4. Condition and attributes as price drivers (published evidence)

- **Condition**
  - Mercari Japan iPhone 7 hedonic: "some scratches" lowers list price by about 1,541 yen and "scratched" by about 3,437 yen, on a mean of about 14,494. That is roughly **−11% and −24%** [V] (https://arxiv.org/pdf/2602.13707).
  - Vinted guidance (see table): 60–80 / 40–60 / 20–40% of retail by condition tier [V].
  - KBB condition base rates of 2/28/50/20%: use them to sanity-check your condition-grade distribution and the inflation in seller self-reports [V].
  - Closo (reseller blog) claims items with tags hold **10–15 percentage points** more of retail than worn ones [S/U] (https://closo.co/blogs/inventory-liquidation/resale-price-vs-original).
- **Category and brand value retention**
  - Same Closo source: fast fashion 17–23%, Lululemon 35–45%, mid-tier bags 40–60%, mainstream sneakers 27–38%, hyped sneakers 110–200% of retail [S/U].
  - Vestiaire data via FashionUnited: Birkin pre-owned is about **56%** of current retail; Chanel Classic about 24%; Speedy about 27%; Dior Saddle about 27% (ratios are my derivation) [S].
  - StockX: average about 1.48× retail; 27.7% of orders below retail [V].
- **Size**
  - StockX 2013 deadstock on eBay (220k auctions, 517 shoes): the spread from best to worst size is **5.4%**. Size 13 is +3.5%; sizes 8 and 10 are about −1.9% [V] (https://stockx.com/news/do-sneaker-prices-vary-by-size-2/).
  - StockX 2016–19 multiples: men's size 16 is 1.86× and size 12.5 is 1.37×. Women's 7.5W is 1.16× vs 10.5W at 1.62×. Rare sizes sell at a premium where scarce and at a discount where demand is thin [V].
  - Model size as relative scarcity (share of supply ÷ share of demand), not as a raw number.
- **Completeness (box, tags, dust bag, receipts)**
  - Receipts and garage-kept mentions raise eBay Motors prices [V] (Lewis 2011, below).
  - PriceCharting treats loose, CIB and new as separate price series [U].
  - Proven elsewhere, untested for fashion: learn a multiplier per category.
- **Authentication**
  - eBay Authenticity Guarantee covers sneakers over $100 (2020) and later bags, watches and cards [S] (https://fashionunited.uk/news/fashion/ebay-to-start-authenticating-sneakers-over-100-dollars/2020101251581).
  - I found **no published causal estimate** of the authentication price premium. **This is a gap**: measure it yourself, with the same SKU sold with and without authentication.
  - Rebag Clair still needs humans to authenticate [V].
- **Photos and disclosure**
  - eBay Motors: around 9 to 10 photos, each extra photo is worth about **1.5–1.75%** of price, with diminishing returns. Sale probability rises about 0.25 points per photo (OLS). The IV estimate is smaller but positive [V] (https://dash.harvard.edu/bitstream/handle/1/4724767/lewis_asymmetricinformation.pdf?sequence=2).
  - Airbnb verified professional photos: **+8.98% occupancy** [V] (https://pubsonline.informs.org/doi/fpi/10.1287/mnsc.2021.4175).
  - Xianyu found text more predictive than images for price [V].
  - Implication: photo quality and count affect the probability of sale (hazard) more than value. Model them in the hazard model, and make "improve photos" a recommended action.
- **Platform effects**
  - VoucherCodes 2022: across 20 branded items on eBay, Depop and Vinted, eBay was cheapest 12 times. A Mulberry Darley ranged from £152 (eBay) to £345 (Vinted), a 127% gap [S] (https://fashionunited.uk/news/fashion/ebay-is-the-cheapest-resale-platform-data-shows/2022091365118). Those are active-listing prices, not sold prices.
  - Estimate platform fixed effects per segment from sold data, ideally from the startup's own cross-posted listings of the same item.
- **Fees and shipping**
  - Each $1 of eBay shipping lowers the sale price by about $0.82. Free shipping raises the total price paid by about $2.50 [V] (Einav et al. 2015).
  - Fee schedules and change dates:
    - Depop US: 0% seller fee and a buyer fee of up to 5% + $1 (2024-07-15) [V].
    - Mercari US: 10% seller plus 3.6% buyer (2025-01) [V].
    - eBay UK: no fees for private sellers (2024-10) [V] (https://www.euronews.com/2024/10/07/gloves-off-in-pre-loved-price-war-as-ebay-scraps-private-seller-fees).
    - Poshmark: 20% above $15 [S].
    - Grailed: 9% plus processing [S].
    - eBay US: about 13.25% FVF plus processing [S] (https://closo.co/blogs/inventory-liquidation/resell-websites).
    - Chairish: 20–40% [V].
  - Buyer-paid fees are not free to the seller. The Poshmark episode shows demand reacts strongly to them [V].

---

## 5. Evaluation: measuring pricing quality, and the pitfalls

### Metrics
- **Point accuracy vs realised price**, by tier (exact SKU, model, brand/category, unique) and by price decile:
  - MdAPE, or better **MdABRE** (symmetric) [V, REA paper]
  - RMSLE and MALE (comparable to Mercari and Xianyu)
  - Hit rates within 10% and 20% (Zestimate-style)
  - IAAO ratio-study analogues: median ratio of predicted to sold between 0.90 and 1.10; COD 5–15 for heterogeneous property, above 20 being poor; PRD 0.98–1.03 for vertical equity, meaning cheap items are not systematically over-predicted [V] (https://www.audits2.ga.gov/wp-content/uploads/2024/08/Standard_on_Ratio_Studies.pdf). PRB and PRD are especially useful because errors on $15 items behave differently from errors on $1,500 items.
- **Intervals:** empirical coverage at nominal 80%, both overall and conditional (by category, price decile, comp count and platform), plus median relative width. Coverage that is right but much too wide is useless. Track coverage-width curves.
- **Time to sale:**
  - Calibration of P(sold by 7, 30 and 60 days | price): reliability plots and Brier score/ECE
  - Concordance index (the car study reached 0.59–0.63) [V]
  - Integrated Brier score for full survival curves
- **Decision quality (Airbnb analogues)** [V]:
  - *Price-decrease recall*: share of listings that went unsold in 30 days for which the system recommended a price below the one shown.
  - *Sale regret*: for sold items, how far the recommendation was below the realised price. This captures leaving money on the table.
- **Business metrics (A/B, randomized by seller, not by listing, to avoid interference):**
  - Primary: **net seller proceeds per listed item at day 60**, counting unsold items at zero or at a liquidation value.
  - Secondary: sell-through at 30 and 60 days, median days to sale, seller adoption and override rate, cancellation and return rate, buyer conversion.
  - Guardrails: complaint rate, and lowball-offer rate on the shop side.

### Pitfalls
1. **Sold-only data is truncated in both directions.**
   - Sold items are the ones whose ask was at or below some buyer's willingness to pay, so they understate what a patient seller could get.
   - They also over-represent desirable, well-photographed, good-condition items, so they overstate the typical value of the type.
   - Fix: train with censored likelihoods and interval losses that include unsold and expired listings (Opendoor, Airbnb and Xianyu precedents) [V].
2. **Asking vs sold.**
   - Auction prices averaged 0.84 of the same seller's posted price [V].
   - Mercari Japan sale price is about 97% of list [V].
   - eBay Best Offer sold pages show the list price, not the accepted price [V]. eBay's own Price Guide uses accepted offers [V].
   - Never train a "sale price" model on asks without a learned ask-to-sale ratio per platform.
3. **Delisting is not a sale.** Status inferred from scraping is noisy. Prefer first-party outcomes, and run a robustness check on a sold-only sample (the car study's hazard ratio shifted from 0.836 to 0.941) [V].
4. **Cross-post duplication.** The same item listed on four platforms inflates supply counts and creates leakage between comps (it can appear as a comp for itself). Deduplicate with perceptual hashes and embeddings, and remove the item's own cross-posts from its comps.
5. **Time leakage.** Use chronological splits, so no future comps (REA, Opendoor) [V].
6. **Feedback loops (performative prediction).**
   - 1% of Zestimate moves list price by 0.73% and sale price by 0.08%, and Zestimates then retrain on those sales [V] (Fu, Jin, Liu, NBER w29880).
   - Model confidence becomes inflated over time [V] (Malik & Manzoor).
   - General framework: Perdomo et al., "Performative Prediction", ICML 2020 (https://proceedings.mlr.press/v119/perdomo20a.html) [V: citation].
   - Mitigations:
     - Keep a 5–10% **no-suggestion holdout** of sellers permanently.
     - Log the shown price and its propensity.
     - Inject small randomized list-price perturbations (for example ±3–5%) to keep identifying elasticity.
     - Use off-policy evaluation for new policies.
     - Never count "seller accepted our price and it sold" as proof the price was right.
7. **Non-stationarity.** Trend shocks and fee changes (Poshmark, Mercari, Depop) shift demand overnight. Monitor data distributions with Opendoor-style alerts [V], and use time-weighted conformal calibration.
8. **Heterogeneous effects.** Rue La La's tool lost revenue in the cheapest category while gaining 11–24% elsewhere [V]. Always report results by segment.

---

## 6. Data sources and access

| Source | Data | Access and licensing | Notes |
|---|---|---|---|
| **Own users' platform accounts** (agent-operated) | Full history of their listings, sales, accepted offers, views, watchers and likes; cross-platform outcomes for the same item | User-authorized. Logged-in use binds the account to platform ToS, so stay within normal user behaviour and rate limits [U, legal review] | **Highest-value dataset, and get it first.** Also use the price history of the items you cross-post. |
| eBay Marketplace Insights API | Sold-item history, recent window (about 90 days [U]) | **Limited Release**. Reportedly only for major partners [V] | Apply anyway through a partner or business development route. |
| eBay Browse API | Active listings, prices, item specifics | Standard developer access [U on quotas] | Supply-side snapshots |
| eBay Terapeak (Product Research) | 3 years of sold data, average and range, STR ≤90 days, seller count | Free in Seller Hub UI [V]. No public API [U] | Usable through the agent operating a user's Seller Hub, with the user's permission. Check the ToS. |
| eBay Price Guide | Cards only, accepted-offer medians, 2 years | Consumer UI [V] | Not relevant to fashion except as a design reference |
| 130point | Accepted Best Offer prices for US eBay sales | Free web tool [V] | Card-focused. Use the technique: fetch accepted price for an item ID. |
| WorthPoint | Aggregated sold prices for antiques, vintage and collectibles | Subscription. Commercial licensing unknown [U] | Fetch blocked this session |
| LiveAuctioneers price results | **About 29M hammer prices** since 1999 from thousands of houses: art, furniture, jewelry, fashion | Free research tool [V] (https://www.liveauctioneers.com/price-guide/). Bulk use needs licensing [U] | Key furniture and design comps source. Hammer price excludes buyer's premium [U]. |
| Invaluable price archive | Prices realized | Free for 12 months; Premium 5 years; Professional 15+ years [V] (https://www.invaluable.com/inv/help/faq/search-price-archive/) | License for bulk use |
| Heritage Auctions archive | Prices realized with images | Free registration [U] | Luxury handbags and watches |
| StockX / GOAT | Bid/ask, last sale, by size | No general public market-data API. Seller tools exist. Scrapers exist (Apify) but carry ToS risk [U] | Seek a partnership for SKU-level items. |
| Depop Partner API | "Pricing Inspiration" range plus similar sold items | Partner API documentation exists [V]. Eligibility unknown [U] | Ask for partner access. It is cheap market data if granted. |
| Poshmark / Mercari / Grailed / Depop sold listings on the web | Sold prices (list price shown; offers hidden) | Public pages, ToS restrictions. Meta v. Bright Data (N.D. Cal., 2024-01-23): logged-off scraping of public data did not breach Meta's terms, but the ruling is narrow [V] (https://www.quinnemanuel.com/the-firm/news-events/client-alert-what-does-the-meta-v-bright-data-summary-judgment-ruling-mean-for-web-scraping/) | Get legal advice. Prefer partnerships and first-party data. |
| Vinted | Active catalogue; no sold search [U] | Public pages | Supply only |
| 1stDibs / Chairish | Active listings; 1stDibs Insider pricing index for sellers [V] | Seller access through the user's account | Price parity applies [V]. |
| Retail feeds | MSRP, current retail price and discount state | Affiliate networks (CJ, Rakuten, Impact, Awin) and Google Shopping APIs or SERP vendors [U] | Needed for the retail anchor and "retail on sale" detection |
| Google Trends API (alpha) | Consistently scaled search interest, 5-year window, by region | Application-based alpha [V] | Brand and model heat |
| Kaggle Mercari dataset | 1.4M listings (2018) | Competition data license [U] | Pretraining and benchmarking only. Stale. |

---

## 7. Recommended pricing system

### 7.1 Outputs (per item × channel)
- **Expected sale price V̂**, which is net-of-fees, landed value to the buyer. Also report expected proceeds to the seller.
- **80% interval** for sale price given a sale, calibrated with CQR.
- **Time-to-sell curve**: P(sold by 7, 14, 30, 60 days | list price) and expected days to sale.
- **List price** (the anchor), **hidden floor** (auto-decline threshold) and **auto-accept threshold**.
- A **markdown plan**: decision checkpoints, not a fixed schedule.
- A **confidence tier** (A: exact SKU with dense comps → D: unique with no comps) and a short rationale citing the 3–5 comps used.
- **Buyer side:** a fair-price score, the percentile of a listing's price within the predicted sale-price distribution for that identity, condition and channel. Show "great deal" only when the price sits below the lower interval bound **and** identity confidence is high. That rule protects against fakes and misidentification.

### 7.2 Model structure (pipeline)

**Stage 0: Identity resolution.**
- A VLM reads photos (labels, tags, style codes, logos, hardware, construction) and the seller's text. It outputs a canonical identity at the deepest level reachable, with a match probability:
  - exact SKU (style code, colourway, size)
  - model/line
  - brand × category × attributes
  - category only
- For furniture: maker or designer attribution, model, period, material and dimensions. Attribution confidence is critical, since "attributed to" vs "signed" can mean a 10× price difference [U].
- Gate on confidence, as Xianyu's "qualified for suggestion" classifier does [V]. Below the threshold, ask one targeted question, such as "photo of inside label" or "style code".

**Stage 1: Comps retrieval (hybrid).**
- Exact-ID matching, plus attribute filters, plus kNN on image and text embeddings. Learn the retriever end to end later, as in the REA paper [V].
- Pools:
  - sold, up to 12–24 months with recency weights
  - unsold or expired, treated as censored
  - active, as weak bounds and as supply
  - auction results, for furniture and luxury
- Normalize every comp to buyer-landed price in the target currency. Separate shipping. Convert asks to an expected sale price with platform-specific ratios. Time-adjust with segment indices (Stage 4).
- Deduplicate cross-posts and drop the item's own copies.

**Stage 2: Base value (hierarchical Bayesian blend).**
- V_base = posterior mean of log value. Components:
  1. A weighted-comps estimate. Weights come from learned similarity, recency and condition distance (Opendoor/REA style).
  2. A global hedonic GBM/NN prior using brand, category, retail price, age, materials and text and image embeddings.
  3. A hierarchical prior over SKU → model → brand × category → category.
- The weight on comps grows with effective comp count and similarity, and the weight on priors grows when comps are sparse. MMR's minimum thresholds (≥6 in a year, ≥2 in 90 days) are a sensible starting rule for the "dense comps" tier [V].
- Optional LLM-reasoning layer (LLP pattern) for explanations and edge cases. Bound its adjustment to ±x% of the statistical estimate and discard high-uncertainty outputs [V].

**Stage 3: Condition and attribute adjustments.**
- Multiplicative log-additive factors, learned within identity clusters so that brand and model effects do not leak in:
  - condition grade (a 5-level scale with a defect taxonomy, graded from photos and reconciled with the seller's claim)
  - size scarcity
  - completeness (box, tags, dust bag, receipts)
  - authentication status
  - age/season
- Start from hand-specified priors: Vinted's percent-of-retail by condition; Mercari's −11% and −24% for scratch levels as a hardgoods prior. Learn the deltas from your data.
- Photo quality and count go mainly into the **hazard** model (Lewis, Airbnb evidence) [V].

**Stage 4: Market-state adjustment.** Per segment (brand × category × region × channel):
- Index momentum: a hedonic time-dummy index and a repeat-SKU index where they exist.
- Months of supply = active ÷ sales rate.
- STR, new-listing rate and search-trend z-score (Google Trends).
- Retail state (in-season and on-sale at retail?) and seasonality.
- These enter (a) as small, capped shifts to V, for example at most ±10% unless an index-backed segment says otherwise, and (b) as features in the hazard model. Supply and demand mostly change **speed at a given price**; level shifts should come from realized-price indices.

**Stage 5: Sale-hazard model (time to sell).**
- A discrete-time daily hazard: h(t) = σ(g(relative price r = p/V̂, days listed, price-change history, item, photo and listing quality, channel, market state, engagement to date)).
- Train on **all** listings, with unsold ones censored (Opendoor) [V]. Use GBM first, and later a neural survival model or RSF to capture the steep penalty for overpricing [V].
- From this, compute P(sale by T | p) for any candidate p.

**Stage 6: Channel module.** Per platform:
- Fee function (seller and buyer fees) and shipping cost and its pass-through (about 80% on eBay) [V].
- Platform price level and offer culture: the expected discount from list, offer frequency, and Poshmark offers to likers.
- Audience fit (hazard multiplier) and policy constraints (1stDibs price parity; eBay Authenticity Guarantee thresholds).
- Logistics for furniture: local pickup vs freight. Freight can exceed fees, so model the regional pickup radius.

**Stage 7: Price-policy optimizer.**
- Seller goals: Fast / Balanced / Max, set as a daily patience cost δ or a target date.
- Solve a small dynamic program over checkpoints (day 0, 3, 7, 14, 21, 30, 45, 60): maximize Σ_t S(t−1)·h(t|p_t)·NetProceeds(p_t) − holding cost.
- Outputs:
  - **List price** = the optimal anchor plus a platform-specific offer cushion, with rounding rules. Avoid round-number prices when patience is high; they signal impatience and cost 5–8% [V].
  - **Floor** = the reservation value: the price at which accepting now equals the continuation value of waiting. Never below the seller's stated minimum.
  - **Auto-accept** = the price above which continuation value is lower.
  - **Expected price and interval** from Stage 2/3 with CQR.
  - **Expected days to sale** from Stage 5.
- For genuinely unique items in tier D, the optimizer may choose a price-discovery mechanism: an eBay auction with a reserve equal to the floor (auctions are favoured for unique items [V]), or a descending-price path.

**Stage 8: Updating and markdowns (demand-driven).**
- Treat each listing as a Bayesian learning problem about its own latent value and demand. Evidence:
  - Engagement vs expectation: views, likes and watchers relative to what comparable items at that relative price and age receive. Under-engagement lowers the posterior value or the hazard.
  - Offers: each offer is a lower bound on one buyer's willingness to pay. The offer distribution updates the value posterior directly.
  - Time without sale: censoring evidence.
  - Market-state changes.
- Actions at each checkpoint, in order of preference:
  1. **Targeted private offers** to likers and watchers. These discriminate on price and avoid teaching the public to wait [V randomized-markdown evidence]. Respect platform minimums (Poshmark ≥10%).
  2. **Listing-quality fixes**: photos, title and item specifics. These raise the hazard without cutting price.
  3. **Public price drops** sized to cross notification thresholds and search price buckets.
  4. **Channel moves**: add or remove platforms, or move to auction.
- Use small randomized variation in step size and timing, with logged propensities, for continuous elasticity learning (Uber-style identification, ThredUp-style bandits) [V].

### 7.3 Learn vs hand-specify

| Component | Hand-specify (v0) | Learn (v1+) |
|---|---|---|
| Identity taxonomy, condition scale, defect taxonomy | Yes. Fixed schema, KBB-like grade definitions | VLM grader trained on labelled photos |
| Comp similarity | Rules: same SKU > same model > same brand × category, plus recency decay | Learned retriever and weights (REA, Opendoor) |
| Condition, size and completeness multipliers | Priors (Vinted ranges, Mercari scratch deltas) | Within-cluster estimates with shrinkage |
| Ask-to-sale ratio per platform | Start at 0.90–0.97 [U] | From accepted-offer data in own accounts |
| Fees, shipping, parity rules | Yes (tables) | No |
| Hazard model | None (needs data). Use a logistic curve in r with per-segment slopes from eBay evidence as a placeholder | GBM discrete-time hazard |
| Market-state effects | Caps and directions only | Learned coefficients |
| Markdown policy | Rule-based checkpoints and thresholds | DP over the learned hazard; later contextual bandits |
| Seller patience | User setting | Inferred from behaviour |

### 7.4 Cold start: items with no comps
1. **Climb the hierarchy.** SKU → model → brand × category × attributes → category. Widen the interval as you go up, and tag the tier.
2. **Retail-anchor prior.** Estimated retail × retention curve, where retention depends on brand and category, condition (Vinted ranges), age, and retail-sale status. Find retail via image search and product feeds.
3. **Embedding neighbours in a broader space**: visually and textually similar items across brands, adjusted by brand-level price ratios.
4. **LLM prior** with retrieval, used only when its uncertainty is low. Never let it be the sole basis for tier A or B labels.
5. **Price discovery by mechanism.**
   - Start near the upper interval with a planned descending path, or run an auction with a reserve equal to the floor for unique items.
   - Use offers as a discovery channel.
   - Cross-post to several platforms at once and read the engagement signal within 72 hours.
6. **Ask the seller for one high-value fact**: original price, style code, receipt or designer signature.
7. **Furniture specifics.** Weight auction results (LiveAuctioneers, Invaluable) heavily. Separate attribution levels. Include freight and pickup radius. Expect long horizons (weeks to months).

### 7.5 Avoiding Zillow-style adverse selection
- **Do not take inventory or guarantee prices at launch.** The agent/consignment model means sellers keep the price risk, which is structurally safe. Revenue-share or consignment contracts reduce selection [V].
- If you later offer "instant cash" or guaranteed sale:
  - Offer = lower quantile (for example q10–q20) of net proceeds minus holding and margin.
  - Offer only for tier A/B items with narrow intervals and P(sale within 30 days) above some threshold. This mirrors iBuyers only buying liquid, easy-to-value homes [V].
  - **Monitor acceptance rate** as a selection alarm. Zillow's jump to 74% acceptance vs a 50–60% target preceded the losses [V]. Rising acceptance means you are over-paying.
  - Require photo or physical inspection for condition, since sellers know defects you can't see (the "soft information" gap: 80% vs 68% R²) [V].
  - Don't override the model for growth (the Project Ketchup lesson) [V].
- **Buying-agent winner's curse.** If the shop or buying agent hunts "underpriced" listings, it will pick listings where your model overestimates value. Shrink estimates toward priors, require the discount to exceed k·σ, and weight by identity confidence (fakes look like bargains).
- **Selection in your training data.** Users may route easy items to you and sell hard items elsewhere, or the reverse. Track what share of each user's inventory flows through you, and reweight.

### 7.6 Evaluation plan and targets

**Proposed targets.** These are not benchmarks from literature. They are informed by Zestimate, Xianyu and Mercari results.

| Tier | Example | Offline MdABRE target (v1) | Within 20% hit rate |
|---|---|---|---|
| A: exact SKU, dense comps | Sneaker or bag with style code; branded chair model | ≤ 10–12% | ≥ 80% |
| B: model level | "Lululemon Align 25in, size 6" | ≤ 18–22% | ≥ 60% |
| C: brand × category | "Reformation midi dress" | ≤ 25–30% | ≥ 45% |
| D: unique / no comps | Vintage no-label; unattributed furniture | ≤ 35–40%, wide intervals and a discovery mechanism | n/a |

- **Intervals:** 80% nominal → 77–83% empirical in every tier, price decile and platform cell with n ≥ 200. Track median width.
- **Time to sale:** ECE < 3 points for P(sold by 30 days). C-index ≥ 0.65 (the car study managed 0.59–0.63 with less information).
- **Vertical equity:** PRD 0.98–1.03 and PRB within ±0.05 (IAAO bands) [V].
- **Online A/B:**
  - Randomize by seller. Primary metric: net proceeds per listed item at day 60.
  - Pre-register a minimum detectable effect, for example +5%. The Airbnb (+8.6%) and Rue La La (+9.7%) effect sizes suggest this is plausible.
  - Secondary: sell-through at 30 days, days to sale, override rate.
  - Keep the permanent holdout of 5–10% with no suggestions.
- **Backtest protocol:** rolling-origin time splits (train to month m, test m+1). No future comps. Deduplicate cross-posts. Report results by tier and segment.

### 7.7 What data to get first (priority order)
1. **First-party telemetry schema from day one.** For every agent-operated listing on every platform, log:
   - shown suggestion, list price, every price change, views, likes, watchers
   - every offer (amount and time) and the response
   - accepted price, fees, shipping, outcome, and days to sale
   - photos and condition grade
   - randomization flags and propensities

   This is the moat and fixes the asking-vs-sold, survivorship and engagement gaps.
2. **Sold comps for fashion:** eBay (apply for Marketplace Insights and use Terapeak through users' Seller Hub with permission), Poshmark, Mercari, Grailed and Depop sold pages. Get legal review first.
3. **Retail anchor:** affiliate product feeds and Google Shopping for MSRP and current discount state.
4. **Labelled condition dataset:** a few thousand items graded by experts on your 5-level scale with defect tags, to train the VLM grader and calibrate it against seller self-reports.
5. **Market-state feeds:** daily active-listing snapshots per identity cluster (supply), and Google Trends API access.
6. **Furniture comps:** LiveAuctioneers and Invaluable price archives (license), plus Chairish and 1stDibs actives.
7. **Partnerships:** Depop Partner API (Pricing Inspiration), StockX/GOAT for SKU market data, WorthPoint for vintage.

### 7.8 Build sequence
- **Weeks 0–6:** identity v0 (VLM + embedding retrieval); rule-weighted comps; hedonic GBM prior; Vinted-prior condition multipliers; heuristic hazard and fee tables; list/floor/interval with split conformal; full telemetry logging; a fixed-checkpoint markdown with private offers first.
- **Months 2–4:** CQR intervals by tier; discrete-time hazard GBM trained on own data plus scraped censored listings; learned ask-to-sale ratios per platform; buyer-side fair-price score with confidence gating; seller-randomized A/B and holdout.
- **Months 4–9:** learned retriever; LLM-reasoning layer (LLP-style), bounded and gated; DP markdown optimizer; contextual-bandit exploration on step sizes; segment indices; furniture module.

---

## 8. Open gaps and unverified items
- No causal published estimate of the **authentication premium** or of the **NWT premium** for fashion; the Closo 10–15 points is unverified. Measure both.
- WorthPoint, PriceCharting and Heritage methods and licensing are unverified (fetch blocked or not attempted).
- The eBay Marketplace Insights window (about 90 days) and fields are unverified.
- Uber elasticity values (−0.4 to −0.6) and Mercari Kaggle's exact winning score are from memory.
- The thresholds behind Xianyu LLP's SAR/DAR accuracy metrics were not extracted.
- Which platforms publicly expose like or favourite counts needs a per-platform check.
- Legal: scraping and agent-operated-account ToS exposure need counsel; Meta v. Bright Data is narrow.
