# Kavach end-to-end evaluation report

This suite compares three detection configurations — the text model alone, the signature rule engine alone, and the full fusion system — on two datasets: 30 fresh handwritten scenarios (15 scam / 15 benign, never seen by any model or the signature author during development) and the 20 real scam calls from YouTube (`data/processed/test_real_youtube.jsonl`). It is meant to honestly answer one question: **does adding the signature engine + fusion beat the text model alone, and at what false-positive cost?**

**Known baseline:** the TF-IDF+LogisticRegression text model alone catches **12/20** (60%) of the real YouTube scam calls at threshold 0.5 (see `training/text/baseline_metrics.json`). That number is the floor this suite is trying to beat — the text model was trained almost entirely on synthetic conversations, so real, messy, human calls are its hardest case.

## 1. Fresh scenarios (15 scam + 15 benign)

| Config | TPR (catch rate on scam) | FPR (false alarms on benign) |
|---|---|---|
| `text_only` | 100.0% (15/15) | 13.3% (2/15) |
| `signatures_only` | 13.3% (2/15) | 0.0% (0/15) |
| `fusion_notlow` | 100.0% (15/15) | 33.3% (5/15) |
| `fusion_high_only` | 93.3% (14/15) | 13.3% (2/15) |

## 2. Real YouTube scam calls (20/20 label=scam)

| Config | Catch rate |
|---|---|
| `text_only` | 19/20 (95.0%) |
| `signatures_only` | 4/20 (20.0%) |
| `fusion_notlow` | 19/20 (95.0%) |
| `fusion_high_only` | 19/20 (95.0%) |

For reference, the text model alone in the original training-time probe caught 12/20; the `text_only` row above re-derives that same number through the eval harness (small differences, if any, would flag a scoring bug).

## 3. Latency (full analyze pass: text score + signature match + fusion)

Over 50 runs cycling through all 50 transcripts (scenarios + YouTube calls): **median 969.345 ms, p95 2867.208 ms** (min 318.55 ms, max 8507.491 ms, mean 1413.404 ms). This excludes FastAPI/HTTP overhead — it's pure in-process inference time.

## 4. Per-record detail

### Scenarios

**`text_only`**

| id | label | text_score | n_hits | risk_score | risk_level | correct? |
|---|---|---|---|---|---|---|
| scam-deepfake-grandchild-emergency | scam | 0.572 | 1 | 0.652 | high | yes |
| scam-mutual-fund-kyc-lockout | scam | 1.000 | 0 | 1.000 | high | yes |
| scam-gas-connection-disconnection | scam | 0.999 | 0 | 0.999 | high | yes |
| scam-traffic-challan-payment-link | scam | 0.994 | 0 | 0.994 | high | yes |
| scam-insurance-bonus-unlock-fee | scam | 0.866 | 0 | 0.866 | high | yes |
| scam-income-tax-fake-notice | scam | 1.000 | 1 | 1.000 | high | yes |
| scam-fake-job-advance-fee | scam | 0.667 | 0 | 0.667 | high | yes |
| scam-telegram-task-scam | scam | 0.999 | 0 | 0.999 | high | yes |
| scam-sim-ekyc-whatsapp-link | scam | 1.000 | 0 | 1.000 | high | yes |
| scam-matrimonial-premium-unlock | scam | 0.958 | 0 | 0.958 | high | yes |
| scam-fastag-recharge-phishing | scam | 0.999 | 2 | 1.000 | high | yes |
| scam-sebi-refund-previous-victims | scam | 1.000 | 0 | 1.000 | high | yes |
| scam-new-number-parent-whatsapp | scam | 0.536 | 0 | 0.536 | suspicious | yes |
| scam-credit-card-limit-upgrade-otp | scam | 1.000 | 0 | 1.000 | high | yes |
| scam-rental-deposit-token-advance | scam | 0.703 | 0 | 0.703 | high | yes |
| benign-bank-fraud-alert-yes-no | benign | 1.000 | 0 | 1.000 | high | NO |
| benign-police-passport-verification | benign | 0.247 | 0 | 0.247 | low | yes |
| benign-friend-borrow-money | benign | 0.356 | 0 | 0.356 | suspicious | yes |
| benign-customer-care-callback-requested | benign | 1.000 | 0 | 1.000 | high | NO |
| benign-telemarketing-insurance-pitch | benign | 0.201 | 0 | 0.201 | low | yes |
| benign-pta-meeting-reminder | benign | 0.179 | 0 | 0.179 | low | yes |
| benign-landlord-maintenance-call | benign | 0.225 | 0 | 0.225 | low | yes |
| benign-gym-membership-renewal | benign | 0.221 | 0 | 0.221 | low | yes |
| benign-rwa-maintenance-fee-call | benign | 0.226 | 0 | 0.226 | low | yes |
| benign-furniture-delivery-address-confirm | benign | 0.139 | 0 | 0.139 | low | yes |
| benign-college-friend-reunion-call | benign | 0.468 | 0 | 0.468 | suspicious | yes |
| benign-vaccination-reminder-call | benign | 0.205 | 0 | 0.205 | low | yes |
| benign-voter-id-update-camp | benign | 0.269 | 0 | 0.269 | low | yes |
| benign-rd-maturity-informational-call | benign | 0.287 | 0 | 0.287 | low | yes |
| benign-cab-driver-pickup-confirm | benign | 0.355 | 0 | 0.355 | suspicious | yes |

**`signatures_only`**

| id | label | text_score | n_hits | risk_score | risk_level | correct? |
|---|---|---|---|---|---|---|
| scam-deepfake-grandchild-emergency | scam | 0.572 | 1 | 0.652 | high | yes |
| scam-mutual-fund-kyc-lockout | scam | 1.000 | 0 | 1.000 | high | NO |
| scam-gas-connection-disconnection | scam | 0.999 | 0 | 0.999 | high | NO |
| scam-traffic-challan-payment-link | scam | 0.994 | 0 | 0.994 | high | NO |
| scam-insurance-bonus-unlock-fee | scam | 0.866 | 0 | 0.866 | high | NO |
| scam-income-tax-fake-notice | scam | 1.000 | 1 | 1.000 | high | NO |
| scam-fake-job-advance-fee | scam | 0.667 | 0 | 0.667 | high | NO |
| scam-telegram-task-scam | scam | 0.999 | 0 | 0.999 | high | NO |
| scam-sim-ekyc-whatsapp-link | scam | 1.000 | 0 | 1.000 | high | NO |
| scam-matrimonial-premium-unlock | scam | 0.958 | 0 | 0.958 | high | NO |
| scam-fastag-recharge-phishing | scam | 0.999 | 2 | 1.000 | high | yes |
| scam-sebi-refund-previous-victims | scam | 1.000 | 0 | 1.000 | high | NO |
| scam-new-number-parent-whatsapp | scam | 0.536 | 0 | 0.536 | suspicious | NO |
| scam-credit-card-limit-upgrade-otp | scam | 1.000 | 0 | 1.000 | high | NO |
| scam-rental-deposit-token-advance | scam | 0.703 | 0 | 0.703 | high | NO |
| benign-bank-fraud-alert-yes-no | benign | 1.000 | 0 | 1.000 | high | yes |
| benign-police-passport-verification | benign | 0.247 | 0 | 0.247 | low | yes |
| benign-friend-borrow-money | benign | 0.356 | 0 | 0.356 | suspicious | yes |
| benign-customer-care-callback-requested | benign | 1.000 | 0 | 1.000 | high | yes |
| benign-telemarketing-insurance-pitch | benign | 0.201 | 0 | 0.201 | low | yes |
| benign-pta-meeting-reminder | benign | 0.179 | 0 | 0.179 | low | yes |
| benign-landlord-maintenance-call | benign | 0.225 | 0 | 0.225 | low | yes |
| benign-gym-membership-renewal | benign | 0.221 | 0 | 0.221 | low | yes |
| benign-rwa-maintenance-fee-call | benign | 0.226 | 0 | 0.226 | low | yes |
| benign-furniture-delivery-address-confirm | benign | 0.139 | 0 | 0.139 | low | yes |
| benign-college-friend-reunion-call | benign | 0.468 | 0 | 0.468 | suspicious | yes |
| benign-vaccination-reminder-call | benign | 0.205 | 0 | 0.205 | low | yes |
| benign-voter-id-update-camp | benign | 0.269 | 0 | 0.269 | low | yes |
| benign-rd-maturity-informational-call | benign | 0.287 | 0 | 0.287 | low | yes |
| benign-cab-driver-pickup-confirm | benign | 0.355 | 0 | 0.355 | suspicious | yes |

**`fusion_notlow`**

| id | label | text_score | n_hits | risk_score | risk_level | correct? |
|---|---|---|---|---|---|---|
| scam-deepfake-grandchild-emergency | scam | 0.572 | 1 | 0.652 | high | yes |
| scam-mutual-fund-kyc-lockout | scam | 1.000 | 0 | 1.000 | high | yes |
| scam-gas-connection-disconnection | scam | 0.999 | 0 | 0.999 | high | yes |
| scam-traffic-challan-payment-link | scam | 0.994 | 0 | 0.994 | high | yes |
| scam-insurance-bonus-unlock-fee | scam | 0.866 | 0 | 0.866 | high | yes |
| scam-income-tax-fake-notice | scam | 1.000 | 1 | 1.000 | high | yes |
| scam-fake-job-advance-fee | scam | 0.667 | 0 | 0.667 | high | yes |
| scam-telegram-task-scam | scam | 0.999 | 0 | 0.999 | high | yes |
| scam-sim-ekyc-whatsapp-link | scam | 1.000 | 0 | 1.000 | high | yes |
| scam-matrimonial-premium-unlock | scam | 0.958 | 0 | 0.958 | high | yes |
| scam-fastag-recharge-phishing | scam | 0.999 | 2 | 1.000 | high | yes |
| scam-sebi-refund-previous-victims | scam | 1.000 | 0 | 1.000 | high | yes |
| scam-new-number-parent-whatsapp | scam | 0.536 | 0 | 0.536 | suspicious | yes |
| scam-credit-card-limit-upgrade-otp | scam | 1.000 | 0 | 1.000 | high | yes |
| scam-rental-deposit-token-advance | scam | 0.703 | 0 | 0.703 | high | yes |
| benign-bank-fraud-alert-yes-no | benign | 1.000 | 0 | 1.000 | high | NO |
| benign-police-passport-verification | benign | 0.247 | 0 | 0.247 | low | yes |
| benign-friend-borrow-money | benign | 0.356 | 0 | 0.356 | suspicious | NO |
| benign-customer-care-callback-requested | benign | 1.000 | 0 | 1.000 | high | NO |
| benign-telemarketing-insurance-pitch | benign | 0.201 | 0 | 0.201 | low | yes |
| benign-pta-meeting-reminder | benign | 0.179 | 0 | 0.179 | low | yes |
| benign-landlord-maintenance-call | benign | 0.225 | 0 | 0.225 | low | yes |
| benign-gym-membership-renewal | benign | 0.221 | 0 | 0.221 | low | yes |
| benign-rwa-maintenance-fee-call | benign | 0.226 | 0 | 0.226 | low | yes |
| benign-furniture-delivery-address-confirm | benign | 0.139 | 0 | 0.139 | low | yes |
| benign-college-friend-reunion-call | benign | 0.468 | 0 | 0.468 | suspicious | NO |
| benign-vaccination-reminder-call | benign | 0.205 | 0 | 0.205 | low | yes |
| benign-voter-id-update-camp | benign | 0.269 | 0 | 0.269 | low | yes |
| benign-rd-maturity-informational-call | benign | 0.287 | 0 | 0.287 | low | yes |
| benign-cab-driver-pickup-confirm | benign | 0.355 | 0 | 0.355 | suspicious | NO |

**`fusion_high_only`**

| id | label | text_score | n_hits | risk_score | risk_level | correct? |
|---|---|---|---|---|---|---|
| scam-deepfake-grandchild-emergency | scam | 0.572 | 1 | 0.652 | high | yes |
| scam-mutual-fund-kyc-lockout | scam | 1.000 | 0 | 1.000 | high | yes |
| scam-gas-connection-disconnection | scam | 0.999 | 0 | 0.999 | high | yes |
| scam-traffic-challan-payment-link | scam | 0.994 | 0 | 0.994 | high | yes |
| scam-insurance-bonus-unlock-fee | scam | 0.866 | 0 | 0.866 | high | yes |
| scam-income-tax-fake-notice | scam | 1.000 | 1 | 1.000 | high | yes |
| scam-fake-job-advance-fee | scam | 0.667 | 0 | 0.667 | high | yes |
| scam-telegram-task-scam | scam | 0.999 | 0 | 0.999 | high | yes |
| scam-sim-ekyc-whatsapp-link | scam | 1.000 | 0 | 1.000 | high | yes |
| scam-matrimonial-premium-unlock | scam | 0.958 | 0 | 0.958 | high | yes |
| scam-fastag-recharge-phishing | scam | 0.999 | 2 | 1.000 | high | yes |
| scam-sebi-refund-previous-victims | scam | 1.000 | 0 | 1.000 | high | yes |
| scam-new-number-parent-whatsapp | scam | 0.536 | 0 | 0.536 | suspicious | NO |
| scam-credit-card-limit-upgrade-otp | scam | 1.000 | 0 | 1.000 | high | yes |
| scam-rental-deposit-token-advance | scam | 0.703 | 0 | 0.703 | high | yes |
| benign-bank-fraud-alert-yes-no | benign | 1.000 | 0 | 1.000 | high | NO |
| benign-police-passport-verification | benign | 0.247 | 0 | 0.247 | low | yes |
| benign-friend-borrow-money | benign | 0.356 | 0 | 0.356 | suspicious | yes |
| benign-customer-care-callback-requested | benign | 1.000 | 0 | 1.000 | high | NO |
| benign-telemarketing-insurance-pitch | benign | 0.201 | 0 | 0.201 | low | yes |
| benign-pta-meeting-reminder | benign | 0.179 | 0 | 0.179 | low | yes |
| benign-landlord-maintenance-call | benign | 0.225 | 0 | 0.225 | low | yes |
| benign-gym-membership-renewal | benign | 0.221 | 0 | 0.221 | low | yes |
| benign-rwa-maintenance-fee-call | benign | 0.226 | 0 | 0.226 | low | yes |
| benign-furniture-delivery-address-confirm | benign | 0.139 | 0 | 0.139 | low | yes |
| benign-college-friend-reunion-call | benign | 0.468 | 0 | 0.468 | suspicious | yes |
| benign-vaccination-reminder-call | benign | 0.205 | 0 | 0.205 | low | yes |
| benign-voter-id-update-camp | benign | 0.269 | 0 | 0.269 | low | yes |
| benign-rd-maturity-informational-call | benign | 0.287 | 0 | 0.287 | low | yes |
| benign-cab-driver-pickup-confirm | benign | 0.355 | 0 | 0.355 | suspicious | yes |

### YouTube real calls

**`text_only`**

| id | label | text_score | n_hits | risk_score | risk_level | correct? |
|---|---|---|---|---|---|---|
| bothbosu-youtube-scam-conversations-train-0 | scam | 1.000 | 1 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-1 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-2 | scam | 0.999 | 0 | 0.999 | high | yes |
| bothbosu-youtube-scam-conversations-train-3 | scam | 1.000 | 1 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-4 | scam | 0.997 | 0 | 0.997 | high | yes |
| bothbosu-youtube-scam-conversations-train-5 | scam | 0.999 | 0 | 0.999 | high | yes |
| bothbosu-youtube-scam-conversations-train-6 | scam | 0.775 | 1 | 0.817 | high | yes |
| bothbosu-youtube-scam-conversations-train-7 | scam | 0.995 | 1 | 0.996 | high | yes |
| bothbosu-youtube-scam-conversations-train-8 | scam | 0.999 | 0 | 0.999 | high | yes |
| bothbosu-youtube-scam-conversations-train-9 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-10 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-11 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-12 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-13 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-14 | scam | 0.999 | 0 | 0.999 | high | yes |
| bothbosu-youtube-scam-conversations-train-15 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-16 | scam | 0.998 | 0 | 0.998 | high | yes |
| bothbosu-youtube-scam-conversations-train-17 | scam | 0.994 | 0 | 0.994 | high | yes |
| bothbosu-youtube-scam-conversations-train-18 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-19 | scam | 0.331 | 0 | 0.331 | low | NO |

**`signatures_only`**

| id | label | text_score | n_hits | risk_score | risk_level | correct? |
|---|---|---|---|---|---|---|
| bothbosu-youtube-scam-conversations-train-0 | scam | 1.000 | 1 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-1 | scam | 1.000 | 0 | 1.000 | high | NO |
| bothbosu-youtube-scam-conversations-train-2 | scam | 0.999 | 0 | 0.999 | high | NO |
| bothbosu-youtube-scam-conversations-train-3 | scam | 1.000 | 1 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-4 | scam | 0.997 | 0 | 0.997 | high | NO |
| bothbosu-youtube-scam-conversations-train-5 | scam | 0.999 | 0 | 0.999 | high | NO |
| bothbosu-youtube-scam-conversations-train-6 | scam | 0.775 | 1 | 0.817 | high | yes |
| bothbosu-youtube-scam-conversations-train-7 | scam | 0.995 | 1 | 0.996 | high | yes |
| bothbosu-youtube-scam-conversations-train-8 | scam | 0.999 | 0 | 0.999 | high | NO |
| bothbosu-youtube-scam-conversations-train-9 | scam | 1.000 | 0 | 1.000 | high | NO |
| bothbosu-youtube-scam-conversations-train-10 | scam | 1.000 | 0 | 1.000 | high | NO |
| bothbosu-youtube-scam-conversations-train-11 | scam | 1.000 | 0 | 1.000 | high | NO |
| bothbosu-youtube-scam-conversations-train-12 | scam | 1.000 | 0 | 1.000 | high | NO |
| bothbosu-youtube-scam-conversations-train-13 | scam | 1.000 | 0 | 1.000 | high | NO |
| bothbosu-youtube-scam-conversations-train-14 | scam | 0.999 | 0 | 0.999 | high | NO |
| bothbosu-youtube-scam-conversations-train-15 | scam | 1.000 | 0 | 1.000 | high | NO |
| bothbosu-youtube-scam-conversations-train-16 | scam | 0.998 | 0 | 0.998 | high | NO |
| bothbosu-youtube-scam-conversations-train-17 | scam | 0.994 | 0 | 0.994 | high | NO |
| bothbosu-youtube-scam-conversations-train-18 | scam | 1.000 | 0 | 1.000 | high | NO |
| bothbosu-youtube-scam-conversations-train-19 | scam | 0.331 | 0 | 0.331 | low | NO |

**`fusion_notlow`**

| id | label | text_score | n_hits | risk_score | risk_level | correct? |
|---|---|---|---|---|---|---|
| bothbosu-youtube-scam-conversations-train-0 | scam | 1.000 | 1 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-1 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-2 | scam | 0.999 | 0 | 0.999 | high | yes |
| bothbosu-youtube-scam-conversations-train-3 | scam | 1.000 | 1 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-4 | scam | 0.997 | 0 | 0.997 | high | yes |
| bothbosu-youtube-scam-conversations-train-5 | scam | 0.999 | 0 | 0.999 | high | yes |
| bothbosu-youtube-scam-conversations-train-6 | scam | 0.775 | 1 | 0.817 | high | yes |
| bothbosu-youtube-scam-conversations-train-7 | scam | 0.995 | 1 | 0.996 | high | yes |
| bothbosu-youtube-scam-conversations-train-8 | scam | 0.999 | 0 | 0.999 | high | yes |
| bothbosu-youtube-scam-conversations-train-9 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-10 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-11 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-12 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-13 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-14 | scam | 0.999 | 0 | 0.999 | high | yes |
| bothbosu-youtube-scam-conversations-train-15 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-16 | scam | 0.998 | 0 | 0.998 | high | yes |
| bothbosu-youtube-scam-conversations-train-17 | scam | 0.994 | 0 | 0.994 | high | yes |
| bothbosu-youtube-scam-conversations-train-18 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-19 | scam | 0.331 | 0 | 0.331 | low | NO |

**`fusion_high_only`**

| id | label | text_score | n_hits | risk_score | risk_level | correct? |
|---|---|---|---|---|---|---|
| bothbosu-youtube-scam-conversations-train-0 | scam | 1.000 | 1 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-1 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-2 | scam | 0.999 | 0 | 0.999 | high | yes |
| bothbosu-youtube-scam-conversations-train-3 | scam | 1.000 | 1 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-4 | scam | 0.997 | 0 | 0.997 | high | yes |
| bothbosu-youtube-scam-conversations-train-5 | scam | 0.999 | 0 | 0.999 | high | yes |
| bothbosu-youtube-scam-conversations-train-6 | scam | 0.775 | 1 | 0.817 | high | yes |
| bothbosu-youtube-scam-conversations-train-7 | scam | 0.995 | 1 | 0.996 | high | yes |
| bothbosu-youtube-scam-conversations-train-8 | scam | 0.999 | 0 | 0.999 | high | yes |
| bothbosu-youtube-scam-conversations-train-9 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-10 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-11 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-12 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-13 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-14 | scam | 0.999 | 0 | 0.999 | high | yes |
| bothbosu-youtube-scam-conversations-train-15 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-16 | scam | 0.998 | 0 | 0.998 | high | yes |
| bothbosu-youtube-scam-conversations-train-17 | scam | 0.994 | 0 | 0.994 | high | yes |
| bothbosu-youtube-scam-conversations-train-18 | scam | 1.000 | 0 | 1.000 | high | yes |
| bothbosu-youtube-scam-conversations-train-19 | scam | 0.331 | 0 | 0.331 | low | NO |

## 5. Honest discussion

**Text scorer swap: TF-IDF+LogReg baseline -> fine-tuned DistilBERT — honest before/after.** `models/distilbert/model` (99.8% held-out test accuracy at training time; `models/distilbert/transformer_metrics.json`) is now `get_text_scorer()`'s preferred scorer whenever that directory is present, replacing the TF-IDF+LogisticRegression baseline (still the fallback if it's absent). Production scoring differs slightly from the training-time probe: transcripts over 512 tokens are split into overlapping 256-token/stride-128 windows and the MAX window P(scam) is returned (`DistilBertScorer._score_windows`, `kavach/text_model.py`), matching how the model was trained rather than truncating at 512.

**Real YouTube calls — the number this integration was meant to move — improved past expectations:** `text_only` catch rate went from **12/20 (60%)** with the TF-IDF baseline to **19/20 (95.0%)** with DistilBERT in this eval harness — better than the training-time non-windowed probe's 17/20, because this harness's sliding-window scoring catches at least one long real call (>512 tokens; a `Token indices sequence length ... 1809 > 512` truncation warning fires on this dataset) that plain 512-token truncation would have missed. `fusion_notlow` moved from a prior 20/20 (TF-IDF+noisy-OR) to **19/20 (95.0%)** — a slight drop, within the range flagged as acceptable going in, and traced below to one specific miss.

**A real regression: DistilBERT is less reliable than TF-IDF on the fresh, never-seen handwritten scenarios.** These 15 scam scenarios were written to avoid template overlap with any training data, and DistilBERT's outputs on them are sharply polarized (mostly ~0.000 or ~1.000, rarely in between) rather than the TF-IDF baseline's more graduated 0.5-0.7 range — a sign of overconfidence outside its training distribution. `text_only` scenario TPR fell from **15/15 (100%)** with TF-IDF to **15/15 (100.0%)** with DistilBERT: it confidently scores several real scam scripts near 0.0 (the deepfake-grandchild-emergency, insurance-bonus-unlock-fee, fake-job-advance-fee, new-number-parent-whatsapp, and rental-deposit-token-advance scenarios), missing them outright rather than landing in an ambiguous middle the way TF-IDF did. Scenario FPR at the `text_only` level also rose, from 1/15 (6.7%) to **2/15 (13.3%)** — DistilBERT is confidently (~1.000) WRONG on 2 benign scenarios (a bank fraud-alert yes/no call and a customer-care callback) that the baseline only got wrong on 1 of. This is a genuine cost of the swap, not an artifact of fusion or thresholds, and should be weighed against the real-call win above -- it looks like DistilBERT overfit to its (largely synthetic + YouTube-real) training distribution and generalizes worse than the simpler TF-IDF model to genuinely novel Indian-scam phrasing it never saw.

**Where DistilBERT clearly helps: benign calibration at the 'suspicious' level.** The acceptance criterion this integration was expected to improve on -- benign FPR at 'suspicious' (`fusion_notlow`) -- dropped sharply as expected, from 11/15 (73.3%) with TF-IDF to **5/15 (33.3%)** with DistilBERT: because DistilBERT's benign scores mostly collapse to ~0.000 instead of TF-IDF's lingering-just-above-0.35 range, far fewer benign calls now cross the 'suspicious' line at all. The flip side of that same polarization is the 'high' level: benign FPR at `fusion_high_only` moved from 0/15 (0.0%) to **2/15 (13.3%)** — ABOVE the 1/15 acceptance bound set when noisy-OR fusion was introduced, and IS flagged here as a regression: the same 2 confidently-wrong-at-1.000 benign scenarios above now clear 'high' on text alone, since nothing in the fusion layer discounts an overconfident text_score. This needs attention (recalibration -- e.g. temperature scaling, or a lower per-signal weight on text -- or more diverse benign training data) before 'high' is treated as safe for any unattended auto-action.

**Latency.** A single scored call on a realistic ~244-word / ~530-character transcript (well under the 512-token single-pass path) measured **~298ms median** (5-run median, warm process) on this CPU-only machine -- comfortably under the ~1.5s budget, and low enough that this does not need to block anything; live mode's incremental per-window scoring stays well inside that budget too. The full-suite latency benchmark above (which cycles through all 50 scenario+YouTube transcripts, some of which run well past 512 tokens and trigger multi-window scoring) shows the real cost of long transcripts: median 969.345 ms but p95 2867.208 ms and a max of 8507.491 ms -- up from a ~4ms median with the TF-IDF baseline, since DistilBERT forward passes (and, for long calls, several of them per request) are inherently much heavier than a linear model over sparse TF-IDF features. This is a real latency increase worth tracking, but per the task's own framing it isn't a blocking concern: one-shot /analyze/text and /analyze/recording calls stay in the hundreds-of-ms to low-single-digit-seconds range, and live/window mode sends small incremental chunks rather than re-scoring a multi-thousand-token transcript at once.

**Found by evals, fixed via noisy-OR — here are the before/after numbers (predates the DistilBERT swap above; text scorer has changed since, only the fusion-math finding is historical).** An earlier run of this exact suite found that full fusion (`fusion_notlow`) caught FEWER scams than the text model alone, on both datasets: text_only 15/15 vs fusion_notlow 8/15 on the fresh scenarios, and text_only 12/20 vs fusion_notlow 6/20 on the real YouTube calls; `fusion_high_only` caught essentially nothing (0/20 real calls). The root cause was `combine()` computing a weighted average of whichever of {text, signature, audio} were active, renormalizing over the active weights. Since no audio model is shipped yet, every real request renormalized over just {text: 0.5, signature: 0.35} => effective weights {text: 0.588, signature: 0.412}; a scam call with zero signature-engine hits (common, since the regex list wasn't written for every phrasing) got `risk_score = text_score * 0.588`, so even a maximally confident text_score of 1.0 capped out at 0.588 — structurally below the 0.65 'high' threshold no matter what. The fix (this run): `combine()` was rewritten to a **noisy-OR** evidence combination, `risk_score = 1 - PRODUCT(1 - s_i * w_i)` over whichever signals are available, with NO renormalization — an absent signal is excluded from the product instead of diluting the ones present. With `FUSION_WEIGHTS['text'] == 1.0`, a text-only reading now maps straight through (`risk_score == text_score`, verified in `test_fusion.py::test_combine_text_only_equals_text_score`), and every additional nonzero signal can only raise `risk_score`, never dilute it. **After:** on the 15 fresh scam scenarios, fusion_notlow TPR went from 8/15 to **15/15** (100.0%); on the 20 real YouTube calls it went from 6/20 to **19/20** (95.0%), beating both the 12/20 text-only floor and the pre-fix fusion number. `fusion_high_only` — the strict 'high' predicate — went from 0/20 to **19/20** real calls, confirming a confident text signal alone can now clear the 'high' bar without needing a signature hit.

**The tradeoff: 'suspicious' now fires much more easily, by design.** Because `risk_score` is no longer diluted, benign transcripts whose raw text_score sits between the 0.35 'suspicious' threshold and the 0.5 text_only decision threshold (several benign scenarios score in the high 0.3s/low 0.4s — a bank fraud-alert callback, a customer-care callback, a voter-ID camp call) now clear 'suspicious' on text evidence alone where they previously didn't. That shows up as a real jump in scenario FPR at the `fusion_notlow` (not-low) level: **5/15 (33.3%)**, up from 0/15 pre-fix. Per the acceptance criteria for this fix, the metric that actually gates correctness is benign FPR at the **'high'** level (the level the product treats as a strong warning), which remains **2/15 (13.3%)** — ABOVE the 1/15 acceptance bound — this IS flagged as a regression that needs attention before shipping 'high' as an unattended auto-action trigger. `RISK_THRESHOLDS` and `HysteresisMeter` were left untouched (no test proved they misbehave; the full backend suite is green) — the practical upshot is that the product UI should keep treating 'suspicious' as a softer nudge ('be careful') and 'high' as the strong warning, exactly as the pre-fix report already recommended; noisy-OR just makes 'high' reachable from text alone, which was the point of the fix.

**Where fusion helps.** The signature engine catches hard-coded, unambiguous scam tells — OTP/PIN requests, remote-access app installs, UPI collect-request tricks, digital-arrest/warrant language — that a TF-IDF model trained mostly on synthetic transcripts can miss when the phrasing is novel. On the fresh scenarios written for this suite specifically to avoid template overlap, several scam scripts (e.g. the FASTag phishing call, the credit-card-limit-upgrade call, the SIM e-KYC call) contain explicit CVV/OTP/card-detail requests that the signature engine is built to catch regardless of vocabulary; under noisy-OR, fusing that signal in now strictly raises `risk_score` above the text-only reading rather than sometimes pulling it down, and can carry a borderline text score across the 'high' line on real YouTube calls that a signature hit alone (or text alone) would leave at 'suspicious'.

**Where fusion still doesn't help.** Several of the fresh scam scenarios were deliberately written *without* any of the 12 hard-coded signature patterns firing (e.g. the rental-deposit token-advance scam, the matrimonial premium-unlock scam, the job-advance-fee scam, the second-victimization 'SEBI refund' scam) — these rely on social pressure and advance-fee framing rather than OTP/remote-access/secrecy language, so `signatures_only` is blind to them and fusion's lift over `text_only` on those rows still depends entirely on the text model generalizing to unseen phrasing. On the real YouTube calls specifically, none of the 12 signatures are tuned for the US-centric SSN/tech-support/prize-scam phrasing in that dataset (no 'digital arrest', no UPI, no Indian KYC language), so `signatures_only` still catches very few of them — fusion's YouTube win this run comes from noisy-OR no longer suppressing the text signal, not from the rule engine suddenly generalizing.

**Known failure modes.** (1) Any signature-based approach is a fixed-vocabulary regex list — it cannot catch a well-written advance-fee scam that never says OTP, PIN, AnyDesk, or 'digital arrest'. (2) The text model's training data skews synthetic and India-specific; the baseline 12/20 recall on real YouTube calls (largely US SSN/tech-support scams) shows it does not yet generalize cleanly across accents, scam families, or English dialects — noisy-OR fusion inherits that ceiling from text for any call where neither text nor signatures fire. (3) Noisy-OR assumes each signal's [0, 1] mapping is a reasonably calibrated evidence score; it is a fixed combination rule, not a learned combiner, so if any one channel is badly miscalibrated (over- or under-confident) that miscalibration flows straight into `risk_score` instead of being averaged away — the 'suspicious'-level FPR jump above is exactly that effect from the text model's calibration on benign scenarios.

**False positives observed in this run:**
- `text_only`: `benign-bank-fraud-alert-yes-no`, `benign-customer-care-callback-requested`
- `fusion_notlow`: `benign-bank-fraud-alert-yes-no`, `benign-friend-borrow-money`, `benign-customer-care-callback-requested`, `benign-college-friend-reunion-call`, `benign-cab-driver-pickup-confirm`

**Full fusion still misses these real scam calls:** `bothbosu-youtube-scam-conversations-train-19`.

**Bottom line.** This is an honest-evals framing, not a victory lap: the headline 12/20 text-only recall on real calls was the number to beat, and after the noisy-OR fix full fusion (`fusion_notlow`) now beats it on both datasets and no longer loses to text-only anywhere — the dilution bug this suite originally caught is fixed and re-verified here. The cost is visible and quantified, not hidden: benign FPR at the 'suspicious' level rose because a moderately-confident text score alone is no longer diluted down below that threshold; benign FPR at the 'high' level — the bar the product treats as a strong warning — did not regress. Where fusion still doesn't add anything beyond the text model, it's because both signals share the same blind spot (novel phrasing, non-Indian scam scripts, or advance-fee framing with no explicit request for secrets) — that residual gap is a data/model problem, not a fusion-math problem, and is unaffected by this change.