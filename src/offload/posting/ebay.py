"""eBay through its official seller APIs, acting with the user's own OAuth consent.

Written against eBay's public API docs (Inventory, Taxonomy, Negotiation, Fulfillment REST APIs and
Trading API for incoming Best Offers). NOT yet exercised against the sandbox: do that before use.

Prerequisites per user: an OAuth refresh token (sell.inventory, sell.account, sell.fulfillment,
sell.negotiation scopes), business policies (fulfillment / payment / return) and an inventory location.
Images must be public HTTPS URLs (our photo storage), not local files.
"""

from __future__ import annotations

import base64
import os
import time
import uuid
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx

from ..negotiation.models import Decision, Offer
from .base import Event, OfferEvent, PlatformListing, SaleEvent

HOSTS = {"production": "https://api.ebay.com", "sandbox": "https://api.sandbox.ebay.com"}
SCOPES = " ".join(
    f"https://api.ebay.com/oauth/api_scope/{s}"
    for s in ("sell.inventory", "sell.account", "sell.fulfillment", "sell.negotiation")
)

# Our condition -> eBay ConditionEnum. Valid values depend on the category.
# Clothing, shoes & accessories accept NEW, NEW_OTHER, NEW_WITH_DEFECTS, PRE_OWNED_EXCELLENT,
# USED_EXCELLENT (shown as "Pre-owned - Good") and PRE_OWNED_FAIR. Check with the Metadata API per category.
FASHION_CONDITION = {
    "new_with_tags": "NEW",
    "new_without_tags": "NEW_OTHER",
    "like_new": "PRE_OWNED_EXCELLENT",
    "very_good": "PRE_OWNED_EXCELLENT",
    "good": "USED_EXCELLENT",
    "fair": "PRE_OWNED_FAIR",
    "poor": "PRE_OWNED_FAIR",
    "unknown": "USED_EXCELLENT",
}
FASHION_CATEGORIES = {"apparel", "footwear", "bags", "accessories"}
CONDITION = {
    "new_with_tags": "NEW",
    "new_without_tags": "NEW_OTHER",
    "like_new": "USED_EXCELLENT",
    "very_good": "USED_VERY_GOOD",
    "good": "USED_GOOD",
    "fair": "USED_ACCEPTABLE",
    "poor": "FOR_PARTS_OR_NOT_WORKING",
    "unknown": "USED_GOOD",
}
ASPECT_NAMES = {"brand": "Brand", "model": "Model", "size": "Size", "color": "Color", "material": "Material",
                "style_code": "Style Code", "gender": "Department"}
DEPARTMENT = {"Men's": "Men", "Women's": "Women", "Unisex": "Unisex Adults", "Boys'": "Boys", "Girls'": "Girls", "Baby": "Baby"}


def ebay_condition(category: str, condition: str) -> str:
    table = FASHION_CONDITION if category in FASHION_CATEGORIES else CONDITION
    return table.get(condition, table["unknown"])


def _ebay_time(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _money(cents: int) -> dict:
    return {"currency": "USD", "value": f"{cents / 100:.2f}"}


@dataclass
class EbayAdapter:
    client_id: str
    client_secret: str
    refresh_token: str
    fulfillment_policy_id: str
    payment_policy_id: str
    return_policy_id: str
    merchant_location_key: str
    env: str = "production"
    http: httpx.Client = field(default_factory=lambda: httpx.Client(timeout=30))
    name: str = "ebay"
    _token: str | None = None
    _token_exp: float = 0.0

    @classmethod
    def from_env(cls, **policies: str) -> "EbayAdapter":
        return cls(
            os.environ["EBAY_CLIENT_ID"], os.environ["EBAY_CLIENT_SECRET"], os.environ["EBAY_USER_REFRESH_TOKEN"],
            env=os.environ.get("EBAY_ENV", "sandbox"), **policies,
        )

    # ---------- plumbing ----------
    @property
    def host(self) -> str:
        return HOSTS[self.env]

    def _access_token(self) -> str:
        if self._token and time.time() < self._token_exp - 60:
            return self._token
        basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        r = self.http.post(
            f"{self.host}/identity/v1/oauth2/token",
            headers={"Authorization": f"Basic {basic}", "Content-Type": "application/x-www-form-urlencoded"},
            data={"grant_type": "refresh_token", "refresh_token": self.refresh_token, "scope": SCOPES},
        )
        r.raise_for_status()
        body = r.json()
        self._token, self._token_exp = body["access_token"], time.time() + int(body.get("expires_in", 7200))
        return self._token

    def _req(self, method: str, path: str, **kw) -> httpx.Response:
        headers = {"Authorization": f"Bearer {self._access_token()}", "Content-Language": "en-US",
                   "Accept-Language": "en-US", **kw.pop("headers", {})}
        r = self.http.request(method, f"{self.host}{path}", headers=headers, **kw)
        if r.status_code >= 400:
            raise RuntimeError(f"eBay {method} {path} -> {r.status_code}: {r.text[:500]}")
        return r

    def _trading(self, call: str, body: str) -> ET.Element:
        xml = f'<?xml version="1.0" encoding="utf-8"?><{call}Request xmlns="urn:ebay:apis:eBLBaseComponents">{body}</{call}Request>'
        r = self.http.post(
            f"{self.host}/ws/api.dll",
            headers={"X-EBAY-API-CALL-NAME": call, "X-EBAY-API-SITEID": "0", "X-EBAY-API-COMPATIBILITY-LEVEL": "1193",
                     "X-EBAY-API-IAF-TOKEN": self._access_token(), "Content-Type": "text/xml"},
            content=xml.encode(),
        )
        r.raise_for_status()
        root = ET.fromstring(r.text)
        ns = {"e": "urn:ebay:apis:eBLBaseComponents"}
        if root.findtext("e:Ack", namespaces=ns) not in ("Success", "Warning"):
            raise RuntimeError(f"eBay {call} failed: {r.text[:500]}")
        return root

    # ---------- listing ----------
    def suggest_category(self, query: str) -> str:
        r = self._req("GET", "/commerce/taxonomy/v1/category_tree/0/get_category_suggestions", params={"q": query})
        return r.json()["categorySuggestions"][0]["category"]["categoryId"]

    def create_listing(self, listing: dict, *, photos: list[str]) -> PlatformListing:
        if "floor_cents" in listing:
            raise ValueError("the hidden minimum must never be sent to a platform")
        if not photos or not all(p.startswith("https://") for p in photos):
            raise ValueError("eBay needs public https image URLs")
        sku = listing.get("sku") or f"off-{uuid.uuid4().hex[:16]}"
        pkg = listing.get("package") or {}
        aspects = {
            ASPECT_NAMES[k]: [DEPARTMENT.get(v, v) if k == "gender" else v]
            for k, v in listing.get("attributes", {}).items() if k in ASPECT_NAMES
        }
        item = {
            "availability": {"shipToLocationAvailability": {"quantity": 1}},
            "condition": ebay_condition(listing.get("category", ""), listing["condition"]),
            "product": {"title": listing["title"][:80], "description": listing["description"], "aspects": aspects, "imageUrls": photos[:24]},
        }
        if pkg:
            item["packageWeightAndSize"] = {
                "dimensions": {"length": pkg["length_in"], "width": pkg["width_in"], "height": pkg["height_in"], "unit": "INCH"},
                "weight": {"value": pkg["weight_lb"], "unit": "POUND"},
            }
        self._req("PUT", f"/sell/inventory/v1/inventory_item/{sku}", json=item)

        terms = listing.get("best_offer") or {}
        policies = {
            "fulfillmentPolicyId": self.fulfillment_policy_id,
            "paymentPolicyId": self.payment_policy_id,
            "returnPolicyId": self.return_policy_id,
        }
        if terms:
            # eBay handles the edges natively; our engine handles the middle via the Trading API.
            policies["bestOfferTerms"] = {
                "bestOfferEnabled": True,
                "autoAcceptPrice": _money(terms["auto_accept_cents"]),
                "autoDeclinePrice": _money(terms["auto_decline_cents"]),
            }
        offer = {
            "sku": sku,
            "marketplaceId": "EBAY_US",
            "format": "FIXED_PRICE",
            "availableQuantity": 1,
            "categoryId": listing.get("ebay_category_id") or self.suggest_category(listing.get("search_query") or listing["title"]),
            "listingDescription": listing["description"],
            "listingPolicies": policies,
            "pricingSummary": {"price": _money(listing["price_cents"])},
            "merchantLocationKey": self.merchant_location_key,
        }
        offer_id = self._req("POST", "/sell/inventory/v1/offer", json=offer).json()["offerId"]
        listing_id = self._req("POST", f"/sell/inventory/v1/offer/{offer_id}/publish").json()["listingId"]
        return PlatformListing("ebay", listing_id, f"https://www.ebay.com/itm/{listing_id}", listing["price_cents"],
                               extra={"sku": sku, "offer_id": offer_id})

    def update_price(self, listing: PlatformListing, price_cents: int) -> None:
        r = self._req("POST", "/sell/inventory/v1/bulk_update_price_quantity", json={"requests": [{
            "sku": listing.extra["sku"],
            "offers": [{"offerId": listing.extra["offer_id"], "availableQuantity": 1, "price": _money(price_cents)}],
        }]})
        # HTTP 200 can still carry per-offer failures.
        for resp in (r.json() or {}).get("responses", []):
            if resp.get("statusCode") not in (200, None) or resp.get("errors"):
                raise RuntimeError(f"eBay rejected the price update: {resp}")
        listing.price_cents = price_cents

    def delist(self, listing: PlatformListing) -> None:
        self._req("POST", f"/sell/inventory/v1/offer/{listing.extra['offer_id']}/withdraw")
        listing.status = "delisted"

    # ---------- offers and sales ----------
    def poll(self, listing: PlatformListing, since: datetime | None) -> list[Event]:
        events: list[Event] = []
        root = self._trading("GetBestOffers", f"<ItemID>{listing.listing_id}</ItemID><BestOfferStatus>Active</BestOfferStatus>")
        ns = {"e": "urn:ebay:apis:eBLBaseComponents"}
        for bo in root.iterfind(".//e:BestOffer", ns):
            events.append(OfferEvent(listing.listing_id, Offer(
                id=f"ebay-{bo.findtext('e:BestOfferID', namespaces=ns)}",
                platform="ebay",
                buyer_id=bo.findtext("e:Buyer/e:UserID", default="unknown", namespaces=ns),
                amount_cents=round(float(bo.findtext("e:Price", default="0", namespaces=ns)) * 100),
                received_at=datetime.now(timezone.utc),
                message=bo.findtext("e:BuyerMessage", default="", namespaces=ns),
                binding=True,  # an accepted eBay Best Offer commits the buyer to pay
                buyer_completed_purchases=int(bo.findtext("e:Buyer/e:FeedbackScore", default="0", namespaces=ns) or 0),
            )))
        params = {"limit": 200}
        if since:
            params["filter"] = f"creationdate:[{_ebay_time(since)}..]"
        orders = self._req("GET", "/sell/fulfillment/v1/order", params=params).json().get("orders", [])
        for o in orders:
            if (o.get("cancelStatus") or {}).get("cancelState") in ("CANCELED", "IN_PROGRESS"):
                continue
            for li in o.get("lineItems", []):
                if li.get("legacyItemId") == listing.listing_id:
                    cost = li.get("lineItemCost") or li["total"]  # item price, excluding shipping and tax
                    events.append(SaleEvent(listing.listing_id, "ebay", o.get("buyer", {}).get("username", "unknown"),
                                            round(float(cost["value"]) * 100), datetime.now(timezone.utc), o.get("orderId")))
        return events

    def respond_to_offer(self, listing: PlatformListing, offer: Offer, decision: Decision, message: str) -> None:
        action = {"accept": "Accept", "decline": "Decline", "counter": "Counter"}[decision.action]
        body = (f"<ItemID>{listing.listing_id}</ItemID><BestOfferID>{offer.id.removeprefix('ebay-')}</BestOfferID>"
                f"<Action>{action}</Action><SellerResponse>{_xml_escape(message[:500])}</SellerResponse>")
        if decision.action == "counter":
            body += f'<CounterOfferPrice currencyID="USD">{decision.amount_cents / 100:.2f}</CounterOfferPrice><CounterOfferQuantity>1</CounterOfferQuantity>'
        self._trading("RespondToBestOffer", body)

    def send_offer_to_interested(self, listing: PlatformListing, price_cents: int, message: str, days: int = 2) -> None:
        """Negotiation API: offer a discount to watchers / cart holders (seller-initiated offers)."""
        self._req("POST", "/sell/negotiation/v1/send_offer_to_interested_buyers",
                  headers={"X-EBAY-C-MARKETPLACE-ID": "EBAY_US"},
                  json={"allowCounterOffer": True, "message": message[:2000], "offerDuration": {"unit": "DAY", "value": days},
                        "offeredItems": [{"listingId": listing.listing_id, "price": _money(price_cents), "quantity": 1}]})

    def send_message(self, listing: PlatformListing, thread_id: str, text: str) -> None:
        raise NotImplementedError("buyer messaging on eBay goes through the browser adapter for now")


def _xml_escape(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
