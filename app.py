from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta
from html import escape
from uuid import uuid4

import streamlit as st
from streamlit.components.v1 import html as components_html

try:
    from openai import OpenAI
except ImportError:  # The grounded extractive fallback still works without it.
    OpenAI = None

try:
    from pypdf import PdfReader
except ImportError:  # Text, Markdown and CSV uploads still work without it.
    PdfReader = None


st.set_page_config(
    page_title="LogiHub AI — Freight operating hub",
    page_icon="🚚",
    layout="wide",
)


@st.dialog("Cookies & privacy", width="small", dismissible=False)
def cookie_consent_dialog() -> None:
    """Show a transparent, session-scoped consent notice on first visit."""
    st.markdown(
        """
        **Your privacy matters.**

        LogiHub uses essential cookies and session storage to keep form inputs,
        workspace choices and uploaded documents available while you use this demo.
        We do not use advertising cookies or cross-site tracking.
        """
    )
    with st.expander("How this demo handles data"):
        st.markdown(
            """
            - Uploaded files are processed only for the active session.
            - This MVP does not add uploaded documents to a permanent database.
            - You can end the session by closing the tab or clearing site data.
            """
        )

    if st.button(
        "Accept essential cookies & continue",
        type="primary",
        use_container_width=True,
        key="accept_cookie_notice",
    ):
        st.session_state["cookie_consent"] = "essential"
        st.rerun()


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


# Curated, public primary sources for the default Knowledge Brain. These short
# extracts are deliberately narrow: the assistant must abstain when the answer
# is not supported by this material or by a file uploaded by the user.
OFFICIAL_KNOWLEDGE = [
    {
        "title": "Union Customs Code",
        "section": "Regulation (EU) No 952/2013, Article 70",
        "text": (
            "The primary basis for the customs value of goods is the transaction value: "
            "the price actually paid or payable for goods sold for export to the customs "
            "territory of the Union, adjusted where necessary. The total payment includes "
            "payments made or to be made as a condition of sale of the imported goods."
        ),
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32013R0952",
    },
    {
        "title": "Union Customs Code",
        "section": "Regulation (EU) No 952/2013, Article 71",
        "text": (
            "When determining customs value under Article 70, additions may include certain "
            "commissions and brokerage, container and packing costs, assists supplied by the "
            "buyer, royalties or licence fees, proceeds accruing to the seller, and transport "
            "and insurance costs up to the place where goods enter the Union customs territory."
        ),
        "url": "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32013R0952",
    },
    {
        "title": "European Commission — EORI",
        "section": "Economic Operators Registration and Identification",
        "text": (
            "An EORI number is mandatory for customs clearance in the European Union for "
            "imports, exports and transit. It is used to identify economic operators and "
            "other persons in their dealings with customs authorities."
        ),
        "url": "https://taxation-customs.ec.europa.eu/customs/customs-procedures-import-and-export/customs-operations/economic-operators-registration-and-identification-number-eori_en",
    },
    {
        "title": "European Commission — TARIC",
        "section": "EU Customs Tariff (TARIC)",
        "text": (
            "TARIC is the multilingual integrated tariff database of the European Union. It "
            "integrates measures relating to the Common Customs Tariff and should be checked "
            "for the measures applicable to a product code. TARIC does not contain national "
            "VAT and excise-duty rates."
        ),
        "url": "https://taxation-customs.ec.europa.eu/online-services/online-services-and-databases-customs/eu-customs-tariff-taric_en",
    },
    {
        "title": "European Commission — Access2Markets",
        "section": "My Trade Assistant",
        "text": (
            "To look up an applicable import duty, use My Trade Assistant with the country of "
            "origin, destination country and product code. Results can include duties, rules "
            "of origin, import procedures and product requirements."
        ),
        "url": "https://trade.ec.europa.eu/access-to-markets/en/home",
    },
    {
        "title": "European Commission — Binding Tariff Information",
        "section": "European Binding Tariff Information (EBTI)",
        "text": (
            "Binding Tariff Information is a legal decision issued by an EU customs authority "
            "on the tariff classification of a product. It is the appropriate route when a "
            "business needs legal certainty about classification rather than an informal HS "
            "code suggestion."
        ),
        "url": "https://taxation-customs.ec.europa.eu/online-services/online-services-and-databases-customs/european-binding-tariff-information-ebti_en",
    },
]


# Each profile below represents one real, mode-specific service. Keeping modes
# separate prevents an Air search from inheriting a Roadfreight service name or
# link. Prices and reliability remain independent LogiHub estimates: carrier
# websites do not publish one live tariff table for every route and cargo mix.
def service_profile(
    profile_id: str,
    name: str,
    service: str,
    mode: str,
    logo: str,
    domain: str,
    source_url: str,
    rating: int,
    base_fee: float,
    km_rate: float,
    kg_rate: float,
    fuel_rate: float,
    speed_factor: float,
    handling_days: int,
    route_factor: float,
    color: str,
    hazardous: bool = True,
    temperature: bool = True,
) -> dict:
    return {
        "profile_id": profile_id,
        "name": name,
        "service": service,
        "mode": mode,
        "logo": logo,
        "logo_url": f"https://www.google.com/s2/favicons?domain={domain}&sz=128",
        "source_url": source_url,
        "rating": rating,
        "base_fee": base_fee,
        "km_rate": km_rate,
        "kg_rate": kg_rate,
        "fuel_rate": fuel_rate,
        "speed_factor": speed_factor,
        "handling_days": handling_days,
        "route_factor": route_factor,
        "hazardous": hazardous,
        "temperature": temperature,
        "color": color,
    }


CARRIERS = [
    # Road freight
    service_profile(
        "dsv-road", "DSV Road", "DSV Groupage / Direct", "Road", "DSV", "dsv.com",
        "https://www.dsv.com/en/our-solutions/modes-of-transport/road-transport",
        95, 260, 0.72, 0.050, 0.15, 1.08, 1, 1.18, "#E30613",
    ),
    service_profile(
        "rhenus-road", "Rhenus Logistics", "Rhenus European Groupage / LTL / FTL", "Road", "RH", "rhenus.group",
        "https://www.rhenus.group/de/en/road-transport/",
        93, 235, 0.66, 0.045, 0.14, 1.02, 1, 1.18, "#003B5C",
    ),
    service_profile(
        "dachser-road", "DACHSER", "DACHSER European Logistics", "Road", "DAC", "dachser.com",
        "https://www.dachser.com/en/european-logistics-51",
        95, 250, 0.69, 0.047, 0.14, 1.08, 1, 1.18, "#F6A800",
    ),
    service_profile(
        "girteka-road", "Girteka Logistics", "Girteka European FTL", "Road", "GIR", "girteka.eu",
        "https://www.girteka.eu/",
        92, 220, 0.62, 0.042, 0.13, 1.03, 1, 1.18, "#00A651",
    ),
    service_profile(
        "xpo-road", "XPO Logistics Europe", "XPO European LTL / FTL", "Road", "XPO", "xpo.com",
        "https://europe.xpo.com/en/transport-solutions/",
        92, 230, 0.64, 0.044, 0.14, 1.00, 1, 1.18, "#F15A22", temperature=False,
    ),
    service_profile(
        "hellmann-road", "Hellmann Worldwide Logistics", "Hellmann Roadfreight", "Road", "HWL", "hellmann.com",
        "https://www.hellmann.com/en/products/roadfreight",
        94, 245, 0.68, 0.048, 0.15, 1.07, 1, 1.18, "#E2231A",
    ),

    # Rail freight and intermodal main-haul services
    service_profile(
        "db-cargo-rail", "DB Cargo", "European Rail Freight Services", "Rail", "DB", "dbcargo.com",
        "https://www.dbcargo.com/rail-de-en/services",
        94, 460, 0.43, 0.026, 0.08, 1.00, 2, 1.12, "#EC0016", temperature=False,
    ),
    service_profile(
        "rcg-rail", "ÖBB Rail Cargo Group", "Intermodal Logistics", "Rail", "RCG", "railcargo.com",
        "https://www.railcargo.com/en/services/intermodal-logistics",
        95, 475, 0.41, 0.025, 0.08, 1.04, 2, 1.12, "#D71920",
    ),
    service_profile(
        "hupac-rail", "Hupac Intermodal", "European Shuttle Net", "Rail", "HUP", "hupac.com",
        "https://www.hupac.com/",
        93, 430, 0.38, 0.023, 0.07, 1.08, 2, 1.10, "#007A3D",
    ),
    service_profile(
        "lineas-rail", "Lineas", "European Rail Freight", "Rail", "LIN", "lineas.net",
        "https://lineas.net/en",
        92, 420, 0.39, 0.024, 0.08, 0.98, 2, 1.12, "#F4C300",
    ),
    service_profile(
        "dsv-rail", "DSV Rail", "European Rail Freight", "Rail", "DSV", "dsv.com",
        "https://www.dsv.com/en/our-solutions/modes-of-transport/rail-freight/rail-freight-transport",
        93, 485, 0.44, 0.027, 0.09, 1.02, 2, 1.12, "#E30613",
    ),
    service_profile(
        "sbb-rail", "SBB Cargo", "Cargo Rail / Cargo Express", "Rail", "SBB", "sbbcargo.com",
        "https://www.sbbcargo.com/de/angebot/transportleistungen/einzelwagen-wagengruppen.html",
        94, 470, 0.42, 0.026, 0.08, 1.03, 2, 1.11, "#E2001A",
    ),

    # Air cargo and air-freight forwarding
    service_profile(
        "lufthansa-air", "Lufthansa Cargo", "General Cargo · td.Pro / td.Flash", "Air", "LH", "lufthansa-cargo.com",
        "https://www.lufthansa-cargo.com/en/general-cargo",
        96, 690, 0.13, 2.05, 0.25, 1.10, 1, 1.05, "#05164D",
    ),
    service_profile(
        "dsv-air", "DSV Air", "Air Freight / AIR Direct", "Air", "DSV", "dsv.com",
        "https://www.dsv.com/en/our-solutions/modes-of-transport/air-freight",
        95, 780, 0.14, 2.15, 0.24, 1.05, 1, 1.05, "#E30613",
    ),
    service_profile(
        "dhl-air", "DHL Global Forwarding", "Air Freight", "Air", "DHL", "dhl.com",
        "https://www.dhl.com/de-en/home/global-forwarding.html",
        96, 820, 0.15, 2.25, 0.24, 1.08, 1, 1.05, "#D40511",
    ),
    service_profile(
        "turkish-air", "Turkish Cargo", "TK Smart / TK Premium", "Air", "TK", "turkishcargo.com",
        "https://www.turkishcargo.com/en",
        93, 650, 0.12, 1.95, 0.25, 1.00, 1, 1.08, "#C8102E",
    ),
    service_profile(
        "afkl-air", "Air France KLM Martinair Cargo", "General Cargo", "Air", "AFK", "afklcargo.com",
        "https://www.afklcargo.com/",
        94, 720, 0.13, 2.05, 0.24, 1.07, 1, 1.06, "#1B4F9C",
    ),
    service_profile(
        "cargolux-air", "Cargolux", "General Air Cargo", "Air", "CV", "cargolux.com",
        "https://www.cargolux.com/",
        94, 740, 0.13, 2.10, 0.25, 1.04, 1, 1.06, "#E2231A",
    ),

    # Ocean and short-sea freight
    service_profile(
        "maersk-sea", "Maersk", "Ocean Transport", "Sea", "MAE", "maersk.com",
        "https://www.maersk.com/transportation-services/ocean-transport",
        95, 620, 0.30, 0.018, 0.10, 1.04, 4, 1.35, "#00AEEF",
    ),
    service_profile(
        "msc-sea", "MSC", "Dry Cargo Shipping", "Sea", "MSC", "msc.com",
        "https://www.msc.com/en/solutions/dry-cargo",
        94, 590, 0.28, 0.017, 0.10, 1.02, 4, 1.35, "#FFB81C",
    ),
    service_profile(
        "hapag-sea", "Hapag-Lloyd", "Container Shipping", "Sea", "HLC", "hapag-lloyd.com",
        "https://www.hapag-lloyd.com/en/home.html",
        94, 610, 0.29, 0.018, 0.10, 1.03, 4, 1.35, "#F58220",
    ),
    service_profile(
        "dsv-sea", "DSV Sea", "Sea Freight", "Sea", "DSV", "dsv.com",
        "https://www.dsv.com/en/our-solutions/modes-of-transport/sea-freight",
        93, 640, 0.31, 0.019, 0.10, 1.00, 4, 1.35, "#E30613",
    ),
    service_profile(
        "dhl-sea", "DHL Global Forwarding", "Ocean Freight", "Sea", "DHL", "dhl.com",
        "https://www.dhl.com/de-en/home/global-forwarding.html",
        95, 660, 0.32, 0.019, 0.10, 1.05, 4, 1.35, "#D40511",
    ),
    service_profile(
        "cma-sea", "CMA CGM", "Container Shipping", "Sea", "CMA", "cma-cgm.com",
        "https://www.cma-cgm.com/",
        93, 600, 0.29, 0.017, 0.10, 1.01, 4, 1.35, "#003B71",
    ),
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

MODE_SPEED_KM_DAY = {"Road": 650, "Rail": 850, "Air": 3000, "Sea": 500}
MODE_CO2_G_TON_KM = {"Road": 62, "Rail": 22, "Air": 602, "Sea": 16}


# -----------------------------------------------------------------------------
# Grounded Knowledge Brain helpers
# -----------------------------------------------------------------------------

STOP_WORDS = {
    "about", "after", "also", "and", "are", "can", "does", "for", "from",
    "goods", "have", "how", "into", "must", "need", "should", "that", "the",
    "their", "this", "use", "what", "when", "where", "which", "with", "your",
}


def knowledge_tokens(value: str) -> set[str]:
    """Return stable search tokens without sending document contents elsewhere."""
    return {
        token
        for token in re.findall(r"[a-z0-9][a-z0-9.-]+", value.lower())
        if len(token) > 2 and token not in STOP_WORDS
    }


def chunk_text(text: str, title: str, source_url: str = "") -> list[dict]:
    """Split an uploaded document into small, citable retrieval chunks."""
    clean = re.sub(r"\s+", " ", text).strip()
    if not clean:
        return []
    words = clean.split()
    chunks = []
    for index in range(0, len(words), 180):
        part = " ".join(words[index:index + 220]).strip()
        if len(part) < 40:
            continue
        chunks.append(
            {
                "title": title,
                "section": f"Uploaded document · passage {len(chunks) + 1}",
                "text": part,
                "url": source_url,
            }
        )
    return chunks


def extract_uploaded_knowledge(uploaded_files) -> tuple[list[dict], list[str]]:
    """Extract text from PDF, TXT, Markdown and CSV files uploaded in the UI."""
    chunks: list[dict] = []
    errors: list[str] = []
    for uploaded_file in uploaded_files or []:
        try:
            raw = uploaded_file.getvalue()
            if uploaded_file.name.lower().endswith(".pdf"):
                if PdfReader is None:
                    errors.append(f"{uploaded_file.name}: PDF support is not installed.")
                    continue
                reader = PdfReader(uploaded_file)
                text = "\n".join((page.extract_text() or "") for page in reader.pages)
            else:
                text = raw.decode("utf-8", errors="replace")
            file_chunks = chunk_text(text, uploaded_file.name)
            if not file_chunks:
                errors.append(f"{uploaded_file.name}: no readable text was found.")
            chunks.extend(file_chunks)
        except Exception as exc:  # Keep one bad file from breaking the live demo.
            errors.append(f"{uploaded_file.name}: {exc}")
    return chunks, errors


def retrieve_knowledge(question: str, documents: list[dict], limit: int = 4) -> list[dict]:
    """Rank passages by transparent token overlap and phrase matches."""
    query_tokens = knowledge_tokens(question)
    if not query_tokens:
        return []
    ranked = []
    for document in documents:
        haystack = f"{document['title']} {document['section']} {document['text']}"
        document_tokens = knowledge_tokens(haystack)
        overlap = query_tokens & document_tokens
        score = len(overlap) * 4
        lowered = haystack.lower()
        score += sum(2 for token in query_tokens if token in lowered)
        if "eori" in question.lower() and "eori" in lowered:
            score += 10
        if any(term in question.lower() for term in ("tariff", "duty", "hs code", "classification")):
            score += 5 if any(term in lowered for term in ("taric", "tariff", "classification")) else 0
        if any(term in question.lower() for term in ("customs value", "valuation", "transaction value")):
            score += 7 if any(term in lowered for term in ("customs value", "transaction value")) else 0
        if score:
            ranked.append((score, document))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [dict(document, score=score) for score, document in ranked[:limit]]


def secret_value(name: str) -> str:
    """Read an optional Streamlit secret without failing on local machines."""
    try:
        return str(st.secrets.get(name, "")).strip()
    except Exception:
        return ""


def grounded_extract_answer(question: str, passages: list[dict]) -> str:
    """Build a useful, fully extractive answer when no model key is configured."""
    if not passages:
        return (
            "I cannot answer that from the loaded sources. Upload the relevant regulation, "
            "form or firm FAQ, or ask a narrower question."
        )
    lines = [
        "Based only on the most relevant loaded passages:",
        "",
    ]
    for index, passage in enumerate(passages[:3], start=1):
        sentences = re.split(r"(?<=[.!?])\s+", passage["text"])
        excerpt = " ".join(sentences[:2]).strip()
        lines.append(f"- {excerpt} **[{index}]**")
    lines.extend(
        [
            "",
            "This is an operational research aid, not a binding customs decision or legal advice.",
        ]
    )
    return "\n".join(lines)


def grounded_ai_answer(question: str, passages: list[dict]) -> tuple[str, str]:
    """Use OpenAI when configured; otherwise return an honest extractive answer."""
    api_key = secret_value("OPENAI_API_KEY")
    if not passages:
        return grounded_extract_answer(question, passages), "No supported passage found"
    if not api_key or OpenAI is None:
        return grounded_extract_answer(question, passages), "Grounded extractive mode"

    context = "\n\n".join(
        f"[{index}] {passage['title']} — {passage['section']}\n{passage['text']}"
        for index, passage in enumerate(passages, start=1)
    )
    instructions = (
        "You are LogiHub's customs knowledge assistant. Answer only from the supplied context. "
        "Cite every material claim with [1], [2], etc. If the context is insufficient, say so. "
        "Do not invent tariff rates, HS classifications, deadlines or legal conclusions. Keep "
        "the answer concise and end with: 'Operational research aid — verify with customs.'"
    )
    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=secret_value("OPENAI_MODEL") or "gpt-4o-mini",
            instructions=instructions,
            input=f"Question: {question}\n\nApproved context:\n{context}",
            max_output_tokens=650,
        )
        return response.output_text.strip(), "AI synthesis · grounded in retrieved passages"
    except Exception as exc:
        fallback = grounded_extract_answer(question, passages)
        return fallback, f"AI unavailable; used grounded extractive mode ({type(exc).__name__})"


def render_knowledge_brain() -> None:
    """Render the source-grounded Q&A workspace and stop before the quote workflow."""
    st.markdown(
        """
        <div class="knowledge-hero">
            <div class="knowledge-kicker">Grounded Knowledge Brain</div>
            <h2>Ask the rules. See the evidence.</h2>
            <p>Search approved EU customs material together with your firm's PDFs, forms and FAQs. Every answer is limited to retrieved passages and shows its sources.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    source_col, answer_col = st.columns([0.9, 1.45], gap="large")
    with source_col:
        with st.container(border=True):
            st.markdown('<div class="step-label">Knowledge sources</div>', unsafe_allow_html=True)
            st.subheader("Load firm material")
            uploaded_files = st.file_uploader(
                "PDF, TXT, Markdown or CSV",
                type=["pdf", "txt", "md", "csv"],
                accept_multiple_files=True,
                help="Files are processed for this browser session and are not added to the public repository.",
            )
            uploaded_chunks, upload_errors = extract_uploaded_knowledge(uploaded_files)
            st.metric("Approved passages", len(OFFICIAL_KNOWLEDGE) + len(uploaded_chunks))
            st.caption(
                f"{len(OFFICIAL_KNOWLEDGE)} curated EU passages"
                + (f" · {len(uploaded_chunks)} uploaded passages" if uploaded_chunks else "")
            )
            for error in upload_errors:
                st.warning(error)
            with st.expander("View built-in official sources"):
                for source in OFFICIAL_KNOWLEDGE:
                    st.markdown(f"- [{source['title']} — {source['section']}]({source['url']})")
            mode_label = "AI synthesis enabled" if secret_value("OPENAI_API_KEY") and OpenAI else "Grounded extractive mode"
            st.markdown(f'<div class="source-status"><span></span>{mode_label}</div>', unsafe_allow_html=True)

    with answer_col:
        with st.container(border=True):
            st.markdown('<div class="step-label">Source-cited Q&A</div>', unsafe_allow_html=True)
            st.subheader("Ask your knowledge base")
            examples = [
                "How is customs value calculated under the Union Customs Code?",
                "When is an EORI number required?",
                "Where should I verify the import duty for a product?",
                "How can I obtain legal certainty about an HS classification?",
            ]
            selected_example = st.selectbox("Example question", ["Write my own question", *examples])
            default_question = "" if selected_example == "Write my own question" else selected_example
            with st.form("knowledge_question_form"):
                question = st.text_area(
                    "Question",
                    value=default_question,
                    placeholder="Example: Which costs must be added to the transaction value?",
                    height=110,
                )
                ask_clicked = st.form_submit_button("Answer from approved sources", type="primary", use_container_width=True)

            if ask_clicked:
                documents = [*OFFICIAL_KNOWLEDGE, *uploaded_chunks]
                passages = retrieve_knowledge(question, documents)
                answer, answer_mode = grounded_ai_answer(question, passages)
                st.session_state["knowledge_result"] = {
                    "question": question,
                    "answer": answer,
                    "mode": answer_mode,
                    "passages": passages,
                }

            result = st.session_state.get("knowledge_result")
            if result:
                st.markdown(f'<div class="answer-mode">{escape(result["mode"])}</div>', unsafe_allow_html=True)
                st.markdown(result["answer"])
                if result["passages"]:
                    st.markdown("#### Sources used")
                    for index, passage in enumerate(result["passages"], start=1):
                        label = f"[{index}] {passage['title']} — {passage['section']}"
                        if passage.get("url"):
                            st.markdown(f"**{label}** · [Open official source]({passage['url']})")
                        else:
                            st.markdown(f"**{label}**")
                        st.caption(passage["text"][:420] + ("…" if len(passage["text"]) > 420 else ""))
            else:
                st.info("Choose an example or enter a question. The assistant will show the exact passages used.")

    st.markdown(
        '<div class="demo-note"><span class="demo-icon">i</span><span><strong>Grounding rule.</strong> The assistant must abstain when the answer is not supported by an approved or uploaded source. It does not replace a binding customs decision.</span></div>',
        unsafe_allow_html=True,
    )


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


def mode_suitability(mode: str, distance: float, weight: float, days: int, priority: str) -> float:
    """Estimate how well a mode fits the shipment before carrier ranking."""
    if mode == "Road":
        score = 0.95
        if distance > 1500:
            score -= 0.12
        if weight > 15000:
            score -= 0.08
        if priority == "Fastest delivery":
            score += 0.03
    elif mode == "Rail":
        score = 0.48 + min(distance / 2500, 1) * 0.18 + min(weight / 20000, 1) * 0.20
        if days >= 4:
            score += 0.12
        if distance < 300:
            score -= 0.20
        if priority == "Highest reliability":
            score += 0.05
    elif mode == "Air":
        score = 0.45
        if days <= 2:
            score += 0.42
        elif days <= 4:
            score += 0.28
        else:
            score += 0.08
        if weight <= 1500:
            score += 0.10
        if priority == "Fastest delivery":
            score += 0.12
        if priority == "Lowest price":
            score -= 0.18
    else:  # Sea
        score = 0.32
        if distance >= 1200:
            score += 0.25
        if weight >= 6000:
            score += 0.20
        if days >= 8:
            score += 0.18
        if distance < 700:
            score -= 0.18
        if days < 5:
            score -= 0.25
        if priority == "Lowest price":
            score += 0.12

    return max(0.05, min(1.0, score))


def mode_reason(mode: str) -> str:
    return {
        "Road": "direct European road coverage and flexible first/last-mile access",
        "Rail": "a lower-emission rail main haul with road terminal connections",
        "Air": "the shortest line-haul transit through European cargo airports",
        "Sea": "cost-efficient container transport with inland port connections",
    }[mode]


def calculate_offers(search: dict) -> list[dict]:
    origin_coordinates = CITIES[search["origin_country"]][search["origin_city"]]
    destination_coordinates = CITIES[search["destination_country"]][search["destination_city"]]

    direct_distance = max(80, haversine_km(origin_coordinates, destination_coordinates))
    allowed_days = max(1, (search["delivery_date"] - search["ready_date"]).days + search["flex_days"])
    offers = []

    for carrier in CARRIERS:
        # An explicitly selected mode is a strict filter, not a pricing hint.
        if search["mode"] != "Let LogiHub choose" and carrier["mode"] != search["mode"]:
            continue
        if search["hazardous"] and not carrier["hazardous"]:
            continue
        if search["temperature"] and not carrier["temperature"]:
            continue

        mode = carrier["mode"]
        suitability = (
            1.0
            if search["mode"] != "Let LogiHub choose"
            else mode_suitability(mode, direct_distance, search["weight"], allowed_days, search["priority"])
        )
        # Automatic search removes clearly impractical modes. An explicit mode
        # remains available, provided it can meet the requested delivery date.
        if search["mode"] == "Let LogiHub choose" and suitability < 0.25:
            continue

        distance = direct_distance * carrier["route_factor"]

        transit_days = max(
            1,
            math.ceil(distance / (MODE_SPEED_KM_DAY[mode] * carrier["speed_factor"]))
            + carrier["handling_days"],
        )
        if transit_days > allowed_days:
            continue

        transport_cost = (
            carrier["base_fee"]
            + distance * carrier["km_rate"]
            + search["weight"] * carrier["kg_rate"]
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
        door_fee = ({"Road": 135, "Rail": 220, "Air": 280, "Sea": 320}[mode] if search["door"] else 0)
        total_price = transport_cost + fuel_surcharge + customs_fee + insurance_fee + door_fee

        co2_kg = distance * (search["weight"] / 1000) * MODE_CO2_G_TON_KM[mode] / 1000

        offers.append(
            {
                "profile_id": carrier["profile_id"],
                "carrier": carrier["name"],
                "service": carrier["service"],
                "logo": carrier["logo"],
                "logo_url": carrier["logo_url"],
                "source_url": carrier["source_url"],
                "rating": carrier["rating"],
                "color": carrier["color"],
                "mode": mode,
                "mode_fit": suitability,
                "mode_reason": mode_reason(mode),
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
        "Best balance": (0.30, 0.20, 0.25, 0.25),
        "Lowest price": (0.62, 0.08, 0.15, 0.15),
        "Fastest delivery": (0.08, 0.58, 0.19, 0.15),
        "Highest reliability": (0.10, 0.10, 0.65, 0.15),
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
                + weights[3] * offer["mode_fit"]
            )
        )

    offers.sort(key=lambda offer: (-offer["match_score"], offer["price"]))

    cheapest_profile = min(offers, key=lambda offer: offer["price"])["profile_id"]
    fastest_profile = min(offers, key=lambda offer: offer["days"])["profile_id"]
    reliable_profile = max(offers, key=lambda offer: offer["rating"])["profile_id"]

    for index, offer in enumerate(offers):
        badges = []
        if index == 0:
            badges.append("Recommended")
        if offer["profile_id"] == cheapest_profile:
            badges.append("Lowest price")
        if offer["profile_id"] == fastest_profile:
            badges.append("Fastest")
        if offer["profile_id"] == reliable_profile:
            badges.append("Most reliable")
        offer["badges"] = badges

    return offers


def format_euro(value: float) -> str:
    return f"€{value:,.0f}".replace(",", " ")


def shipment_documents(search: dict, offer: dict) -> list[str]:
    """Return a concise, non-binding document checklist for the demo brief."""
    transport_document = {
        "Road": "CMR consignment note",
        "Rail": "CIM rail consignment note",
        "Air": "Air Waybill (AWB)",
        "Sea": "Bill of Lading / Sea Waybill",
    }[offer["mode"]]
    documents = ["Commercial invoice", "Packing list", transport_document]
    if search["customs"]:
        documents.extend(["Customs declaration", "EORI number", "Commodity / HS code"])
    if search["hazardous"]:
        dangerous_goods_document = {
            "Road": "ADR dangerous-goods declaration",
            "Rail": "RID dangerous-goods declaration",
            "Air": "IATA Shipper's Declaration for Dangerous Goods",
            "Sea": "IMDG dangerous-goods declaration",
        }[offer["mode"]]
        documents.extend(["Safety Data Sheet (SDS)", dangerous_goods_document])
    if search["temperature"]:
        documents.append("Temperature-handling instructions")
    if offer["mode"] == "Sea":
        documents.append("Verified Gross Mass (VGM), when containerised")
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
    documents = "\n".join(f"- {item}" for item in shipment_documents(search, offer))
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


def build_booking_receipt(
    search: dict,
    offer: dict,
    company_name: str,
    contact_name: str,
    email: str,
    phone: str,
    payment_method: str,
) -> dict:
    """Create one stable confirmation record after the demo form is submitted."""
    return {
        "offer_profile_id": offer["profile_id"],
        "reference": f"LH-{datetime.now().strftime('%y%m%d')}-{uuid4().hex[:6].upper()}",
        "created_at": datetime.now().strftime("%d %b %Y, %H:%M"),
        "company": company_name.strip(),
        "contact_name": contact_name.strip(),
        "email": email.strip(),
        "phone": phone.strip() or "Not provided",
        "carrier": offer["carrier"],
        "service": offer["service"],
        "mode": offer["mode"],
        "route": (
            f"{search['origin_city']}, {search['origin_country']} → "
            f"{search['destination_city']}, {search['destination_country']}"
        ),
        "cargo": search["cargo_description"],
        "shipment_size": f"{search['weight']:,.0f} kg · {search['packages']} packages",
        "transit": f"{offer['days']} days",
        "estimated_arrival": offer["arrival_date"].strftime("%d %b %Y"),
        "estimated_total": format_euro(offer["price"]),
        "payment_method": payment_method,
    }


def receipt_card_html(receipt: dict) -> str:
    """Return a safe, styled receipt for display inside the Streamlit page."""
    safe = {key: escape(str(value)) for key, value in receipt.items()}
    return f"""
    <div id="receipt-section" class="receipt-card">
        <div class="receipt-head">
            <div>
                <div class="receipt-kicker">LogiHub AI · Booking confirmation</div>
                <div class="receipt-title">Request received</div>
                <div class="receipt-reference">Reference {safe['reference']} · {safe['created_at']}</div>
            </div>
            <div class="receipt-status"><span></span> Pending carrier confirmation</div>
        </div>
        <div class="receipt-grid">
            <div class="receipt-cell">
                <small>Customer</small>
                <strong>{safe['contact_name']}</strong>
                <span>{safe['company']}<br>{safe['email']}<br>{safe['phone']}</span>
            </div>
            <div class="receipt-cell">
                <small>Selected freight service</small>
                <strong>{safe['carrier']}</strong>
                <span>{safe['service']} · {safe['mode']}<br>{safe['transit']} · arrival {safe['estimated_arrival']}</span>
            </div>
            <div class="receipt-cell">
                <small>Shipment</small>
                <strong>{safe['route']}</strong>
                <span>{safe['cargo']}<br>{safe['shipment_size']}</span>
            </div>
            <div class="receipt-cell">
                <small>Preferred settlement</small>
                <strong>{safe['payment_method']}</strong>
                <span>No payment has been charged.</span>
            </div>
        </div>
        <div class="receipt-total">
            <div><small>Estimated order total</small><span>Final rate requires carrier confirmation</span></div>
            <strong>{safe['estimated_total']}</strong>
        </div>
        <div class="receipt-footnote">
            This confirmation records a demo booking request. It is not a carrier-issued invoice or a binding transport contract.
        </div>
    </div>
    """


def receipt_download_html(receipt: dict) -> str:
    """Create a standalone receipt that opens in any browser and prints to PDF."""
    safe = {key: escape(str(value)) for key, value in receipt.items()}
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>LogiHub confirmation {safe['reference']}</title>
<style>
body{{margin:0;background:#f4f7f5;color:#101514;font:15px/1.5 Arial,sans-serif}}
.sheet{{max-width:820px;margin:40px auto;background:white;border:1px solid #dce6e1;border-radius:24px;padding:34px;box-shadow:0 18px 45px #223f3520}}
.top{{display:flex;justify-content:space-between;gap:24px;align-items:flex-start;border-bottom:1px solid #dce6e1;padding-bottom:22px}}
.brand{{font-size:14px;font-weight:800;color:#177760;text-transform:uppercase;letter-spacing:.1em}}
h1{{margin:8px 0 4px;font-size:32px}} .muted{{color:#64736e}}
.status{{background:#ecffd0;color:#25420f;border-radius:999px;padding:8px 12px;font-weight:700}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:22px 0}}
.cell{{border:1px solid #dce6e1;border-radius:15px;padding:16px}} small{{display:block;color:#64736e;margin-bottom:6px}} strong{{display:block;margin-bottom:5px}}
.total{{display:flex;justify-content:space-between;align-items:center;background:#101514;color:white;border-radius:18px;padding:18px 20px}} .total strong{{font-size:28px;margin:0}}
.note{{color:#64736e;font-size:12px;margin-top:18px}}
@media(max-width:650px){{.sheet{{margin:0;border-radius:0;padding:22px}}.top,.total{{display:block}}.status{{display:inline-block;margin-top:14px}}.grid{{grid-template-columns:1fr}}.total strong{{margin-top:8px}}}}
</style>
</head>
<body><main class="sheet">
<div class="top"><div><div class="brand">LogiHub AI · Booking confirmation</div><h1>Request received</h1><div class="muted">Reference {safe['reference']} · {safe['created_at']}</div></div><div class="status">Pending carrier confirmation</div></div>
<div class="grid">
<div class="cell"><small>Customer</small><strong>{safe['contact_name']}</strong>{safe['company']}<br>{safe['email']}<br>{safe['phone']}</div>
<div class="cell"><small>Selected freight service</small><strong>{safe['carrier']}</strong>{safe['service']} · {safe['mode']}<br>{safe['transit']} · arrival {safe['estimated_arrival']}</div>
<div class="cell"><small>Shipment</small><strong>{safe['route']}</strong>{safe['cargo']}<br>{safe['shipment_size']}</div>
<div class="cell"><small>Preferred settlement</small><strong>{safe['payment_method']}</strong>No payment has been charged.</div>
</div>
<div class="total"><div><small>Estimated order total</small>Final rate requires carrier confirmation</div><strong>{safe['estimated_total']}</strong></div>
<div class="note">This confirmation records a demo booking request. It is not a carrier-issued invoice or a binding transport contract.</div>
</main></body></html>"""


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
        .knowledge-hero {
            position:relative; overflow:hidden; margin:.35rem 0 1rem; padding:1.4rem 1.5rem;
            color:white; background:linear-gradient(125deg,#101514 0%,#173D35 62%,#1B6855 100%);
            border-radius:26px; box-shadow:0 20px 48px rgba(16,21,20,.13);
        }
        .knowledge-hero:after {
            content:""; position:absolute; width:210px; height:210px; right:-55px; top:-105px;
            border-radius:50%; background:rgba(200,255,98,.20);
        }
        .knowledge-kicker { color:#C8FF62; font-size:.7rem; font-weight:900; letter-spacing:.12em; text-transform:uppercase; }
        .knowledge-hero h2 { position:relative; z-index:1; color:white; margin:.45rem 0 .35rem; font-size:2rem; letter-spacing:-.04em; }
        .knowledge-hero p { position:relative; z-index:1; max-width:760px; color:#D6E4DF; margin:0; line-height:1.55; }
        .source-status, .answer-mode {
            display:inline-flex; align-items:center; gap:.45rem; margin-top:.65rem; padding:.38rem .62rem;
            color:#185845; background:#E4F8F2; border:1px solid #C5EADF; border-radius:999px;
            font-size:.7rem; font-weight:800;
        }
        .source-status span { width:7px; height:7px; border-radius:50%; background:#20A77D; }
        .answer-mode { color:#31510E; background:#ECFFD0; border-color:#D1F69A; }
        [data-testid="stFileUploader"] { padding:.35rem; border-radius:15px; background:#F8FAF9; }
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
            color:var(--black) !important;
            background:#FBFCFE !important;
            border:1px solid #D7E1EC !important;
            border-radius:12px !important;
        }
        [data-testid="stSelectbox"] [data-baseweb="select"] > div {
            color:var(--black) !important;
            background:#FBFCFE !important;
            border:1px solid #D7E1EC !important;
            border-radius:12px !important;
            cursor:pointer !important;
        }
        [data-testid="stDateInput"] [data-baseweb="input"],
        [data-testid="stNumberInputContainer"],
        [data-testid="stTextInputRootElement"] {
            color:var(--black) !important;
            background:#FBFCFE !important;
            border:1px solid #D7E1EC !important;
            border-radius:12px !important;
            overflow:hidden !important;
            cursor:default !important;
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
            caret-color:#101514 !important;
            cursor:default !important;
            opacity:1 !important;
        }
        [data-testid="stTextInput"],
        [data-testid="stTextInput"] [data-baseweb="input"],
        [data-testid="stTextInput"] [data-baseweb="base-input"],
        [data-testid="stNumberInput"],
        [data-testid="stNumberInput"] [data-baseweb="input"],
        [data-testid="stNumberInput"] [data-baseweb="base-input"],
        [data-testid="stDateInput"],
        [data-testid="stDateInput"] [data-baseweb="input"],
        [data-testid="stDateInput"] [data-baseweb="base-input"] {
            cursor:default !important;
        }
        [data-testid="stSelectbox"],
        [data-testid="stSelectbox"] *,
        [data-testid="stCheckbox"] label,
        [data-testid="stRadio"] label {
            cursor:pointer !important;
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
            cursor:pointer !important;
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
        .receipt-card {
            margin-top:1rem; padding:1.15rem; color:var(--black); background:#FFFFFF;
            border:1px solid #DCE6E1; border-radius:22px; box-shadow:0 16px 38px rgba(34,65,58,.08);
        }
        .receipt-head { display:flex; align-items:flex-start; justify-content:space-between; gap:1rem; padding-bottom:1rem; border-bottom:1px solid #E2EAE6; }
        .receipt-kicker { color:#177760; font-size:.67rem; font-weight:900; letter-spacing:.11em; text-transform:uppercase; }
        .receipt-title { margin:.3rem 0 .15rem; font-size:1.55rem; line-height:1.05; font-weight:900; letter-spacing:-.035em; }
        .receipt-reference { color:#64736E; font-size:.75rem; }
        .receipt-status { flex:none; display:inline-flex; align-items:center; gap:.45rem; color:#31510E; background:#ECFFD0; border:1px solid #D1F69A; border-radius:999px; padding:.42rem .65rem; font-size:.7rem; font-weight:800; }
        .receipt-status span { width:7px; height:7px; border-radius:50%; background:#82C826; }
        .receipt-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:.65rem; margin:1rem 0; }
        .receipt-cell { min-width:0; padding:.8rem; background:#F8FAF9; border:1px solid #E0E8E4; border-radius:15px; }
        .receipt-cell small { display:block; color:#72807B; font-size:.66rem; font-weight:750; text-transform:uppercase; letter-spacing:.06em; margin-bottom:.3rem; }
        .receipt-cell strong { display:block; color:var(--black); font-size:.85rem; overflow-wrap:anywhere; }
        .receipt-cell span { display:block; color:#5B6A65; font-size:.75rem; line-height:1.5; margin-top:.2rem; overflow-wrap:anywhere; }
        .receipt-total { display:flex; align-items:center; justify-content:space-between; gap:1rem; color:white; background:var(--black); border-radius:17px; padding:.85rem 1rem; }
        .receipt-total small { display:block; color:#AEBBB7; font-size:.66rem; text-transform:uppercase; letter-spacing:.07em; }
        .receipt-total span { color:#BFCBC7; font-size:.7rem; }
        .receipt-total strong { flex:none; color:white; font-size:1.55rem; letter-spacing:-.04em; }
        .receipt-footnote { color:#6A7873; font-size:.68rem; line-height:1.45; margin-top:.65rem; }
        @media (max-width: 820px) {
            .journey-strip { grid-template-columns:repeat(2,1fr); }
            .hero-shell { border-radius:22px; padding:1.15rem; }
            .network-pill { display:none; }
            .hero-grid { grid-template-columns:1fr; }
            .hero-card { display:none; }
            .hero-title { font-size:3.35rem; }
            .ai-grid { grid-template-columns:1fr; }
            .receipt-grid { grid-template-columns:1fr; }
        }
        @media (max-width: 700px) {
            .block-container { padding-left:1rem; padding-right:1rem; }
            .price, .price-note { text-align:left; }
            .journey-strip { grid-template-columns:1fr 1fr; gap:.25rem; }
            .journey-item { font-size:.7rem; }
            .hero-title { font-size:1.8rem; }
            .receipt-head, .receipt-total { display:block; }
            .receipt-status { margin-top:.7rem; }
            .receipt-total strong { display:block; margin-top:.35rem; }
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if "cookie_consent" not in st.session_state:
    cookie_consent_dialog()

st.markdown(
    f"""
    <div class="hero-shell">
        <div class="brand-row">
            <div class="brand">
                <div class="brand-mark">LH</div>
                <div>
                    <div class="brand-name">LogiHub AI</div>
                    <div class="brand-caption">AI operating hub for freight teams</div>
                </div>
            </div>
            <div class="network-pill"><span class="network-dot"></span> Grounded workflow MVP</div>
        </div>
        <div class="hero-grid">
            <div class="hero-copy">
                <div class="eyebrow">Intake · knowledge · first useful output</div>
                <h1 class="hero-title">Run freight.<br>Know the rules.</h1>
                <p class="hero-subtitle">Turn an incoming shipment request into a source-cited customs brief, ranked transport options and a client-ready proposal in one workspace.</p>
                <div class="hero-facts">
                    <span class="hero-fact">Source-grounded Q&amp;A</span>
                    <span class="hero-fact">Explainable freight matching</span>
                    <span class="hero-fact">Client-ready handoff</span>
                </div>
            </div>
            <div class="hero-card">
                <div class="hero-card-label">Operations snapshot</div>
                <div class="hero-card-number">2×</div>
                <div class="hero-card-copy">One hub combines freight intake and quoting with a grounded customs Knowledge Brain.</div>
                <div class="hero-card-line">Built for freight teams</div>
            </div>
        </div>
    </div>
    <div class="journey-strip">
        <div class="journey-item"><span class="journey-number">1</span> Route</div>
        <div class="journey-item"><span class="journey-number">2</span> Schedule</div>
        <div class="journey-item"><span class="journey-number">3</span> Cargo</div>
        <div class="journey-item"><span class="journey-number">4</span> Proposal &amp; handoff</div>
    </div>
    <div class="demo-note"><span class="demo-icon">i</span><span><strong>Independent MVP.</strong> Customs answers cite approved sources. Carrier rates, availability and reliability are LogiHub estimates—not live quotes. Real company names are used for comparison; no affiliation is implied.</span></div>
    """,
    unsafe_allow_html=True,
)

workspace = st.radio(
    "Choose workspace",
    ["Freight intake & proposal", "Customs Knowledge Brain"],
    horizontal=True,
    label_visibility="collapsed",
    key="active_workspace",
)

if workspace == "Customs Knowledge Brain":
    render_knowledge_brain()
    st.stop()


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
        st.session_state.pop("booking_receipt", None)


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
    search_scope = (
        "all viable road, rail, air and sea services"
        if search["mode"] == "Let LogiHub choose"
        else f"{search['mode']}-only services"
    )
    st.caption(f"Search scope: {search_scope}. Incompatible service profiles are excluded before ranking.")

    if not offers:
        if search["mode"] == "Let LogiHub choose":
            st.warning(
                "No carrier profile matches all selected cargo requirements and dates. "
                "Try adding schedule flexibility or changing a special-handling requirement."
            )
        else:
            st.warning(
                f"No {search['mode'].lower()} service can meet the selected delivery window and handling requirements. "
                "Try adding schedule flexibility or choose Let LogiHub choose."
            )
    else:
        best = offers[0]
        price_difference = best["price"] - min(offer["price"] for offer in offers)
        explanation = (
            f"{best['carrier']} is the strongest match for your **{search['priority'].lower()}** priority. "
            f"Its **{best['mode']}** service provides {best['mode_reason']}. "
            f"It delivers in **{best['days']} days**, has a **{best['rating']}% estimated reliability score**, "
            f"and costs **{format_euro(best['price'])}**."
        )
        if price_difference > 0:
            explanation += f" That is {format_euro(price_difference)} above the cheapest compatible option."

        st.info(f"**Smart recommendation:** {explanation}")

        documents = shipment_documents(search, best)
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
                <div class="ai-brief-kicker">✦ Operations brief</div>
                <h3>What needs attention before booking</h3>
                <p>LogiHub translated the intake data into an explainable operational checklist for the selected recommendation.</p>
                <div class="ai-grid">
                    <div class="ai-cell"><strong>Why this match</strong><span>{best['carrier']} ranks highest for {search['priority'].lower()}, with {best['days']}-day estimated transit and a {best['match_score']}% match score.</span></div>
                    <div class="ai-cell"><strong>Document checklist</strong><span>{document_preview}</span></div>
                    <div class="ai-cell"><strong>Customs & risk flags</strong><span>{customs_summary}<br><br>{risk_preview}</span></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        for rank, offer in enumerate(offers[:8], start=1):
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
                    st.caption("Independent LogiHub estimate based on route, weight, selected mode and illustrative 2026 European freight-market assumptions. It is not a binding quote from the carrier.")

                if st.button("Select this estimate", key=f"select_{offer['profile_id']}_{rank}", use_container_width=True):
                    st.session_state["selected_offer"] = offer
                    st.session_state.pop("booking_receipt", None)
                    scroll_request_id = st.session_state.get("scroll_request_id", 0) + 1
                    st.session_state["scroll_request_id"] = scroll_request_id
                    st.session_state["scroll_to_booking"] = scroll_request_id
                    st.rerun()

        selected_offer = st.session_state.get("selected_offer")
        if selected_offer:
            booking_anchor_id = f"booking-section-{st.session_state.get('scroll_request_id', 0)}"
            st.divider()
            with st.container(border=True):
                st.markdown('<span class="section-anchor checkout-section"></span>', unsafe_allow_html=True)
                st.markdown(
                    f"""
                    <div id="{booking_anchor_id}"></div>
                    <div class="booking-head">
                        <div class="booking-kicker">Step 5 · Carrier handoff</div>
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
                    if not company_name.strip() or not contact_name.strip() or "@" not in email.strip() or not confirmation:
                        st.error("Please complete the company, contact and email fields and accept the confirmation statement.")
                    else:
                        receipt = build_booking_receipt(
                            search,
                            selected_offer,
                            company_name,
                            contact_name,
                            email,
                            phone,
                            payment_method,
                        )
                        st.session_state["booking_receipt"] = receipt
                        st.session_state["scroll_to_receipt"] = receipt["reference"]
                        st.success(
                            f"Booking request {receipt['reference']} was created for {company_name}. "
                            "Your confirmation receipt is ready below."
                        )

                receipt = st.session_state.get("booking_receipt")
                if receipt and receipt.get("offer_profile_id") == selected_offer["profile_id"]:
                    st.markdown(receipt_card_html(receipt), unsafe_allow_html=True)
                    st.download_button(
                        "Download confirmation receipt",
                        data=receipt_download_html(receipt),
                        file_name=f"logihub_confirmation_{receipt['reference']}.html",
                        mime="text/html",
                        key=f"download_receipt_{receipt['reference']}",
                        use_container_width=True,
                    )

            scroll_request_id = st.session_state.pop("scroll_to_booking", None)
            if scroll_request_id is not None:
                components_html(
                    f"""
                    <script>
                        (() => {{
                            const requestId = {int(scroll_request_id)};
                            let attempts = 0;
                            const scrollToBooking = () => {{
                                const target = window.parent.document.getElementById("booking-section-{int(scroll_request_id)}");
                                attempts += 1;
                                if (target) {{
                                    target.scrollIntoView({{behavior: "smooth", block: "start"}});
                                    return true;
                                }}
                                return attempts >= 20;
                            }};
                            if (!scrollToBooking()) {{
                                const timer = window.setInterval(() => {{
                                    if (scrollToBooking()) window.clearInterval(timer);
                                }}, 100);
                            }}
                        }})();
                    </script>
                    """,
                    height=0,
                )

            receipt_request_id = st.session_state.pop("scroll_to_receipt", None)
            if receipt_request_id is not None:
                components_html(
                    f"""
                    <script>
                        (() => {{
                            const requestId = "{receipt_request_id}";
                            let attempts = 0;
                            const scrollToReceipt = () => {{
                                const target = window.parent.document.getElementById("receipt-section");
                                attempts += 1;
                                if (target) {{
                                    target.scrollIntoView({{behavior: "smooth", block: "center"}});
                                    return true;
                                }}
                                return attempts >= 20;
                            }};
                            if (!scrollToReceipt()) {{
                                const timer = window.setInterval(() => {{
                                    if (scrollToReceipt()) window.clearInterval(timer);
                                }}, 100);
                            }}
                        }})();
                    </script>
                    """,
                    height=0,
                )
