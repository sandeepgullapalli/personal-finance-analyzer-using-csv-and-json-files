"""
Categorization and Merchant Cleaning Module
Matches transaction descriptions against rules and patterns to auto-assign categories
and extract clean merchant names.
"""

import re
from typing import List, Dict, Any, Tuple

DEFAULT_CATEGORY_RULES: List[Dict[str, Any]] = [
    # Income
    {
        "category": "Income",
        "patterns": [
            r"payroll", r"salary", r"direct dep", r"dir dep", r"deposit",
            r"ach credit", r"employer", r"interest payment", r"dividend",
            r"refund", r"cashback", r"freelance", r"wire in",
            r"neft cr", r"imps cr", r"client payment", r"project payment",
            r"ctc", r"appraisal", r"bonus", r"incentive"
        ]
    },
    # Housing & Rent
    {
        "category": "Housing & Rent",
        "patterns": [
            r"rent", r"mortgage", r"apartment", r"property mgmt", r"landlord",
            r"hoa fee", r"lease", r"real estate", r"housing", r"flat rent",
            r"maintenance charge", r"society charge"
        ]
    },
    # Groceries
    {
        "category": "Groceries",
        "patterns": [
            r"dmart", r"d-mart", r"bigbasket", r"big basket", r"reliance fresh",
            r"reliance smart", r"jiomart", r"nature.s basket", r"more supermarket",
            r"easyday", r"star bazaar", r"grocery", r"supermarket", r"hypermarket",
            r"walmart", r"costco", r"trader joe", r"whole foods", r"safeway",
            r"instacart", r"blinkit", r"swiggy instamart", r"zepto", r"dunzo"
        ]
    },
    # Dining & Takeout
    {
        "category": "Dining & Cafes",
        "patterns": [
            r"zomato", r"swiggy", r"starbucks", r"mcdonald", r"kfc", r"pizza hut",
            r"dominos", r"burger king", r"subway", r"dunkin", r"third wave coffee",
            r"blue tokai", r"cafe coffee day", r"ccd", r"barista", r"chai point",
            r"restaurant", r"cafe", r"bistro", r"dhaba", r"hotel food",
            r"doordash", r"uber eats", r"chipotle", r"bakery"
        ]
    },
    # Utilities & Bills
    {
        "category": "Utilities & Bills",
        "patterns": [
            r"bescom", r"msedcl", r"tata power", r"electricity", r"electric bill",
            r"bwssb", r"water bill", r"gas bill", r"mahanagar gas", r"indraprastha gas",
            r"act broadband", r"jio fiber", r"airtel broadband", r"bsnl broadband",
            r"airtel", r"jio", r"vi ", r"vodafone", r"idea", r"bsnl", r"tata docomo",
            r"comcast", r"xfinity", r"internet", r"utility"
        ]
    },
    # Transportation & Fuel
    {
        "category": "Transportation",
        "patterns": [
            r"indian oil", r"hp petrol", r"bharat petroleum", r"shell", r"fuel",
            r"petrol pump", r"ola ", r"uber(?! eats)", r"rapido", r"meru",
            r"irctc", r"indian railway", r"metro card", r"bus pass", r"fastag",
            r"toll", r"parking", r"auto repair", r"car service", r"maruti",
            r"lyft", r"tesla supercharg", r"chevron", r"exxon"
        ]
    },
    # Entertainment & Subscriptions
    {
        "category": "Entertainment & Subscriptions",
        "patterns": [
            r"netflix", r"spotify", r"hotstar", r"disney\+", r"amazon prime",
            r"youtube prem", r"apple", r"zee5", r"sonyliv", r"voot",
            r"bookmyshow", r"pvr cinema", r"inox", r"cinepolis",
            r"patreon", r"audible", r"steam", r"playstation", r"xbox", r"nintendo",
            r"ticketmaster", r"hbo", r"max\.com", r"hulu"
        ]
    },
    # Shopping & Retail
    {
        "category": "Shopping & Retail",
        "patterns": [
            r"amazon", r"flipkart", r"myntra", r"ajio", r"meesho", r"snapdeal",
            r"nykaa", r"purplle", r"decathlon", r"puma", r"nike", r"adidas",
            r"zara", r"h&m", r"uniqlo", r"westside", r"pantaloons",
            r"croma", r"reliance digital", r"vijay sales", r"best buy",
            r"ikea", r"home depot", r"apple store", r"ebay", r"etsy"
        ]
    },
    # Healthcare & Wellness
    {
        "category": "Healthcare & Fitness",
        "patterns": [
            r"apollo pharmacy", r"medplus", r"1mg", r"netmeds", r"pharmeasy",
            r"apollo hospital", r"fortis", r"manipal hospital", r"aiims",
            r"doctor", r"dentist", r"clinic", r"hospital", r"lab test",
            r"thyrocare", r"dr lal pathlabs", r"cult fit", r"gym", r"fitness",
            r"crossfit", r"yoga", r"healthify", r"cvs", r"walgreens"
        ]
    },
    # Financial & Investments
    {
        "category": "Investments & Finance",
        "patterns": [
            r"zerodha", r"groww", r"upstox", r"angel broking", r"hdfc securities",
            r"icicidirect", r"sbi mutual fund", r"nps contribution",
            r"ppf deposit", r"fd booking", r"rd installment",
            r"fidelity", r"vanguard", r"schwab", r"robinhood", r"coinbase", r"crypto"
        ]
    },
    # Bank Charges & Fees
    {
        "category": "Bank Fees & Charges",
        "patterns": [
            r"atm fee", r"service fee", r"overdraft", r"monthly maintenance",
            r"late fee", r"foreign transaction fee", r"wire fee", r"gst charge",
            r"bank charge", r"sms charge", r"locker fee"
        ]
    }
]

# Common prefixes and suffixes to strip from merchant names
CLEANUP_REGEXES = [
    r"^TST\*\s*",             # Toast POS prefix
    r"^SQ\*\s*",              # Square POS prefix
    r"^SP\*\s*",              # Shopify prefix
    r"^PAYPAL\s*\*\s*",       # PayPal prefix
    r"^AMZN\s*Mktp\s*(US\*)?",# Amazon marketplace
    r"^CHECKCARD\s*",
    r"^DEBIT\s*CARD\s*PURCHASE\s*",
    r"\s*#\d+",               # Store numbers like #1234
    r"\s*\d{3,}-\d{3,}",      # Phone numbers
    r"\s+[A-Z]{2}\s+\d{5}$",  # State & Zip at end e.g. "CA 94103"
    r"\.COM(\b|$)"            # .com domains
]


def clean_merchant_name(raw: str) -> str:
    """Extract a cleaner, human-friendly merchant name."""
    if not raw:
        return "Unknown"
    
    text = raw.strip()
    for reg in CLEANUP_REGEXES:
        text = re.sub(reg, "", text, flags=re.IGNORECASE).strip()

    # If all caps, convert to Title Case for better presentation
    if text.isupper():
        text = text.title()

    # Shorten excessively long description strings
    if len(text) > 35:
        text = text[:32] + "..."

    return text or raw.strip()


def categorize_transaction(desc: str, amount: float, current_category: str = None) -> Tuple[str, str]:
    """
    Returns (category, clean_merchant).
    If current_category is already provided and valid, it is respected.
    """
    clean_merchant = clean_merchant_name(desc)

    if current_category and current_category.strip() and current_category.strip().lower() not in ('uncategorized', 'other', 'none'):
        return current_category.strip(), clean_merchant

    # Check if clearly income by amount and sign
    if amount > 0:
        desc_lower = desc.lower()
        for pat in DEFAULT_CATEGORY_RULES[0]["patterns"]:
            if re.search(pat, desc_lower):
                return "Income", clean_merchant
        # If amount is positive and not matched, categorize as Income/Inflow
        return "Income", clean_merchant

    desc_lower = desc.lower()
    for rule in DEFAULT_CATEGORY_RULES:
        if rule["category"] == "Income":
            continue
        for pat in rule["patterns"]:
            if re.search(pat, desc_lower):
                return rule["category"], clean_merchant

    return "Uncategorized", clean_merchant


def apply_categories(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Applies categorization rules and merchant cleaning to all transactions."""
    categorized = []
    for tx in transactions:
        t = dict(tx)
        cat, clean_merch = categorize_transaction(
            t["description"],
            t["amount"],
            t.get("category")
        )
        t["category"] = cat
        t["merchant"] = clean_merch
        categorized.append(t)
    return categorized
