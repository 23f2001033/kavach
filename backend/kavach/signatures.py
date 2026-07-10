"""Kavach scam-signature knowledge base + rule engine.

Each signature is a known scam *tell* — a phrase pattern strongly associated
with a manipulation tactic used in Indian phone scams (digital arrest, fake
KYC, UPI collect-request tricks, loan-app blackmail, etc). Signatures are pure
data (id / name / scam_type / severity / regex patterns / plain-language
explanation) so they can be tuned or extended without touching the engine.
`scam_type` values are taxonomy tags from data_pipeline/schema.py.

match(transcript) -> list[dict], each:
    {id, name, scam_type, severity, explanation, matches: [snippet, ...]}

Known hard case (v1, intentional, documented here rather than papered over):
a legitimate bank reminder that says "we never ask for your OTP" *mentions*
the word OTP as a safety warning, not a request. The OTP/PIN/CVV signature
below only fires on an imperative request verb (share/tell/read/give/send/
confirm/provide) sitting right next to the term, so "{bank} never asks for
your OTP" does NOT match — there's no request verb, only "asks for" framed as
a negative. This covers the common real phrasing. An acceptable v1 residual:
adversarial phrasing that mimics a safety warning while sneaking in a request
could still slip past regexes; resolving that fully needs the learned text
classifier (or later DistilBERT model), not more regex. The fusion layer's
job is to make sure this signature alone can't push a benign call to "high".
"""
import re

SEVERITY_LOW = 1
SEVERITY_MEDIUM = 2
SEVERITY_HIGH = 3

# Shared term group for OTP/PIN/CVV-like secrets, incl. "six digit code" style
# references some scammers use instead of saying "OTP" outright.
_SECRET_TERMS = (
    r"(?:otp|one[- ]time password|pin|cvv|card number|expiry date|"
    r"verification code|security code|"
    r"(?:\d{1,2}|two|three|four|five|six)[- ]?digit code)"
)

SIGNATURES = [
    {
        "id": "otp_pin_cvv_request",
        "name": "OTP / PIN / CVV request",
        "scam_type": "bank_fraud",
        "severity": SEVERITY_HIGH,
        "patterns": [
            rf"\b(?:share|tell me|read (?:me|out)|give me|send me|provide|confirm)\b[^.?!\n]{{0,25}}\b{_SECRET_TERMS}\b",
            rf"\bwhat(?:'s| is)\s+(?:the|your)\s+{_SECRET_TERMS}\b",
            r"\botp\b[^.?!\n]{0,20}\bread it\b",
        ],
        "explanation": "The caller asked you to share your OTP, PIN, or CVV — banks, police, and courts never ask for these on a call.",
    },
    {
        "id": "digital_arrest_or_warrant_threat",
        "name": '"Digital arrest" / warrant threat',
        "scam_type": "govt_impersonation",
        "severity": SEVERITY_HIGH,
        "patterns": [
            r"\bdigital arrest\b",
            r"\barrest warrant\b",
            r"\bfir (?:has been|is|has|being) registered\b",
            r"\bunder arrest\b",
            r"\bstay on (?:the )?(?:video )?call\b",
        ],
        "explanation": "The caller claimed police/court authority and threatened arrest to pressure you — there is no such thing as “digital arrest”; real police never arrest anyone over a phone call.",
    },
    {
        "id": "remote_access_app_request",
        "name": "Remote-access app request",
        "scam_type": "tech_support",
        "severity": SEVERITY_MEDIUM,
        "patterns": [
            r"\b(?:download|install|open)\b[^.?!\n]{0,25}\b(?:anydesk|teamviewer|quicksupport)\b",
            r"\b(?:anydesk|teamviewer|quicksupport)\b",
            r"\bremote access\b[^.?!\n]{0,20}\b(?:app|screen)\b",
        ],
        "explanation": "The caller asked you to install a remote-access app (AnyDesk/TeamViewer/QuickSupport) — this hands them full control of your phone or computer.",
    },
    {
        "id": "upi_collect_qr_trick",
        "name": "UPI collect-request / “scan to receive” trick",
        "scam_type": "refund_scam",
        "severity": SEVERITY_HIGH,
        "patterns": [
            r"\bcollect request\b",
            r"\bscan (?:this|the|my)?\s*qr code\b",
            r"\benter your (?:upi )?pin\b[^.?!\n]{0,30}\b(?:receive|refund|get)\b",
            r"\bfor receiving\b[^.?!\n]{0,20}\bpin\b",
            r"\breverse qr\b",
        ],
        "explanation": "You were asked to scan a QR code or enter your UPI PIN to “receive” money — entering a PIN or scanning a payment QR always sends money out, never in.",
    },
    {
        "id": "secrecy_demand",
        "name": "Secrecy / isolation demand",
        "scam_type": "unknown_scam",
        "severity": SEVERITY_MEDIUM,
        "patterns": [
            r"\bdo(?:n't| not) (?:tell|inform)\b[^.?!\n]{0,25}\b(?:anyone|family|bank|police)\b",
            r"\bnot even your family\b",
            r"\bkeep this (?:call|conversation)? ?confidential\b",
            r"\btelling anybody\b",
        ],
        "explanation": "The caller told you not to tell anyone (family, bank, police) — genuine officials never ask you to keep a call secret; this is an isolation tactic.",
    },
    {
        "id": "urgency_deadline",
        "name": "Artificial urgency / deadline",
        "scam_type": "unknown_scam",
        "severity": SEVERITY_LOW,
        "patterns": [
            r"\b(?:within|in the next)\s+(?:ten|10|five|5|one|1|two|2|sixty|60|thirty|30)\s+(?:minutes?|hours?|seconds?)\b",
            r"\bexpires? in\s+(?:sixty|60|thirty|30)\s+seconds\b",
            r"\blast warning\b",
            r"\btoday only\b",
            r"\bevery minute of delay\b",
        ],
        "explanation": "The caller set an artificial deadline (minutes/hours) to rush you into acting before you can think or verify independently.",
    },
    {
        "id": "prize_lottery_fee",
        "name": "Prize/lottery upfront fee",
        "scam_type": "prize_scam",
        "severity": SEVERITY_MEDIUM,
        "patterns": [
            r"\b(?:lottery|lucky draw|kbc|jackpot)\b[^.?!\n]{0,40}\b(?:won|winner)\b",
            r"\b(?:processing fee|government tax|clearance fee)\b[^.?!\n]{0,25}\b(?:prize|winner|winning|release)\b",
            r"\bwon\b[^.?!\n]{0,25}\b(?:lakh|crore)\b",
        ],
        "explanation": "You're told you won a prize or lottery you never entered, and must pay a “fee” or “tax” upfront to release it — genuine prizes never require an upfront payment.",
    },
    {
        "id": "kyc_expiry_threat",
        "name": "KYC-expiry account-block threat",
        "scam_type": "bank_fraud",
        "severity": SEVERITY_MEDIUM,
        "patterns": [
            r"\bkyc\b[^.?!\n]{0,20}\b(?:expired|expire|incomplete|update)\b",
            r"\baccount\b[^.?!\n]{0,25}\b(?:blocked|suspended|frozen)\b[^.?!\n]{0,25}\b(?:today|kyc|rbi)\b",
        ],
        "explanation": "The caller claimed your KYC has expired and your account will be blocked unless you act immediately — KYC updates happen at your branch or in your bank's app, never by giving details over a call.",
    },
    {
        "id": "safe_account_rbi_transfer",
        "name": "“Safe account” / fake RBI transfer",
        "scam_type": "govt_impersonation",
        "severity": SEVERITY_HIGH,
        "patterns": [
            r"\bsafe account\b",
            r"\b(?:rbi|reserve bank)\b[^.?!\n]{0,30}\b(?:transfer|audit|verification)\b",
            r"\bfunds? must be audited\b",
            r"\bsecure government account\b",
        ],
        "explanation": "You were asked to transfer your money to a “safe” or RBI-verification account — RBI and banks never ask you to move your own money to “protect” it.",
    },
    {
        "id": "loan_app_photo_threat",
        "name": "Loan-app photo/blackmail threat",
        "scam_type": "loan_scam",
        "severity": SEVERITY_HIGH,
        "patterns": [
            r"\b(?:morph(?:ed)?|edited|shameful)\b[^.?!\n]{0,20}\bphotos?\b",
            r"\bcontact list\b[^.?!\n]{0,20}\b(?:access|gallery)\b",
            r"\bsend (?:your|the)?\s*photos?\b[^.?!\n]{0,25}\b(?:contacts|family|everyone)\b",
        ],
        "explanation": "The caller threatened to send morphed or private photos to your contacts over a loan-app “default” — this is a known loan-app blackmail tactic; it is illegal and reportable.",
    },
    {
        "id": "army_marketplace_claim",
        "name": "Army/CRPF marketplace advance-payment claim",
        "scam_type": "marketplace_scam",
        "severity": SEVERITY_MEDIUM,
        "patterns": [
            r"\b(?:army|crpf|jawan|commanding officer)\b[^.?!\n]{0,40}\b(?:transfer|posted|buy|pay|qr)\b",
            r"\barmy (?:canteen|id)\b",
        ],
        "explanation": "The caller claims to be army/CRPF personnel buying your item and pushes an unusual QR or advance-payment scheme — a very common OLX/marketplace fraud pattern.",
    },
    {
        "id": "investment_guaranteed_return",
        "name": "Guaranteed high-return investment claim",
        "scam_type": "investment_scam",
        "severity": SEVERITY_MEDIUM,
        "patterns": [
            r"\bguaranteed\b[^.?!\n]{0,20}\b(?:return|profit|income)\b",
            r"\bdouble your money\b",
            r"\brisk[- ]?free\b[^.?!\n]{0,20}\b(?:profit|return)\b",
            r"\b\d{1,3}\s?%\s?(?:return|profit)\b[^.?!\n]{0,20}\b(?:month|monthly|week|guaranteed)\b",
        ],
        "explanation": "The caller promises guaranteed high returns with no risk — no legitimate investment can guarantee fixed high returns; this is a hallmark of investment fraud.",
    },
]

_COMPILED = [
    {**sig, "_compiled": [re.compile(p, re.IGNORECASE) for p in sig["patterns"]]}
    for sig in SIGNATURES
]

_MAX_SNIPPETS_PER_HIT = 3
_SNIPPET_PAD = 15


def match(transcript: str) -> list:
    """Run every signature's patterns over `transcript`. Returns a list of hit
    dicts (one per signature that matched at least once), each with a few
    matched-span snippets (with a little surrounding context) for the
    explanation / UI layer to quote back to the user."""
    if not transcript:
        return []
    hits = []
    for sig in _COMPILED:
        snippets = []
        for pattern in sig["_compiled"]:
            for m in pattern.finditer(transcript):
                start = max(0, m.start() - _SNIPPET_PAD)
                end = min(len(transcript), m.end() + _SNIPPET_PAD)
                snippet = transcript[start:end].strip()
                if snippet not in snippets:
                    snippets.append(snippet)
                if len(snippets) >= _MAX_SNIPPETS_PER_HIT:
                    break
            if len(snippets) >= _MAX_SNIPPETS_PER_HIT:
                break
        if snippets:
            hits.append({
                "id": sig["id"],
                "name": sig["name"],
                "scam_type": sig["scam_type"],
                "severity": sig["severity"],
                "explanation": sig["explanation"],
                "matches": snippets,
            })
    return hits
