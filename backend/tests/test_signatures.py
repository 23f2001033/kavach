"""Signature-engine tests: obvious scam lines should be flagged with the right
signature ids; benign lines (incl. the OTP-safety-warning hard case) should
stay quiet or at worst produce a low-severity hit that doesn't dominate risk.
"""
from kavach.signatures import match


def _ids(hits):
    return {h["id"] for h in hits}


# ---------------------------------------------------------------- scam lines
def test_flags_digital_arrest_and_otp_request():
    transcript = (
        "Caller: This is Inspector Rathore from Mumbai Police cyber cell. "
        "You are now under digital arrest. Do not disconnect and do not tell "
        "your family. Share your bank account OTP so we can verify your funds "
        "within ten minutes, otherwise a warrant will be issued."
    )
    hits = match(transcript)
    ids = _ids(hits)
    assert "digital_arrest_or_warrant_threat" in ids
    assert "otp_pin_cvv_request" in ids
    assert "secrecy_demand" in ids
    assert "urgency_deadline" in ids
    for h in hits:
        assert h["matches"], f"{h['id']} hit with no matched snippet"


def test_flags_remote_access_app_request():
    transcript = "Caller: Please download AnyDesk right now so I can fix your computer remotely."
    ids = _ids(match(transcript))
    assert "remote_access_app_request" in ids


def test_flags_upi_collect_request_trick():
    transcript = (
        "Caller: I am sending you a collect request for the refund. Just scan the QR code "
        "and enter your UPI pin to receive the money back."
    )
    ids = _ids(match(transcript))
    assert "upi_collect_qr_trick" in ids


def test_flags_kyc_expiry_and_safe_account():
    transcript = (
        "Caller: Your KYC has expired and your account will be blocked today by RBI order. "
        "To keep your funds safe, transfer everything to this secure government account for RBI audit."
    )
    ids = _ids(match(transcript))
    assert "kyc_expiry_threat" in ids
    assert "safe_account_rbi_transfer" in ids


def test_flags_prize_lottery_fee():
    transcript = (
        "Caller: Congratulations, your number has won 25 lakh rupees in the KBC lucky draw! "
        "Just pay the government tax processing fee to release your winner prize."
    )
    ids = _ids(match(transcript))
    assert "prize_lottery_fee" in ids


def test_flags_loan_app_photo_threat():
    transcript = (
        "Caller: We have access to your contact list and gallery. If you don't pay today, "
        "we will send morphed photos to your family and everyone in your contacts."
    )
    ids = _ids(match(transcript))
    assert "loan_app_photo_threat" in ids


def test_flags_army_marketplace_claim():
    transcript = (
        "Caller: I am a CRPF jawan posted in Delhi, I want to buy your sofa set. "
        "I will pay through the army canteen QR, please scan and confirm."
    )
    ids = _ids(match(transcript))
    assert "army_marketplace_claim" in ids


def test_flags_investment_guaranteed_return():
    transcript = (
        "Caller: Our AI trading system gives a guaranteed 30 percent monthly return, completely risk-free. "
        "Many members have doubled their money."
    )
    ids = _ids(match(transcript))
    assert "investment_guaranteed_return" in ids


# -------------------------------------------------------------- benign lines
def test_benign_bank_reminder_with_otp_safety_warning_does_not_flag_otp():
    """Known hard case: a legitimate bank reminder MENTIONS OTP, but only in
    the "we never ask for it" safety-warning sense, not as a request. The
    OTP signature requires an imperative request verb next to the term, so
    this must NOT fire the otp_pin_cvv_request signature."""
    transcript = (
        "Caller: This is a reminder that your credit card payment is due on the 15th. "
        "And a security reminder: your bank never asks for your OTP, PIN, or password on calls. "
        "If anyone does, please report it. Receiver: Good to know, thank you."
    )
    ids = _ids(match(transcript))
    assert "otp_pin_cvv_request" not in ids


def test_benign_delivery_call_mostly_quiet():
    transcript = (
        "Caller: Good afternoon, Blue Dart calling. Your parcel is out for delivery today "
        "between 2 PM and evening. It's cash on delivery, 1,499 rupees, you can also pay by "
        "UPI at the door on the company QR. Receiver: I'll pay by UPI when you arrive."
    )
    hits = match(transcript)
    # No high-severity scam signatures (digital arrest / OTP request / safe-account / loan
    # blackmail / prize fee) should fire on an ordinary delivery call.
    high_severity_ids = {
        "digital_arrest_or_warrant_threat",
        "otp_pin_cvv_request",
        "safe_account_rbi_transfer",
        "loan_app_photo_threat",
    }
    assert high_severity_ids.isdisjoint(_ids(hits))


def test_benign_family_call_no_hits():
    transcript = (
        "Caller: Hello! It's your cousin from Pune. Long time! How is everyone at home? "
        "Receiver: All good here. How have you been?"
    )
    assert match(transcript) == []


def test_match_empty_transcript_returns_empty_list():
    assert match("") == []
    assert match(None) == []


def test_benign_share_pin_location_does_not_flag_otp():
    """'pin' alone is ambiguous in Indian English: a map pin ('share a pin
    location') or a postal PIN code, not a security PIN. Found via evals/ as
    a real false positive on a benign furniture-delivery call."""
    transcript = (
        "Caller: The gate is easier to find from the back lane, I can share a pin "
        "location if that helps. Receiver: That would be great, please share it."
    )
    ids = _ids(match(transcript))
    assert "otp_pin_cvv_request" not in ids


def test_benign_pin_code_does_not_flag_otp():
    transcript = "Receiver: Sure, my PIN code is 400001, that's the postal code for this area."
    ids = _ids(match(transcript))
    assert "otp_pin_cvv_request" not in ids


def test_benign_do_not_need_to_share_otp_does_not_flag_request():
    """Found via evals/ as a real false positive: a genuine bank fraud-alert
    call explicitly reassures the customer they do NOT need to share their
    OTP/PIN — same safety-warning intent as the 'never asks for your OTP'
    hard case above, just phrased with 'share' instead of 'asks for'."""
    transcript = (
        "Caller: You do not need to share your card number, PIN, or any OTP "
        "with me for this — I just needed your yes or no."
    )
    ids = _ids(match(transcript))
    assert "otp_pin_cvv_request" not in ids


def test_scam_share_otp_request_still_flags():
    """Regression guard: the negation lookbehind must not swallow the
    original, unambiguous scam case."""
    transcript = "Caller: Please share your OTP and PIN right now so I can verify your account."
    ids = _ids(match(transcript))
    assert "otp_pin_cvv_request" in ids
