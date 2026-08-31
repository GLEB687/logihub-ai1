from __future__ import annotations

import math
from datetime import date, timedelta

import streamlit as st
from streamlit.components.v1 import html as components_html


st.set_page_config(
    page_title="LogiHub AI — Freight comparison",
    page_icon="🚚",
    layout="wide",
)


# -----------------------------------------------------------------------------
# Demo data
# -----------------------------------------------------------------------------

CITIES = {
    "Germany": {
        "Berlin": (52.5200, 13.4050),
        "Hamburg": (53.5511, 9.9937),
        "Munich": (48.1351, 11.5820),
        "Frankfurt": (50.1109, 8.6821),
        "Cologne": (50.9375, 6.9603),
    },
    "Netherlands": {
        "Amsterdam": (52.3676, 4.9041),
        "Rotterdam": (51.9244, 4.4777),
        "Eindhoven": (51.4416, 5.4697),
    },
    "Belgium": {
        "Brussels": (50.8503, 4.3517),
        "Antwerp": (51.2194, 4.4025),
        "Ghent": (51.0543, 3.7174),
    },
    "France": {
        "Paris": (48.8566, 2.3522),
        "Lyon": (45.7640, 4.8357),
        "Marseille": (43.2965, 5.3698),
    },
    "Poland": {
        "Warsaw": (52.2297, 21.0122),
        "Poznan": (52.4064, 16.9252),
        "Wroclaw": (51.1079, 17.0385),
    },
    "Austria": {
        "Vienna": (48.2082, 16.3738),
        "Salzburg": (47.8095, 13.0550),
        "Graz": (47.0707, 15.4395),
    },
    "Czechia": {
        "Prague": (50.0755, 14.4378),
        "Brno": (49.1951, 16.6068),
        "Ostrava": (49.8209, 18.2625),
    },
    "Italy": {
        "Milan": (45.4642, 9.1900),
        "Turin": (45.0703, 7.6869),
        "Rome": (41.9028, 12.4964),
    },
    "Spain": {
        "Barcelona": (41.3874, 2.1686),
        "Madrid": (40.4168, -3.7038),
        "Valencia": (39.4699, -0.3763),
    },
    "Switzerland": {
        "Zurich": (47.3769, 8.5417),
        "Basel": (47.5596, 7.5886),
        "Geneva": (46.2044, 6.1432),
    },
}


# Real European carrier profiles. Prices, availability and reliability remain
# independent LogiHub estimates because public carrier websites do not expose a
# single live tariff table for every route, cargo type and service combination.
CARRIERS = [
    {
        "name": "DHL Freight",
        "service": "DHL Road Freight Priority / Standard",
        "logo": "DHL",
        "logo_url": "https://www.google.com/s2/favicons?domain=dhl.com&sz=128",
        "source_url": "https://www.dhl.com/de-en/home/freight/european-road-freight.html",
        "rating": 96,
        "base_fee": 290,
        "km_rate": 0.76,
        "kg_rate": 0.052,
        "fuel_rate": 0.16,
        "speed_factor": 1.15,
        "modes": ["Road", "Rail", "Air"],
        "customs": True,
        "insurance": True,
        "door": True,
        "hazardous": True,
        "temperature": True,
        "color": "#D40511",
    },
    {
        "name": "DSV Road",
        "service": "DSV Groupage",
        "logo": "DSV",
        "logo_url": "https://www.google.com/s2/favicons?domain=dsv.com&sz=128",
        "source_url": "https://www.dsv.com/en/our-solutions/modes-of-transport/road-transport/groupage",
        "rating": 95,
        "base_fee": 265,
        "km_rate": 0.72,
        "kg_rate": 0.050,
        "fuel_rate": 0.15,
        "speed_factor": 1.10,
        "modes": ["Road", "Rail", "Air", "Sea"],
        "customs": True,
        "insurance": True,
        "door": True,
        "hazardous": True,
        "temperature": True,
        "color": "#E30613",
    },
    {
        "name": "DACHSER",
        "service": "DACHSER European Logistics",
        "logo": "DAC",
        "logo_url": "https://www.google.com/s2/favicons?domain=dachser.com&sz=128",
        "source_url": "https://www.dachser.com/en/european-logistics-51",
        "rating": 95,
        "base_fee": 250,
        "km_rate": 0.69,
        "kg_rate": 0.047,
        "fuel_rate": 0.14,
        "speed_factor": 1.08,
        "modes": ["Road", "Rail"],
        "customs": True,
        "insurance": True,
        "door": True,
        "hazardous": True,
        "temperature": True,
        "color": "#F6A800",
    },
    {
        "name": "Rhenus Logistics",
        "service": "Rhenus Road Freight Groupage",
        "logo": "RH",
        "logo_url": "https://www.google.com/s2/favicons?domain=rhenus.group&sz=128",
        "source_url": "https://www.rhenus.group/de/en/road-transport/",
        "rating": 93,
        "base_fee": 235,
        "km_rate": 0.66,
        "kg_rate": 0.045,
        "fuel_rate": 0.14,
        "speed_factor": 1.02,
        "modes": ["Road", "Rail", "Sea"],
        "customs": True,
        "insurance": True,
        "door": True,
        "hazardous": True,
        "temperature": True,
        "color": "#003B5C",
    },
    {
        "name": "Hellmann Worldwide Logistics",
        "service": "Hellmann Roadfreight",
        "logo": "HWL",
        "logo_url": "https://www.google.com/s2/favicons?domain=hellmann.com&sz=128",
        "source_url": "https://www.hellmann.com/en/products/roadfreight",
        "rating": 94,
        "base_fee": 245,
        "km_rate": 0.68,
        "kg_rate": 0.048,
        "fuel_rate": 0.15,
        "speed_factor": 1.07,
        "modes": ["Road", "Rail", "Air", "Sea"],
        "customs": True,
        "insurance": True,
        "door": True,
        "hazardous": True,
        "temperature": True,
        "color": "#E2231A",
    },
    {
        "name": "Kuehne+Nagel",
        "service": "Kuehne+Nagel Road Logistics",
        "logo": "K+N",
        "logo_url": "https://www.google.com/s2/favicons?domain=kuehne-nagel.com&sz=128",
        "source_url": "https://home.kuehne-nagel.com/en/services/road-transport",
        "rating": 96,
        "base_fee": 285,
        "km_rate": 0.74,
        "kg_rate": 0.053,
        "fuel_rate": 0.15,
        "speed_factor": 1.12,
        "modes": ["Road", "Rail", "Air", "Sea"],
        "customs": True,
        "insurance": True,
        "door": True,
        "hazardous": True,
        "temperature": True,
        "color": "#004B8D",
    },
    {
        "name": "Girteka Logistics",
        "service": "Girteka European FTL",
        "logo": "GIR",
        "logo_url": "https://www.google.com/s2/favicons?domain=girteka.eu&sz=128",
        "source_url": "https://www.girteka.eu/",
        "rating": 92,
        "base_fee": 220,
        "km_rate": 0.62,
        "kg_rate": 0.042,
        "fuel_rate": 0.13,
        "speed_factor": 1.03,
        "modes": ["Road"],
        "customs": True,
        "insurance": True,
        "door": True,
        "hazardous": True,
        "temperature": True,
        "color": "#00A651",
    },
    {
        "name": "CEVA Logistics",
        "service": "CEVA Ground & Rail",
        "logo": "CEVA",
        "logo_url": "https://www.google.com/s2/favicons?domain=cevalogistics.com&sz=128",
        "source_url": "https://www.cevalogistics.com/en/what-we-do/ground-and-rail",
        "rating": 93,
        "base_fee": 270,
        "km_rate": 0.70,
        "kg_rate": 0.050,
        "fuel_rate": 0.15,
        "speed_factor": 1.05,
        "modes": ["Road", "Rail", "Air", "Sea"],
        "customs": True,
        "insurance": True,
        "door": True,
        "hazardous": True,
        "temperature": True,
        "color": "#E4002B",
    },
    {
        "name": "XPO Logistics Europe",
        "service": "XPO European LTL / FTL",
        "logo": "XPO",
        "logo_url": "https://www.google.com/s2/favicons?domain=xpo.com&sz=128",
        "source_url": "https://europe.xpo.com/en/transport-solutions/",
        "rating": 92,
        "base_fee": 230,
        "km_rate": 0.64,
        "kg_rate": 0.044,
        "fuel_rate": 0.14,
        "speed_factor": 1.00,
        "modes": ["Road"],
        "customs": True,
        "insurance": True,
        "door": True,
        "hazardous": True,
        "temperature": True,
        "color": "#F15A22",
    },
    {
        "name": "GEODIS",
        "service": "GEODIS Road Transport",
        "logo": "GEO",
        "logo_url": "https://www.google.com/s2/favicons?domain=geodis.com&sz=128",
        "source_url": "https://geodis.com/transport-services/road-transportation",
        "rating": 93,
        "base_fee": 260,
        "km_rate": 0.70,
        "kg_rate": 0.049,
        "fuel_rate": 0.15,
        "speed_factor": 1.08,
        "modes": ["Road", "Rail", "Air", "Sea"],
        "customs": True,
        "insurance": True,
        "door": True,
        "hazardous": True,
        "temperature": True,
        "color": "#5B2C83",
    },
]


CARGO_RISK_FACTOR = {
    "General cargo": 1.00,
    "Electronics": 1.08,
    "Machinery": 1.12,
    "Furniture": 1.04,
    "Food & beverages": 1.10,
    "Construction materials": 1.07,
    "Chemicals": 1.20,
    "Textiles": 1.02,
}

MODE_COST_FACTOR = {"Road": 1.00, "Rail": 0.80, "Air": 4.30, "Sea": 0.64}
MODE_WEIGHT_FACTOR = {"Road": 1.00, "Rail": 0.72, "Air": 3.20, "Sea": 0.60}
MODE_SPEED_KM_DAY = {"Road": 620, "Rail": 760, "Air": 2600, "Sea": 430}
MODE_HANDLING_DAYS = {"Road": 1, "Rail": 2, "Air": 1, "Sea": 4}
MODE_CO2_G_TON_KM = {"Road": 62, "Rail": 22, "Air": 602, "Sea": 16}


# -----------------------------------------------------------------------------
# Calculation helpers
# -----------------------------------------------------------------------------

def haversine_km(point_a: tuple[float, float], point_b: tuple[float, float]) -> float:
    """Return the approximate great-circle distance between two coordinates."""
    lat1, lon1 = map(math.radians, point_a)
    lat2, lon2 = map(math.radians, point_b)
    d_lat = lat2 - lat1
    d_lon = lon2 - lon1
    value = (
        math.sin(d_lat / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin(d_lon / 2) ** 2
    )
    return 6371 * 2 * math.asin(math.sqrt(value))


def choose_mode(carrier: dict, requested_mode: str, distance: float, weight: float, days: int) -> str | None:
    """Choose a compatible transport mode for a demo carrier."""
    if requested_mode != "Let LogiHub choose":
        return requested_mode if requested_mode in carrier["modes"] else None

    if days <= 2 and "Air" in carrier["modes"]:
        return "Air"
    if (weight >= 8000 or distance >= 950) and "Rail" in carrier["modes"]:
        return "Rail"
    if distance >= 1500 and days >= 8 and "Sea" in carrier["modes"]:
        return "Sea"
    if "Road" in carrier["modes"]:
        return "Road"

    return min(carrier["modes"], key=lambda mode: MODE_HANDLING_DAYS[mode])


def calculate_offers(search: dict) -> list[dict]:
    origin_coordinates = CITIES[search["origin_country"]][search["origin_city"]]
    destination_coordinates = CITIES[search["destination_country"]][search["destination_city"]]

    # Road routes are longer than straight-line distance. 1.18 is a simple MVP approximation.
    distance = max(80, haversine_km(origin_coordinates, destination_coordinates) * 1.18)
    allowed_days = max(1, (search["delivery_date"] - search["ready_date"]).days + search["flex_days"])
    offers = []

    for carrier in CARRIERS:
        if search["hazardous"] and not carrier["hazardous"]:
            continue
        if search["temperature"] and not carrier["temperature"]:
            continue
        if search["customs"] and not carrier["customs"]:
            continue
        if search["insurance"] and not carrier["insurance"]:
            continue
        if search["door"] and not carrier["door"]:
            continue

        mode = choose_mode(
            carrier,
            search["mode"],
            distance,
            search["weight"],
            allowed_days,
        )
        if mode is None:
            continue

        transit_days = max(
            1,
            math.ceil(distance / (MODE_SPEED_KM_DAY[mode] * carrier["speed_factor"]))
            + MODE_HANDLING_DAYS[mode],
        )
        if transit_days > allowed_days:
            continue

        transport_cost = (
            carrier["base_fee"]
            + distance * carrier["km_rate"] * MODE_COST_FACTOR[mode]
            + search["weight"] * carrier["kg_rate"] * MODE_WEIGHT_FACTOR[mode]
        )
        transport_cost *= CARGO_RISK_FACTOR[search["cargo_type"]]

        if search["hazardous"]:
            transport_cost *= 1.18
        if search["temperature"]:
            transport_cost *= 1.14
        if allowed_days <= 3:
            transport_cost *= 1.10

        # Carrier-specific market calibration. This is an estimate, not the
        # carrier's official or live fuel surcharge.
        fuel_surcharge = transport_cost * carrier["fuel_rate"]
        customs_fee = 165 if search["customs"] else 0
        insurance_fee = max(45, search["declared_value"] * 0.003) if search["insurance"] else 0
        door_fee = 135 if search["door"] else 0
        total_price = transport_cost + fuel_surcharge + customs_fee + insurance_fee + door_fee

        co2_kg = distance * (search["weight"] / 1000) * MODE_CO2_G_TON_KM[mode] / 1000

        offers.append(
            {
                "carrier": carrier["name"],
                "service": carrier["service"],
                "logo": carrier["logo"],
                "logo_url": carrier["logo_url"],
                "source_url": carrier["source_url"],
                "rating": carrier["rating"],
                "color": carrier["color"],
                "mode": mode,
                "distance": round(distance),
                "days": transit_days,
                "arrival_date": search["ready_date"] + timedelta(days=transit_days),
                "transport_cost": transport_cost,
                "fuel_surcharge": fuel_surcharge,
                "customs_fee": customs_fee,
                "insurance_fee": insurance_fee,
                "door_fee": door_fee,
                "price": round(total_price),
                "co2_kg": round(co2_kg),
            }
        )

    if not offers:
        return []

    prices = [offer["price"] for offer in offers]
    transit_times = [offer["days"] for offer in offers]
    min_price, max_price = min(prices), max(prices)
    min_days, max_days = min(transit_times), max(transit_times)

    weights = {
        "Best balance": (0.45, 0.25, 0.30),
        "Lowest price": (0.75, 0.10, 0.15),
        "Fastest delivery": (0.15, 0.70, 0.15),
        "Highest reliability": (0.15, 0.10, 0.75),
    }[search["priority"]]

    for offer in offers:
        price_score = 1 if max_price == min_price else 1 - (offer["price"] - min_price) / (max_price - min_price)
        speed_score = 1 if max_days == min_days else 1 - (offer["days"] - min_days) / (max_days - min_days)
        reliability_score = offer["rating"] / 100
        offer["match_score"] = round(
            100
            * (
                weights[0] * price_score
                + weights[1] * speed_score
                + weights[2] * reliability_score
            )
        )

    offers.sort(key=lambda offer: (-offer["match_score"], offer["price"]))

    cheapest_carrier = min(offers, key=lambda offer: offer["price"])["carrier"]
    fastest_carrier = min(offers, key=lambda offer: offer["days"])["carrier"]
    reliable_carrier = max(offers, key=lambda offer: offer["rating"])["carrier"]

    for index, offer in enumerate(offers):
        badges = []
        if index == 0:
            badges.append("Recommended")
        if offer["carrier"] == cheapest_carrier:
            badges.append("Lowest price")
        if offer["carrier"] == fastest_carrier:
            badges.append("Fastest")
        if offer["carrier"] == reliable_carrier:
            badges.append("Most reliable")
        offer["badges"] = badges

    return offers


def format_euro(value: float) -> str:
    return f"€{value:,.0f}".replace(",", " ")


def shipment_documents(search: dict) -> list[str]:
    """Return a concise, non-binding document checklist for the demo brief."""
    documents = ["Commercial invoice", "Packing list", "CMR consignment note"]
    if search["customs"]:
        documents.extend(["Customs declaration", "EORI number", "Commodity / HS code"])
    if search["hazardous"]:
        documents.extend(["Safety Data Sheet (SDS)", "ADR dangerous-goods declaration"])
    if search["temperature"]:
        documents.append("Temperature-handling instructions")
    return documents


def shipment_risks(search: dict, offer: dict) -> list[str]:
    """Generate explainable MVP risk notes without calling an external AI API."""
    risks = []
    if search["customs"]:
        risks.append("Final duties and import VAT depend on the confirmed HS code and customs value.")
    if search["hazardous"]:
        risks.append("Carrier acceptance and ADR packaging must be confirmed before collection.")
    if search["temperature"]:
        risks.append("Temperature range and monitoring requirements must be confirmed in writing.")
    if offer["days"] <= 2:
        risks.append("The short delivery window leaves limited recovery time for collection delays.")
    if not risks:
        risks.append("No special handling risk detected; final dimensions and loading access still require confirmation.")
    return risks


def proposal_text(search: dict, offer: dict) -> str:
    """Create an email-ready proposal that can be downloaded without extra packages."""
    documents = "\n".join(f"- {item}" for item in shipment_documents(search))
    return f"""LOGIHUB AI — ESTIMATED FREIGHT PROPOSAL

Route: {search['origin_city']}, {search['origin_country']} → {search['destination_city']}, {search['destination_country']}
Carrier profile: {offer['carrier']}
Service: {offer['service']}
Transport mode: {offer['mode']}
Cargo: {search['cargo_description']} ({search['weight']:,.0f} kg, {search['packages']} packages)
Estimated transit: {offer['days']} days
Estimated arrival: {offer['arrival_date'].strftime('%d %b %Y')}
Estimated total: {format_euro(offer['price'])}

DOCUMENT CHECKLIST
{documents}

IMPORTANT
This is an independent LogiHub market estimate, not a binding carrier quotation.
Availability, classification, duties, taxes and the final rate require confirmation.
No payment is collected before carrier confirmation.
"""


# -----------------------------------------------------------------------------
# Interface
# -----------------------------------------------------------------------------

st.markdown(
    """
    <style>
        :root {
            --ink:#0B1734;
            --muted:#64748B;
            --line:#DCE5F0;
            --blue:#2563EB;
            --cyan:#06B6D4;
            --soft-blue:#EFF6FF;
            --green:#0F9F78;
        }
        html { scroll-behavior:smooth; }
        .stApp {
            color:var(--ink);
            background:
                radial-gradient(circle at 8% 4%, rgba(37,99,235,.10), transparent 24rem),
                radial-gradient(circle at 96% 8%, rgba(6,182,212,.09), transparent 22rem),
                #F6F8FC;
        }
        [data-testid="stHeader"] {
            background:rgba(246,248,252,.82);
            backdrop-filter:blur(14px);
            border-bottom:1px solid rgba(220,229,240,.75);
        }
        .block-container { max-width:1180px; padding-top:4.7rem; padding-bottom:5rem; }
        .hero-shell {
            position:relative; overflow:hidden; color:white;
            background:linear-gradient(120deg,#071633 0%,#102A5A 60%,#0B4C68 100%);
            border:1px solid rgba(255,255,255,.10); border-radius:28px;
            padding:1.35rem 1.5rem 1.45rem; margin-bottom:1rem;
            box-shadow:0 24px 60px rgba(7,22,51,.18);
        }
        .hero-shell:after {
            content:""; position:absolute; width:250px; height:250px; border-radius:50%;
            right:-90px; top:-145px; background:rgba(34,211,238,.17); filter:blur(2px);
        }
        .brand-row { display:flex; align-items:center; justify-content:space-between; gap:1rem; }
        .brand { display:flex; align-items:center; gap:.7rem; position:relative; z-index:1; }
        .brand-mark {
            width:44px; height:44px; border-radius:14px; display:grid; place-items:center;
            color:white; font-weight:900; font-size:.92rem; letter-spacing:-.03em;
            background:linear-gradient(135deg,#3B82F6,#22D3EE);
            box-shadow:0 10px 26px rgba(34,211,238,.25);
        }
        .brand-name { font-size:1.2rem; font-weight:850; color:white; letter-spacing:-.02em; }
        .brand-caption { color:#AFC4E8; font-size:.75rem; margin-top:-.08rem; }
        .network-pill {
            position:relative; z-index:1; display:inline-flex; align-items:center; gap:.45rem;
            color:#CFFAFE; background:rgba(6,182,212,.12); border:1px solid rgba(103,232,249,.25);
            border-radius:999px; padding:.45rem .75rem; font-size:.75rem; font-weight:750;
        }
        .network-dot { width:7px; height:7px; border-radius:50%; background:#2DD4BF; box-shadow:0 0 0 5px rgba(45,212,191,.12); }
        .hero-copy { position:relative; z-index:1; margin-top:1.2rem; max-width:760px; }
        .hero-title { margin:0; font-size:clamp(1.75rem,4vw,2.7rem); line-height:1.03; letter-spacing:-.045em; font-weight:850; }
        .hero-subtitle { color:#C6D5EE; margin:.65rem 0 0; font-size:.96rem; line-height:1.55; max-width:650px; }
        .hero-facts { display:flex; flex-wrap:wrap; gap:.55rem; margin-top:1.05rem; }
        .hero-fact {
            color:#DDEBFF; background:rgba(255,255,255,.075); border:1px solid rgba(255,255,255,.10);
            border-radius:10px; padding:.38rem .58rem; font-size:.72rem; font-weight:700;
        }
        .journey-strip {
            display:grid; grid-template-columns:repeat(4,1fr); gap:.6rem; margin:1rem 0;
            padding:.7rem; background:rgba(255,255,255,.80); border:1px solid var(--line);
            border-radius:18px; box-shadow:0 8px 24px rgba(15,23,42,.04);
        }
        .journey-item { display:flex; align-items:center; gap:.55rem; padding:.45rem .5rem; color:#52627A; font-size:.78rem; font-weight:750; }
        .journey-number {
            width:26px; height:26px; display:grid; place-items:center; border-radius:9px;
            color:#1D4ED8; background:#DBEAFE; font-size:.72rem; font-weight:900;
        }
        .step-label {
            display:inline-flex; align-items:center; color:#1D4ED8; background:#EFF6FF;
            border:1px solid #DBEAFE; border-radius:999px; padding:.28rem .58rem;
            font-size:.7rem; font-weight:850; letter-spacing:.07em;
            text-transform:uppercase; margin-bottom:.1rem;
        }
        .demo-note {
            display:flex; align-items:center; gap:.5rem; color:#51627A;
            background:rgba(255,255,255,.78); border:1px solid var(--line);
            padding:.65rem .85rem; border-radius:13px; margin:0 0 1rem;
            font-size:.78rem;
        }
        .demo-icon {
            display:inline-grid; place-items:center; width:23px; height:23px;
            border-radius:8px; color:#1D4ED8; background:#DBEAFE; font-weight:900;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
            background:rgba(255,255,255,.94); border-color:var(--line) !important;
            border-radius:22px !important; box-shadow:0 12px 34px rgba(30,55,90,.055);
            transition:transform .2s ease, box-shadow .2s ease, border-color .2s ease;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:hover {
            border-color:#C7D7EC !important; box-shadow:0 16px 38px rgba(30,55,90,.075);
        }
        [data-testid="stVerticalBlockBorderWrapper"] h3 {
            color:var(--ink); font-size:1.35rem; letter-spacing:-.025em; margin-top:.25rem;
        }
        label, [data-testid="stWidgetLabel"] p { color:#34445B !important; font-weight:700 !important; }
        div[data-baseweb="select"] > div, .stNumberInput input, .stTextInput input, .stDateInput input {
            min-height:2.75rem; border-radius:12px !important; border-color:#D7E1EC !important;
            background:#FBFCFE !important;
        }
        div[data-baseweb="select"] > div:focus-within, .stNumberInput input:focus, .stTextInput input:focus, .stDateInput input:focus {
            border-color:#60A5FA !important; box-shadow:0 0 0 3px rgba(96,165,250,.15) !important;
        }
        [data-testid="stCheckbox"] { padding:.25rem 0; }
        [data-testid="stMetric"] {
            background:#F7FAFD; border:1px solid #E4EAF2; border-radius:13px;
            padding:.65rem .75rem;
        }
        [data-testid="stMetricLabel"] { color:#64748B; }
        [data-testid="stMetricValue"] { color:var(--ink); letter-spacing:-.03em; }
        [data-testid="stAlert"] { border-radius:16px; border:1px solid #BFDBFE; }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.carrier-heading) {
            border-color:#CFDCEF !important;
            box-shadow:0 12px 32px rgba(37,99,235,.07);
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.carrier-heading):hover {
            transform:translateY(-2px); border-color:#93B4E8 !important;
            box-shadow:0 18px 42px rgba(37,99,235,.11);
        }
        .offer-name { font-size:1.08rem; font-weight:850; color:var(--ink); margin-bottom:.1rem; letter-spacing:-.015em; }
        .offer-meta { color:#64748B; font-size:.9rem; }
        .carrier-heading { display:flex; align-items:center; gap:.75rem; margin:.5rem 0 .35rem; }
        .carrier-logo {
            position:relative; overflow:hidden; width:46px; height:46px; border-radius:14px; display:grid; place-items:center;
            color:white; font-size:.88rem; font-weight:900; letter-spacing:.04em;
            box-shadow:inset 0 1px 0 rgba(255,255,255,.35),0 8px 18px rgba(15,23,42,.18); flex:0 0 auto;
        }
        .carrier-logo img {
            position:absolute; inset:0; width:100%; height:100%; object-fit:contain;
            padding:8px; box-sizing:border-box; background:white;
        }
        .included-service {
            display:inline-block; margin-top:.5rem; color:#08755B; background:#DDFBF2;
            border:1px solid #B7F0DF; border-radius:999px; padding:.3rem .55rem;
            font-size:.72rem; font-weight:800;
        }
        .badge {
            display:inline-block; color:#1D4ED8; background:#EAF2FF; border:1px solid #D4E4FF;
            border-radius:999px; padding:.24rem .55rem; font-size:.68rem; font-weight:850; margin-right:.3rem;
        }
        .price { font-size:1.65rem; font-weight:900; color:var(--ink); text-align:right; letter-spacing:-.04em; }
        .price-note { color:#64748B; font-size:.75rem; text-align:right; }
        .stButton > button[kind="primary"] {
            color:white; background:linear-gradient(90deg,#2563EB,#0891B2); border:none;
            min-height:3.25rem; font-weight:850; border-radius:14px;
            box-shadow:0 12px 25px rgba(37,99,235,.20); transition:all .2s ease;
        }
        .stButton > button[kind="primary"]:hover {
            transform:translateY(-1px); box-shadow:0 16px 30px rgba(37,99,235,.27);
        }
        .stButton > button:not([kind="primary"]) {
            color:#1D4ED8; background:#F8FAFF; border:1px solid #D5E2F4;
            border-radius:12px; font-weight:750;
        }
        [data-testid="stExpander"] { border-color:#E0E7F0; border-radius:13px; background:#FBFCFE; }
        hr { border-color:#DCE5F0 !important; margin:2.2rem 0 !important; }
        .results-kicker { color:#2563EB; font-size:.72rem; font-weight:900; letter-spacing:.09em; text-transform:uppercase; }
        .results-note { color:#64748B; font-size:.82rem; line-height:1.5; }

        /* 2026 visual refresh: editorial typography + freight control-room cues */
        :root { --acid:#C8FF62; --mint:#DFF8F1; --paper:#F5F7F2; --black:#101514; }
        .stApp {
            background:
                radial-gradient(circle at 5% 5%, rgba(111,231,200,.24), transparent 25rem),
                radial-gradient(circle at 96% 28%, rgba(200,255,98,.16), transparent 23rem),
                var(--paper);
        }
        [data-testid="stHeader"], [data-testid="stAppHeader"], [data-testid="stToolbar"], [data-testid="stDecoration"] {
            display:none !important;
        }
        #MainMenu, footer { visibility:hidden; }
        .block-container { max-width:1220px; padding-top:1.25rem; }
        .hero-shell {
            color:var(--black); background:linear-gradient(135deg,#E8FAF6 0%,#F8FAF2 57%,#EDFFC9 100%);
            border:1px solid rgba(16,21,20,.12); border-radius:34px; padding:1rem 1rem 1.15rem;
            box-shadow:0 28px 75px rgba(23,53,47,.10); min-height:405px;
        }
        .hero-shell:after {
            width:360px; height:360px; right:-110px; top:90px;
            background:rgba(91,211,181,.18); filter:blur(1px);
        }
        .brand-row {
            background:rgba(255,255,255,.88); border:1px solid rgba(16,21,20,.10);
            border-radius:999px; padding:.55rem .65rem .55rem .7rem;
            box-shadow:0 10px 30px rgba(23,53,47,.07);
        }
        .brand-mark { color:var(--black); background:var(--acid); box-shadow:none; border-radius:50%; }
        .brand-name { color:var(--black); }
        .brand-caption { color:#60706C; }
        .network-pill { color:white; background:var(--black); border-color:var(--black); padding:.58rem .8rem; }
        .network-dot { background:var(--acid); box-shadow:0 0 0 5px rgba(200,255,98,.16); }
        .hero-grid { display:grid; grid-template-columns:minmax(0,1.55fr) minmax(245px,.65fr); gap:1rem; align-items:end; padding:.8rem .55rem 0; }
        .hero-copy { margin:1.2rem 0 .15rem; max-width:790px; }
        .eyebrow { font-size:.71rem; font-weight:900; letter-spacing:.13em; text-transform:uppercase; color:#177760; margin-bottom:.85rem; }
        .hero-title { color:var(--black); font-size:clamp(2.8rem,6vw,5.35rem); line-height:.88; letter-spacing:-.072em; font-weight:900; }
        .hero-subtitle { color:#43514E; font-size:1.02rem; max-width:620px; }
        .hero-fact { color:#25322F; background:rgba(255,255,255,.72); border-color:rgba(16,21,20,.10); border-radius:999px; }
        .hero-card {
            position:relative; z-index:1; color:white; background:var(--black); border-radius:24px;
            padding:1.15rem; box-shadow:0 18px 35px rgba(16,21,20,.16);
        }
        .hero-card-label { color:#9DB0AA; font-size:.68rem; font-weight:850; letter-spacing:.11em; text-transform:uppercase; }
        .hero-card-number { font-size:2.75rem; line-height:1; font-weight:900; letter-spacing:-.06em; margin:.65rem 0 .25rem; }
        .hero-card-copy { color:#C7D2CE; font-size:.78rem; line-height:1.45; }
        .hero-card-line { display:flex; align-items:center; gap:.5rem; margin-top:1rem; color:var(--acid); font-size:.75rem; font-weight:800; }
        .hero-card-line:before { content:""; height:1px; flex:1; background:#53625E; }
        .journey-strip { background:var(--black); border:0; box-shadow:0 16px 35px rgba(16,21,20,.10); }
        .journey-item { color:#B9C7C2; }
        .journey-number { color:var(--black); background:var(--acid); border-radius:50%; }
        .demo-note { background:transparent; border:0; padding:.2rem .35rem .8rem; }
        .demo-icon { color:var(--black); background:#DDE7E2; border-radius:50%; }
        [data-testid="stVerticalBlockBorderWrapper"] {
            border-color:rgba(16,21,20,.11) !important; border-radius:28px !important;
            box-shadow:0 15px 42px rgba(34,65,58,.065); padding:.35rem;
        }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.route-section) { background:linear-gradient(140deg,#FFFFFF,#F1FFFB); }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.schedule-section) { background:linear-gradient(140deg,#FFFFFF,#F6F8FF); }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.cargo-section) { background:linear-gradient(140deg,#FFFFFF,#FFFBEA); }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.preferences-section) { background:linear-gradient(140deg,#FFFFFF,#F4FFE1); }
        .section-anchor { display:none; }
        .step-label { color:#154F41; background:#E4F8F2; border-color:#C7EDE3; }
        .route-preview {
            display:grid; grid-template-columns:auto 1fr auto; align-items:center; gap:1rem;
            padding:.85rem 1rem; margin:.4rem 0 .2rem; background:var(--black); color:white; border-radius:18px;
        }
        .route-place strong { display:block; font-size:1rem; }
        .route-place span { color:#9FB0AA; font-size:.72rem; }
        .route-track { height:1px; background:#63736E; position:relative; }
        .route-track:before,.route-track:after { content:""; position:absolute; top:-5px; width:11px; height:11px; border-radius:50%; background:var(--acid); }
        .route-track:before { left:0; } .route-track:after { right:0; }
        .ai-brief {
            background:var(--black); color:white; border-radius:28px; padding:1.2rem 1.3rem; margin:.7rem 0 1rem;
            box-shadow:0 20px 45px rgba(16,21,20,.13);
        }
        .ai-brief-kicker { color:var(--acid); font-size:.7rem; font-weight:900; letter-spacing:.12em; text-transform:uppercase; }
        .ai-brief h3 { color:white !important; margin:.35rem 0 .25rem !important; font-size:1.45rem !important; }
        .ai-brief p { color:#C7D2CE; margin:.2rem 0 .85rem; }
        .ai-grid { display:grid; grid-template-columns:repeat(3,1fr); gap:.65rem; }
        .ai-cell { background:#1A211F; border:1px solid #303B37; border-radius:17px; padding:.8rem; }
        .ai-cell strong { display:block; color:white; font-size:.78rem; margin-bottom:.35rem; }
        .ai-cell span { color:#B8C5C0; font-size:.72rem; line-height:1.45; }
        [data-testid="stVerticalBlockBorderWrapper"]:has(.top-offer) { border:2px solid #8FCB38 !important; box-shadow:0 20px 48px rgba(105,157,35,.14); }
        .top-offer { display:none; }
        .badge { color:#17380F; background:#E8FFC1; border-color:#C8F47E; }
        .price { color:var(--black); }
        .stButton > button[kind="primary"] { color:var(--black); background:var(--acid); box-shadow:0 12px 25px rgba(139,190,61,.22); }
        .stButton > button[kind="primary"]:hover { color:var(--black); background:#B9F34E; box-shadow:0 16px 30px rgba(139,190,61,.28); }
        .stButton > button:not([kind="primary"]) { color:white; background:var(--black); border-color:var(--black); }
        /* Hosted Streamlit must match the original local light UI exactly.
           Pin the geometry and colours instead of inheriting browser/cloud
           theme values (which caused black steppers and uneven rows). */
        html, body, .stApp { color-scheme:light !important; }

        [data-testid="stSelectbox"] [data-baseweb="select"] > div,
        [data-testid="stDateInput"] [data-baseweb="input"],
        [data-testid="stNumberInputContainer"],
        [data-testid="stTextInputRootElement"] {
            height:44px !important;
            min-height:44px !important;
            box-sizing:border-box !important;
            box-shadow:none !important;
        }
        [data-testid="stSelectbox"] [data-baseweb="select"] > div {
            color:var(--black) !important;
            background:#FBFCFE !important;
            border:1px solid #D7E1EC !important;
            border-radius:12px !important;
        }
        [data-testid="stDateInput"] [data-baseweb="input"],
        [data-testid="stNumberInputContainer"],
        [data-testid="stTextInputRootElement"] {
            color:var(--black) !important;
            background:#F0F2F6 !important;
            border:1px solid #F0F2F6 !important;
            border-radius:8px !important;
            overflow:hidden !important;
        }
        [data-testid="stDateInput"] [data-baseweb="base-input"],
        [data-testid="stNumberInput"] [data-baseweb="input"],
        [data-testid="stNumberInput"] [data-baseweb="base-input"],
        [data-testid="stTextInput"] [data-baseweb="base-input"] {
            height:42px !important;
            min-height:42px !important;
            color:var(--black) !important;
            background:transparent !important;
            border:0 !important;
            box-shadow:none !important;
        }
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stDateInput"] input {
            height:42px !important;
            min-height:42px !important;
            color:var(--black) !important;
            background:transparent !important;
            border:0 !important;
            border-radius:0 !important;
            box-shadow:none !important;
            -webkit-text-fill-color:var(--black) !important;
            opacity:1 !important;
        }
        [data-testid="stSelectbox"] [data-baseweb="select"] div[value] {
            color:var(--black) !important;
            -webkit-text-fill-color:var(--black) !important;
            opacity:1 !important;
        }
        [data-testid="stNumberInput"] button {
            width:32px !important;
            height:42px !important;
            min-height:42px !important;
            padding:0 !important;
            color:#31333F !important;
            background:#F0F2F6 !important;
            border:0 !important;
            border-radius:0 !important;
            box-shadow:none !important;
        }
        [data-testid="stNumberInput"] button:hover {
            color:#101514 !important;
            background:#E8EBF0 !important;
        }
        [data-testid="stNumberInput"] button svg {
            color:#31333F !important;
            fill:#31333F !important;
        }
        [data-testid="stTextInput"] input::placeholder,
        [data-testid="stDateInput"] input::placeholder {
            color:#7A8984 !important;
            -webkit-text-fill-color:#7A8984 !important;
            opacity:1 !important;
        }
        [data-testid="stRadio"] label p,
        [data-testid="stCheckbox"] label p {
            color:#34445B !important;
            -webkit-text-fill-color:#34445B !important;
            opacity:1 !important;
        }
        [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:not(:checked)) > div:first-child {
            background:#FFFFFF !important;
            border:1px solid rgba(49,51,63,.35) !important;
        }
        [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:not(:checked)) > div:first-child > div {
            background:#FFFFFF !important;
        }
        [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child {
            background:#FF4B4B !important;
            border:0 !important;
        }
        [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) > div:first-child > div {
            background:#FFFFFF !important;
        }
        [data-testid="stCheckbox"] label[data-baseweb="checkbox"]:has(input:not(:checked)) > span:first-child {
            background:#FFFFFF !important;
            border:1px solid rgba(49,51,63,.35) !important;
            box-shadow:none !important;
        }
        [data-testid="stDownloadButton"] button {
            height:44px !important;
            min-height:44px !important;
            color:var(--black) !important;
            background:#FFFFFF !important;
            border:1px solid rgba(49,51,63,.20) !important;
            border-radius:8px !important;
            box-shadow:none !important;
        }
        [data-testid="stDownloadButton"] button p,
        [data-testid="stDownloadButton"] button span {
            color:var(--black) !important;
            -webkit-text-fill-color:var(--black) !important;
        }
        [data-testid="stFormSubmitButton"] button {
            height:44px !important;
            min-height:44px !important;
            color:#FFFFFF !important;
            background:#FF4B4B !important;
            border:1px solid #FF4B4B !important;
            border-radius:8px !important;
            box-shadow:none !important;
        }
        [data-testid="stFormSubmitButton"] button p,
        [data-testid="stFormSubmitButton"] button span {
            color:#FFFFFF !important;
            -webkit-text-fill-color:#FFFFFF !important;
        }
        [data-testid="stAlert"] [data-testid="stAlertContainer"] {
            color:#064A78 !important;
            background:#E6F4FF !important;
            border:1px solid #B8DDF5 !important;
            opacity:1 !important;
        }
        [data-testid="stAlert"] [data-testid="stAlertContainer"] * {
            color:#064A78 !important;
            -webkit-text-fill-color:#064A78 !important;
            opacity:1 !important;
        }
        .booking-head { margin:.2rem 0 1rem; }
        .booking-kicker { color:#177760; font-size:.7rem; font-weight:900; letter-spacing:.12em; text-transform:uppercase; }
        .booking-title { font-size:2rem; line-height:1.05; letter-spacing:-.04em; font-weight:900; margin:.35rem 0; color:var(--black); }
        .booking-summary { background:#E8FAF4; border:1px solid #C5EADF; border-radius:18px; padding:.9rem 1rem; margin-bottom:.6rem; }
        .booking-summary strong { color:var(--black); }
        .booking-summary span { color:#51625D; font-size:.82rem; }
        .payment-note { color:#42534E; background:#F0F4F1; border-radius:14px; padding:.7rem .8rem; font-size:.78rem; }
        @media (max-width: 820px) {
            .journey-strip { grid-template-columns:repeat(2,1fr); }
            .hero-shell { border-radius:22px; padding:1.15rem; }
            .network-pill { display:none; }
            .hero-grid { grid-template-columns:1fr; }
            .hero-card { display:none; }
            .hero-title { font-size:3.35rem; }
            .ai-grid { grid-template-columns:1fr; }
        }
        @media (max-width: 700px) {
            .block-container { padding-left:1rem; padding-right:1rem; }
            .price, .price-note { text-align:left; }
            .journey-strip { grid-template-columns:1fr 1fr; gap:.25rem; }
            .journey-item { font-size:.7rem; }
            .hero-title { font-size:1.8rem; }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="hero-shell">
        <div class="brand-row">
            <div class="brand">
                <div class="brand-mark">LH</div>
                <div>
                    <div class="brand-name">LogiHub AI</div>
                    <div class="brand-caption">Freight intelligence platform</div>
                </div>
            </div>
            <div class="network-pill"><span class="network-dot"></span> European carrier profiles online</div>
        </div>
        <div class="hero-grid">
            <div class="hero-copy">
                <div class="eyebrow">One search · multiple freight networks</div>
                <h1 class="hero-title">Move cargo.<br>Skip the chase.</h1>
                <p class="hero-subtitle">Compare European freight options, customs support and delivery terms in one intelligent workspace.</p>
                <div class="hero-facts">
                    <span class="hero-fact">10 European carrier profiles</span>
                    <span class="hero-fact">4 transport modes</span>
                    <span class="hero-fact">AI-assisted comparison</span>
                </div>
            </div>
            <div class="hero-card">
                <div class="hero-card-label">Network snapshot</div>
                <div class="hero-card-number">10×</div>
                <div class="hero-card-copy">One shipment brief is matched against ten researched European carrier profiles.</div>
                <div class="hero-card-line">Ready to compare</div>
            </div>
        </div>
    </div>
    <div class="journey-strip">
        <div class="journey-item"><span class="journey-number">1</span> Route</div>
        <div class="journey-item"><span class="journey-number">2</span> Schedule</div>
        <div class="journey-item"><span class="journey-number">3</span> Cargo</div>
        <div class="journey-item"><span class="journey-number">4</span> Preferences</div>
    </div>
    <div class="demo-note"><span class="demo-icon">i</span><span><strong>Independent MVP.</strong> Real carrier names and trademarks are shown for comparison. Rates, availability and reliability are LogiHub market estimates—not live carrier quotes. No affiliation or endorsement is implied.</span></div>
    """,
    unsafe_allow_html=True,
)


with st.container(border=True):
    st.markdown('<span class="section-anchor route-section"></span>', unsafe_allow_html=True)
    st.markdown('<div class="step-label">Step 1 · Route</div>', unsafe_allow_html=True)
    st.subheader("Where should we move your cargo?")

    route_col_1, route_col_2 = st.columns(2)
    with route_col_1:
        origin_country = st.selectbox("Origin country", list(CITIES), index=0)
        origin_city = st.selectbox("Origin city", list(CITIES[origin_country]), index=0)
    with route_col_2:
        destination_country = st.selectbox("Destination country", list(CITIES), index=1)
        destination_city = st.selectbox("Destination city", list(CITIES[destination_country]), index=1)

    st.markdown(
        f"""
        <div class="route-preview">
            <div class="route-place"><strong>{origin_city}</strong><span>{origin_country}</span></div>
            <div class="route-track"></div>
            <div class="route-place" style="text-align:right"><strong>{destination_city}</strong><span>{destination_country}</span></div>
        </div>
        """,
        unsafe_allow_html=True,
    )


with st.container(border=True):
    st.markdown('<span class="section-anchor schedule-section"></span>', unsafe_allow_html=True)
    st.markdown('<div class="step-label">Step 2 · Schedule</div>', unsafe_allow_html=True)
    st.subheader("When does it need to arrive?")

    schedule_col_1, schedule_col_2, schedule_col_3 = st.columns(3)
    with schedule_col_1:
        ready_date = st.date_input("Cargo ready date", value=date.today() + timedelta(days=1), min_value=date.today())
    with schedule_col_2:
        delivery_date = st.date_input("Requested delivery", value=date.today() + timedelta(days=6), min_value=date.today() + timedelta(days=1))
    with schedule_col_3:
        flex_days = st.select_slider("Schedule flexibility", options=list(range(0, 8)), value=2, format_func=lambda value: f"+{value} days")


with st.container(border=True):
    st.markdown('<span class="section-anchor cargo-section"></span>', unsafe_allow_html=True)
    st.markdown('<div class="step-label">Step 3 · Cargo</div>', unsafe_allow_html=True)
    st.subheader("Tell us about the shipment")

    cargo_col_1, cargo_col_2, cargo_col_3 = st.columns(3)
    with cargo_col_1:
        cargo_type = st.selectbox("Cargo category", list(CARGO_RISK_FACTOR), index=1)
        weight = st.number_input("Total weight (kg)", min_value=1.0, max_value=100000.0, value=1200.0, step=100.0)
    with cargo_col_2:
        declared_value = st.number_input("Declared value (€)", min_value=100.0, max_value=10000000.0, value=40000.0, step=1000.0)
        packages = st.number_input("Number of packages", min_value=1, max_value=10000, value=8, step=1)
    with cargo_col_3:
        mode = st.selectbox("Transport mode", ["Let LogiHub choose", "Road", "Rail", "Air", "Sea"])
        cargo_description = st.text_input("Short description", value="LED lighting equipment")

    cargo_flag_1, cargo_flag_2 = st.columns(2)
    with cargo_flag_1:
        hazardous = st.checkbox("Hazardous goods")
    with cargo_flag_2:
        temperature = st.checkbox("Temperature-controlled transport")


with st.container(border=True):
    st.markdown('<span class="section-anchor preferences-section"></span>', unsafe_allow_html=True)
    st.markdown('<div class="step-label">Step 4 · Preferences</div>', unsafe_allow_html=True)
    st.subheader("What should the offer include?")

    service_col_1, service_col_2, service_col_3 = st.columns(3)
    with service_col_1:
        customs = st.checkbox(
            "LogiHub Customs Concierge",
            value=True,
            help="LogiHub coordinates customs-charge payments and prepares the paperwork required at the border.",
        )
    with service_col_2:
        insurance = st.checkbox("Cargo insurance", value=True)
    with service_col_3:
        door = st.checkbox("Door-to-door delivery", value=True)

    if customs:
        st.caption(
            "✓ We coordinate customs-charge payments and prepare border documentation. "
            "Government duties and taxes are billed separately at their actual assessed amount."
        )

    priority = st.radio(
        "Main priority",
        ["Best balance", "Lowest price", "Fastest delivery", "Highest reliability"],
        horizontal=True,
    )


search_clicked = st.button("Compare freight offers", type="primary", use_container_width=True)

if search_clicked:
    if origin_country == destination_country and origin_city == destination_city:
        st.error("Origin and destination cannot be the same.")
    elif delivery_date <= ready_date:
        st.error("Requested delivery must be later than the cargo ready date.")
    elif not cargo_description.strip():
        st.error("Please add a short cargo description.")
    else:
        search = {
            "origin_country": origin_country,
            "origin_city": origin_city,
            "destination_country": destination_country,
            "destination_city": destination_city,
            "ready_date": ready_date,
            "delivery_date": delivery_date,
            "flex_days": flex_days,
            "cargo_type": cargo_type,
            "cargo_description": cargo_description.strip(),
            "weight": weight,
            "declared_value": declared_value,
            "packages": packages,
            "mode": mode,
            "hazardous": hazardous,
            "temperature": temperature,
            "customs": customs,
            "insurance": insurance,
            "door": door,
            "priority": priority,
        }
        st.session_state["offers"] = calculate_offers(search)
        st.session_state["search"] = search
        st.session_state.pop("selected_offer", None)


if "offers" in st.session_state:
    offers = st.session_state["offers"]
    search = st.session_state["search"]

    st.divider()
    st.markdown('<div class="results-kicker">Matching results</div>', unsafe_allow_html=True)
    st.header(f"{search['origin_city']} → {search['destination_city']}")
    st.caption(
        f"{search['cargo_description']} · {search['weight']:,.0f} kg · "
        f"{len(offers)} compatible estimated offers"
    )
    st.markdown(
        '<p class="results-note">Estimated CO₂ shows the approximate emissions allocated to this shipment based on weight, distance and transport mode. Lower is greener.</p>',
        unsafe_allow_html=True,
    )

    if not offers:
        st.warning(
            "No carrier profile matches all selected requirements and dates. "
            "Try adding schedule flexibility, changing the transport mode, or removing one optional service."
        )
    else:
        best = offers[0]
        price_difference = best["price"] - min(offer["price"] for offer in offers)
        explanation = (
            f"{best['carrier']} is the strongest match for your **{search['priority'].lower()}** priority. "
            f"It delivers in **{best['days']} days**, has a **{best['rating']}% estimated reliability score**, "
            f"and costs **{format_euro(best['price'])}**."
        )
        if price_difference > 0:
            explanation += f" That is {format_euro(price_difference)} above the cheapest compatible option."

        st.info(f"**Smart recommendation:** {explanation}")

        documents = shipment_documents(search)
        risk_notes = shipment_risks(search, best)
        document_preview = "<br>".join(f"• {item}" for item in documents[:4])
        risk_preview = "<br>".join(f"• {item}" for item in risk_notes[:3])
        customs_summary = (
            "LogiHub coordinates border paperwork and customs-charge payment. Duties and taxes remain payable at the assessed amount."
            if search["customs"]
            else "Customs Concierge is not included in this search. Add it if the route requires border formalities."
        )
        st.markdown(
            f"""
            <div class="ai-brief">
                <div class="ai-brief-kicker">✦ AI Shipment Brief</div>
                <h3>What needs attention before booking</h3>
                <p>LogiHub translated the shipment data into an operational checklist for the selected recommendation.</p>
                <div class="ai-grid">
                    <div class="ai-cell"><strong>Why this match</strong><span>{best['carrier']} ranks highest for {search['priority'].lower()}, with {best['days']}-day estimated transit and a {best['match_score']}% match score.</span></div>
                    <div class="ai-cell"><strong>Document checklist</strong><span>{document_preview}</span></div>
                    <div class="ai-cell"><strong>Customs & risk flags</strong><span>{customs_summary}<br><br>{risk_preview}</span></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for rank, offer in enumerate(offers[:6], start=1):
            with st.container(border=True):
                if rank == 1:
                    st.markdown('<span class="top-offer"></span>', unsafe_allow_html=True)
                info_col, metrics_col, price_col = st.columns([2.2, 2.2, 1.1])

                with info_col:
                    badges_html = "".join(f'<span class="badge">{badge}</span>' for badge in offer["badges"])
                    st.markdown(badges_html, unsafe_allow_html=True)
                    st.markdown(
                        f"""
                        <div class="carrier-heading">
                            <div class="carrier-logo" style="background:{offer['color']};">
                                {offer['logo']}
                                <img src="{offer['logo_url']}" alt="{offer['carrier']} brand mark" onerror="this.style.display='none'">
                            </div>
                            <div>
                                <div class="offer-name">{rank}. {offer['carrier']}</div>
                                <div class="offer-meta">{offer['service']} · {offer['mode']} · {offer['distance']:,} km · Match {offer['match_score']}%</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if search["customs"]:
                        st.markdown(
                            '<span class="included-service">✓ Customs charges coordination & border paperwork</span>',
                            unsafe_allow_html=True,
                        )

                with metrics_col:
                    metric_col_1, metric_col_2, metric_col_3 = st.columns(3)
                    metric_col_1.metric("Transit", f"{offer['days']} days")
                    metric_col_2.metric(
                        "Est. reliability",
                        f"{offer['rating']}%",
                        help="LogiHub model score for this demo—not a carrier-published KPI.",
                    )
                    metric_col_3.metric(
                        "Estimated CO₂",
                        f"{offer['co2_kg']} kg",
                        help="Approximate emissions for this shipment based on cargo weight, route distance and transport mode.",
                    )

                with price_col:
                    st.markdown(f'<div class="price">{format_euro(offer["price"])}</div>', unsafe_allow_html=True)
                    st.markdown('<div class="price-note">independent market estimate</div>', unsafe_allow_html=True)

                with st.expander("View price breakdown"):
                    st.write(f"Estimated arrival: **{offer['arrival_date'].strftime('%d %b %Y')}**")
                    st.write(f"Base transport: **{format_euro(offer['transport_cost'])}**")
                    st.write(f"Fuel surcharge: **{format_euro(offer['fuel_surcharge'])}**")
                    if offer["customs_fee"]:
                        st.write(f"LogiHub customs & documentation service: **{format_euro(offer['customs_fee'])}**")
                    if offer["insurance_fee"]:
                        st.write(f"Cargo insurance: **{format_euro(offer['insurance_fee'])}**")
                    if offer["door_fee"]:
                        st.write(f"Door-to-door service: **{format_euro(offer['door_fee'])}**")
                    st.markdown(f"[View the carrier's official service page]({offer['source_url']})")
                    st.caption("Independent LogiHub estimate based on route, weight, mode and Q2 2026 European road-freight market conditions. It is not a binding quote from the carrier.")

                if st.button("Select this estimate", key=f"select_{offer['carrier']}", use_container_width=True):
                    st.session_state["selected_offer"] = offer
                    st.session_state["scroll_to_booking"] = True
                    st.rerun()

        selected_offer = st.session_state.get("selected_offer")
        if selected_offer:
            st.divider()
            with st.container(border=True):
                st.markdown('<span class="section-anchor checkout-section"></span>', unsafe_allow_html=True)
                st.markdown(
                    """
                    <div id="booking-section"></div>
                    <div class="booking-head">
                        <div class="booking-kicker">Step 5 · Booking & payment</div>
                        <div class="booking-title">Request carrier confirmation</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f"""
                    <div class="booking-summary">
                        <strong>{selected_offer['carrier']} · {selected_offer['service']}</strong><br>
                        <span>{search['origin_city']} → {search['destination_city']} · {selected_offer['days']} days · Estimated total {format_euro(selected_offer['price'])}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                download_col, status_col = st.columns([1, 2])
                with download_col:
                    st.download_button(
                        "Download proposal",
                        data=proposal_text(search, selected_offer),
                        file_name="logihub_estimated_proposal.txt",
                        mime="text/plain",
                        use_container_width=True,
                    )
                with status_col:
                    st.markdown(
                        '<div class="payment-note"><strong>No charge today.</strong> The carrier must confirm availability and the final rate before any payment request is issued.</div>',
                        unsafe_allow_html=True,
                    )

                with st.form("booking_request_form"):
                    company_col, contact_col = st.columns(2)
                    with company_col:
                        company_name = st.text_input("Company name")
                    with contact_col:
                        contact_name = st.text_input("Contact person")

                    email_col, phone_col = st.columns(2)
                    with email_col:
                        email = st.text_input("Business email")
                    with phone_col:
                        phone = st.text_input("Phone number")

                    payment_method = st.selectbox(
                        "Preferred settlement method",
                        [
                            "Invoice / SEPA bank transfer",
                            "Corporate card after confirmation",
                            "SWIFT bank transfer",
                        ],
                    )
                    confirmation = st.checkbox(
                        "I understand that this is an estimated rate and that the final booking requires carrier confirmation."
                    )
                    booking_submitted = st.form_submit_button(
                        "Request booking confirmation",
                        type="primary",
                        use_container_width=True,
                    )

                if booking_submitted:
                    if not company_name.strip() or not contact_name.strip() or "@" not in email or not confirmation:
                        st.error("Please complete the company, contact and email fields and accept the confirmation statement.")
                    else:
                        st.success(
                            f"Demo booking request created for {company_name}. "
                            f"Preferred settlement: {payment_method}. No payment was charged and nothing was sent to {selected_offer['carrier']}."
                        )

            if st.session_state.pop("scroll_to_booking", False):
                components_html(
                    """
                    <script>
                        setTimeout(() => {
                            const target = window.parent.document.getElementById("booking-section");
                            if (target) {
                                target.scrollIntoView({behavior: "smooth", block: "start"});
                            }
                        }, 250);
                    </script>
                    """,
                    height=0,
                )
