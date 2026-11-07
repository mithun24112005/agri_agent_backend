"""
Structured Government Schemes Reference Module (Phase 8)
Curated database of verified national agricultural schemes and subsidies in India.
Provides authoritative eligibility, benefits, and verified official government portal links.
"""

from typing import List, Dict, Any, Optional

GOVERNMENT_SCHEMES: List[Dict[str, Any]] = [
    {
        "id": "pm_kisan",
        "name": "Pradhan Mantri Kisan Samman Nidhi (PM-KISAN)",
        "nodal_ministry": "Ministry of Agriculture & Farmers Welfare, Govt of India",
        "category": "Direct Income Support",
        "benefits": "₹6,000 per year transferred directly to bank accounts in 3 equal installments of ₹2,000 every four months.",
        "eligibility": "All landholding farmer families with cultivable landholding in their names. Excludes institutional landholders, high-income taxpayers, and constitutional post holders.",
        "how_to_apply": "Self-registration on the official PM-KISAN portal or through local Common Service Centers (CSC) / State Agriculture Nodal Officers. Requires Aadhaar, land records (Khata/Khasra), and bank details.",
        "official_portal": "https://pmkisan.gov.in"
    },
    {
        "id": "pmfby",
        "name": "Pradhan Mantri Fasal Bima Yojana (PMFBY)",
        "nodal_ministry": "Ministry of Agriculture & Farmers Welfare, Govt of India",
        "category": "Crop Insurance & Risk Mitigation",
        "benefits": "Comprehensive risk insurance covering pre-sowing losses, mid-season adversity, standing crop loss, and post-harvest localized calamities. Maximum farmer premium: 2.0% for Kharif food crops, 1.5% for Rabi crops, and 5.0% for commercial/horticultural crops; remaining premium subsidized by government.",
        "eligibility": "All farmers including sharecroppers and tenant farmers growing notified crops in notified areas. Voluntary for all farmers.",
        "how_to_apply": "Enroll through national crop insurance portal, banks/PACS during crop loan disbursement, or CSC centers before the seasonal cut-off date (typically July 31 for Kharif, Dec 31 for Rabi).",
        "official_portal": "https://pmfby.gov.in"
    },
    {
        "id": "pmksy_pdmc",
        "name": "PM Krishi Sinchayee Yojana — Per Drop More Crop (PDMC)",
        "nodal_ministry": "Department of Agriculture & Farmers Welfare",
        "category": "Micro-Irrigation Subsidy",
        "benefits": "Subsidy on Drip and Sprinkler irrigation systems: up to 55% for Small & Marginal farmers, and up to 45% for other farmers.",
        "eligibility": "Farmers holding cultivable land with an assured water source (well, borewell, canal, farm pond).",
        "how_to_apply": "Apply through State Department of Agriculture / Horticulture online portals (e.g. Mahadbt in Maharashtra, e-Uparjan, etc.) with land records, Aadhaar, and quotation from authorized micro-irrigation vendors.",
        "official_portal": "https://pmksy.gov.in"
    },
    {
        "id": "soil_health_card",
        "name": "Soil Health Card Scheme (SHC)",
        "nodal_ministry": "Ministry of Agriculture & Farmers Welfare",
        "category": "Soil Testing & Nutrient Management",
        "benefits": "Free or nominal-cost comprehensive soil health report card measuring 12 parameters: N, P, K, S, Zn, Fe, Cu, Mn, Bo, pH, EC, and Organic Carbon, alongside crop-wise fertilizer guidance.",
        "eligibility": "All landholding farmers in India.",
        "how_to_apply": "Soil samples collected cyclically by state agriculture department staff. Farmers can also submit soil samples directly to district Soil Testing Laboratories (STL) or Krishi Vigyan Kendras (KVK).",
        "official_portal": "https://soilhealth.dac.gov.in"
    },
    {
        "id": "kcc",
        "name": "Kisan Credit Card (KCC)",
        "nodal_ministry": "Department of Financial Services & NABARD",
        "category": "Institutional Credit & Working Capital",
        "benefits": "Short-term crop production credit up to ₹3 Lakh at an effective interest rate of 4% per annum (7% baseline rate with 3% prompt repayment incentive). Collateral-free loan up to ₹1.60 Lakh.",
        "eligibility": "Individual/joint farmers, tenant farmers, oral lessees, sharecroppers, and Self Help Groups (SHGs).",
        "how_to_apply": "Submit single-page KCC application form at any commercial bank, Regional Rural Bank (RRB), or Primary Agricultural Credit Society (PACS) with land title and crop declaration.",
        "official_portal": "https://www.myscheme.gov.in/schemes/kcc"
    },
    {
        "id": "pm_kusum",
        "name": "PM-KUSUM (Pradhan Mantri Kisan Urja Suraksha evam Utthaan Mahabhiyan)",
        "nodal_ministry": "Ministry of New and Renewable Energy (MNRE)",
        "category": "Solar Pump Subsidies & Renewable Energy",
        "benefits": "Component B: 60% subsidy (30% Central + 30% State) on setting up standalone off-grid solar agricultural pumps up to 7.5 HP; farmer contributes only 10%–40% depending on state policy.",
        "eligibility": "Individual farmers, water user associations, and farmer producer organizations (FPOs) having cultivable land without grid connection.",
        "how_to_apply": "Register online on state renewable energy development agency portals (e.g., MEDA, UPNEDA, HAREDA, etc.). Beware of fraudulent lookalike websites.",
        "official_portal": "https://pmkusum.mnre.gov.in"
    },
    {
        "id": "smam",
        "name": "Sub-Mission on Agricultural Mechanization (SMAM)",
        "nodal_ministry": "Ministry of Agriculture & Farmers Welfare",
        "category": "Farm Machinery & Implement Subsidies",
        "benefits": "40% to 50% financial assistance/subsidy on procurement of tractors, power tillers, rotavators, laser land levelers, and establishment of Custom Hiring Centers (CHCs).",
        "eligibility": "Small, marginal, SC/ST, and women farmers receive higher subsidy preference.",
        "how_to_apply": "Apply through the centralized Direct Benefit Transfer (DBT) in Agriculture Mechanization portal.",
        "official_portal": "https://agrimachinery.nic.in"
    }
]


def search_schemes(query: str) -> List[Dict[str, Any]]:
    """Search schemes matching query terms in title, benefits, or category."""
    tokens = set(query.lower().split())
    matches = []

    for scheme in GOVERNMENT_SCHEMES:
        searchable_text = f"{scheme['name']} {scheme['category']} {scheme['benefits']} {scheme['eligibility']}".lower()
        score = sum(1 for t in tokens if t in searchable_text)
        if score > 0 or not tokens:
            matches.append((score, scheme))

    matches.sort(key=lambda x: x[0], reverse=True)
    return [m[1] for m in matches]


def format_scheme_markdown(scheme: Dict[str, Any]) -> str:
    """Format a single scheme into rich Markdown."""
    return (
        f"### 🏛️ {scheme['name']}\n"
        f"- **Category:** {scheme['category']}\n"
        f"- **Nodal Ministry:** {scheme['nodal_ministry']}\n"
        f"- **Financial Benefits:** {scheme['benefits']}\n"
        f"- **Eligibility:** {scheme['eligibility']}\n"
        f"- **How to Apply:** {scheme['how_to_apply']}\n"
        f"- **Official Portal:** [{scheme['official_portal']}]({scheme['official_portal']})"
    )


def format_schemes_summary(schemes: List[Dict[str, Any]]) -> str:
    """Format multiple schemes into a cohesive Markdown advisory."""
    if not schemes:
        return "No specific government schemes matched your query. Consider checking the unified portal: [myScheme](https://www.myscheme.gov.in)."

    parts = ["### 🌾 Verified Government Agricultural Schemes & Subsidies\n"]
    for s in schemes[:3]:
        parts.append(format_scheme_markdown(s))
        parts.append("\n---\n")

    parts.append("> ⚠️ **Official Advice:** Always verify schemes through official `.gov.in` or `.nic.in` portals. Never share bank OTPs or pay application fees on unofficial third-party websites.")
    return "\n".join(parts)

