"""Unified record schema for the Kavach conversation corpus.

Every source (open datasets + our India-specific synthesis) is normalized into:

    {
      "id":        str,   # stable unique id: "<source-slug>-<index>"
      "source":    str,   # dataset id or "kavach-india-synth"
      "text":      str,   # full dialogue, speakers normalized to "Caller:" / "Receiver:"
      "label":     int,   # 1 = scam, 0 = legitimate
      "scam_type": str,   # unified taxonomy tag (see TAXONOMY), "none" for legit calls
      "origin":    str,   # "synthetic" | "real"
    }
"""

# Unified scam/benign call taxonomy. Source-specific type tags map into these.
TAXONOMY = {
    # scam families
    "govt_impersonation",   # SSN / police / "digital arrest" / court warrants
    "tech_support",         # fake computer/support scams
    "refund_scam",          # fake refunds, remote-access refund traps, UPI refund
    "prize_scam",           # lottery / rewards / KBC
    "bank_fraud",           # fake bank calls, OTP/KYC phishing
    "courier_scam",         # fake customs/parcel scams
    "investment_scam",      # trading apps, crypto doubling
    "loan_scam",            # predatory loan app / recovery threats
    "marketplace_scam",     # OLX-style advance payment fraud
    "unknown_scam",         # scam label with no source type info (e.g. Scammer-Conversation)
    # benign families
    "delivery", "insurance", "telemarketing", "wrong_number",
    "appointment", "banking_legit", "utility_legit", "personal", "none",
}

# BothBosu source tags -> (unified tag). Labels come from the data itself.
BOTHBOSU_TYPE_MAP = {
    "ssn": "govt_impersonation",
    "support": "tech_support",
    "refund": "refund_scam",
    "reward": "prize_scam",
    "delivery": "delivery",
    "insurance": "insurance",
    "telemarketing": "telemarketing",
    "wrong": "wrong_number",
    "appointment": "appointment",
}

CALLER_ALIASES = {"caller", "suspect", "person a", "scammer", "agent"}
RECEIVER_ALIASES = {"receiver", "innocent", "person b", "victim", "user"}
