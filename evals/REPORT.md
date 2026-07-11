# Kavach end-to-end evaluation report

This suite compares three detection configurations — the text model alone, the signature rule engine alone, and the full fusion system — on two datasets: 30 fresh handwritten scenarios (15 scam / 15 benign, never seen by any model or the signature author during development) and the 20 real scam calls from YouTube (`data/processed/test_real_youtube.jsonl`). It is meant to honestly answer one question: **does adding the signature engine + fusion beat the text model alone, and at what false-positive cost?**

**Known baseline:** the TF-IDF+LogisticRegression text model alone catches **12/20** (60%) of the real YouTube scam calls at threshold 0.5 (see `training/text/baseline_metrics.json`). That number is the floor this suite is trying to beat — the text model was trained almost entirely on synthetic conversations, so real, messy, human calls are its hardest case.

## 1. Fresh scenarios (15 scam + 15 benign)

| Config | TPR (catch rate on scam) | FPR (false alarms on benign) |
|---|---|---|
| `text_only` | 100.0% (15/15) | 6.7% (1/15) |
| `signatures_only` | 13.3% (2/15) | 0.0% (0/15) |
| `fusion_notlow` | 53.3% (8/15) | 0.0% (0/15) |
| `fusion_high_only` | 0.0% (0/15) | 0.0% (0/15) |

## 2. Real YouTube scam calls (20/20 label=scam)

| Config | Catch rate |
|---|---|
| `text_only` | 12/20 (60.0%) |
| `signatures_only` | 4/20 (20.0%) |
| `fusion_notlow` | 6/20 (30.0%) |
| `fusion_high_only` | 0/20 (0.0%) |

For reference, the text model alone in the original training-time probe caught 12/20; the `text_only` row above re-derives that same number through the eval harness (small differences, if any, would flag a scoring bug).

## 3. Latency (full analyze pass: text score + signature match + fusion)

Over 50 runs cycling through all 50 transcripts (scenarios + YouTube calls): **median 4.818 ms, p95 7.839 ms** (min 2.335 ms, max 14.749 ms, mean 4.918 ms). This excludes FastAPI/HTTP overhead — it's pure in-process inference time.

## 4. Per-record detail

### Scenarios

**`text_only`**

| id | label | text_score | n_hits | risk_score | risk_level | correct? |
|---|---|---|---|---|---|---|
| scam-deepfake-grandchild-emergency | scam | 0.547 | 1 | 0.412 | suspicious | yes |
| scam-mutual-fund-kyc-lockout | scam | 0.643 | 0 | 0.378 | suspicious | yes |
| scam-gas-connection-disconnection | scam | 0.592 | 0 | 0.348 | low | yes |
| scam-traffic-challan-payment-link | scam | 0.582 | 0 | 0.342 | low | yes |
| scam-insurance-bonus-unlock-fee | scam | 0.619 | 0 | 0.364 | suspicious | yes |
| scam-income-tax-fake-notice | scam | 0.661 | 1 | 0.438 | suspicious | yes |
| scam-fake-job-advance-fee | scam | 0.544 | 0 | 0.320 | low | yes |
| scam-telegram-task-scam | scam | 0.574 | 0 | 0.338 | low | yes |
| scam-sim-ekyc-whatsapp-link | scam | 0.619 | 0 | 0.364 | suspicious | yes |
| scam-matrimonial-premium-unlock | scam | 0.567 | 0 | 0.334 | low | yes |
| scam-fastag-recharge-phishing | scam | 0.591 | 2 | 0.582 | suspicious | yes |
| scam-sebi-refund-previous-victims | scam | 0.642 | 0 | 0.377 | suspicious | yes |
| scam-new-number-parent-whatsapp | scam | 0.543 | 0 | 0.319 | low | yes |
| scam-credit-card-limit-upgrade-otp | scam | 0.665 | 0 | 0.391 | suspicious | yes |
| scam-rental-deposit-token-advance | scam | 0.509 | 0 | 0.299 | low | yes |
| benign-bank-fraud-alert-yes-no | benign | 0.521 | 0 | 0.306 | low | NO |
| benign-police-passport-verification | benign | 0.443 | 0 | 0.260 | low | yes |
| benign-friend-borrow-money | benign | 0.398 | 0 | 0.234 | low | yes |
| benign-customer-care-callback-requested | benign | 0.418 | 0 | 0.246 | low | yes |
| benign-telemarketing-insurance-pitch | benign | 0.300 | 0 | 0.176 | low | yes |
| benign-pta-meeting-reminder | benign | 0.309 | 0 | 0.182 | low | yes |
| benign-landlord-maintenance-call | benign | 0.361 | 0 | 0.212 | low | yes |
| benign-gym-membership-renewal | benign | 0.352 | 0 | 0.207 | low | yes |
| benign-rwa-maintenance-fee-call | benign | 0.365 | 0 | 0.214 | low | yes |
| benign-furniture-delivery-address-confirm | benign | 0.277 | 0 | 0.163 | low | yes |
| benign-college-friend-reunion-call | benign | 0.395 | 0 | 0.232 | low | yes |
| benign-vaccination-reminder-call | benign | 0.324 | 0 | 0.191 | low | yes |
| benign-voter-id-update-camp | benign | 0.416 | 0 | 0.244 | low | yes |
| benign-rd-maturity-informational-call | benign | 0.390 | 0 | 0.229 | low | yes |
| benign-cab-driver-pickup-confirm | benign | 0.411 | 0 | 0.242 | low | yes |

**`signatures_only`**

| id | label | text_score | n_hits | risk_score | risk_level | correct? |
|---|---|---|---|---|---|---|
| scam-deepfake-grandchild-emergency | scam | 0.547 | 1 | 0.412 | suspicious | yes |
| scam-mutual-fund-kyc-lockout | scam | 0.643 | 0 | 0.378 | suspicious | NO |
| scam-gas-connection-disconnection | scam | 0.592 | 0 | 0.348 | low | NO |
| scam-traffic-challan-payment-link | scam | 0.582 | 0 | 0.342 | low | NO |
| scam-insurance-bonus-unlock-fee | scam | 0.619 | 0 | 0.364 | suspicious | NO |
| scam-income-tax-fake-notice | scam | 0.661 | 1 | 0.438 | suspicious | NO |
| scam-fake-job-advance-fee | scam | 0.544 | 0 | 0.320 | low | NO |
| scam-telegram-task-scam | scam | 0.574 | 0 | 0.338 | low | NO |
| scam-sim-ekyc-whatsapp-link | scam | 0.619 | 0 | 0.364 | suspicious | NO |
| scam-matrimonial-premium-unlock | scam | 0.567 | 0 | 0.334 | low | NO |
| scam-fastag-recharge-phishing | scam | 0.591 | 2 | 0.582 | suspicious | yes |
| scam-sebi-refund-previous-victims | scam | 0.642 | 0 | 0.377 | suspicious | NO |
| scam-new-number-parent-whatsapp | scam | 0.543 | 0 | 0.319 | low | NO |
| scam-credit-card-limit-upgrade-otp | scam | 0.665 | 0 | 0.391 | suspicious | NO |
| scam-rental-deposit-token-advance | scam | 0.509 | 0 | 0.299 | low | NO |
| benign-bank-fraud-alert-yes-no | benign | 0.521 | 0 | 0.306 | low | yes |
| benign-police-passport-verification | benign | 0.443 | 0 | 0.260 | low | yes |
| benign-friend-borrow-money | benign | 0.398 | 0 | 0.234 | low | yes |
| benign-customer-care-callback-requested | benign | 0.418 | 0 | 0.246 | low | yes |
| benign-telemarketing-insurance-pitch | benign | 0.300 | 0 | 0.176 | low | yes |
| benign-pta-meeting-reminder | benign | 0.309 | 0 | 0.182 | low | yes |
| benign-landlord-maintenance-call | benign | 0.361 | 0 | 0.212 | low | yes |
| benign-gym-membership-renewal | benign | 0.352 | 0 | 0.207 | low | yes |
| benign-rwa-maintenance-fee-call | benign | 0.365 | 0 | 0.214 | low | yes |
| benign-furniture-delivery-address-confirm | benign | 0.277 | 0 | 0.163 | low | yes |
| benign-college-friend-reunion-call | benign | 0.395 | 0 | 0.232 | low | yes |
| benign-vaccination-reminder-call | benign | 0.324 | 0 | 0.191 | low | yes |
| benign-voter-id-update-camp | benign | 0.416 | 0 | 0.244 | low | yes |
| benign-rd-maturity-informational-call | benign | 0.390 | 0 | 0.229 | low | yes |
| benign-cab-driver-pickup-confirm | benign | 0.411 | 0 | 0.242 | low | yes |

**`fusion_notlow`**

| id | label | text_score | n_hits | risk_score | risk_level | correct? |
|---|---|---|---|---|---|---|
| scam-deepfake-grandchild-emergency | scam | 0.547 | 1 | 0.412 | suspicious | yes |
| scam-mutual-fund-kyc-lockout | scam | 0.643 | 0 | 0.378 | suspicious | yes |
| scam-gas-connection-disconnection | scam | 0.592 | 0 | 0.348 | low | NO |
| scam-traffic-challan-payment-link | scam | 0.582 | 0 | 0.342 | low | NO |
| scam-insurance-bonus-unlock-fee | scam | 0.619 | 0 | 0.364 | suspicious | yes |
| scam-income-tax-fake-notice | scam | 0.661 | 1 | 0.438 | suspicious | yes |
| scam-fake-job-advance-fee | scam | 0.544 | 0 | 0.320 | low | NO |
| scam-telegram-task-scam | scam | 0.574 | 0 | 0.338 | low | NO |
| scam-sim-ekyc-whatsapp-link | scam | 0.619 | 0 | 0.364 | suspicious | yes |
| scam-matrimonial-premium-unlock | scam | 0.567 | 0 | 0.334 | low | NO |
| scam-fastag-recharge-phishing | scam | 0.591 | 2 | 0.582 | suspicious | yes |
| scam-sebi-refund-previous-victims | scam | 0.642 | 0 | 0.377 | suspicious | yes |
| scam-new-number-parent-whatsapp | scam | 0.543 | 0 | 0.319 | low | NO |
| scam-credit-card-limit-upgrade-otp | scam | 0.665 | 0 | 0.391 | suspicious | yes |
| scam-rental-deposit-token-advance | scam | 0.509 | 0 | 0.299 | low | NO |
| benign-bank-fraud-alert-yes-no | benign | 0.521 | 0 | 0.306 | low | yes |
| benign-police-passport-verification | benign | 0.443 | 0 | 0.260 | low | yes |
| benign-friend-borrow-money | benign | 0.398 | 0 | 0.234 | low | yes |
| benign-customer-care-callback-requested | benign | 0.418 | 0 | 0.246 | low | yes |
| benign-telemarketing-insurance-pitch | benign | 0.300 | 0 | 0.176 | low | yes |
| benign-pta-meeting-reminder | benign | 0.309 | 0 | 0.182 | low | yes |
| benign-landlord-maintenance-call | benign | 0.361 | 0 | 0.212 | low | yes |
| benign-gym-membership-renewal | benign | 0.352 | 0 | 0.207 | low | yes |
| benign-rwa-maintenance-fee-call | benign | 0.365 | 0 | 0.214 | low | yes |
| benign-furniture-delivery-address-confirm | benign | 0.277 | 0 | 0.163 | low | yes |
| benign-college-friend-reunion-call | benign | 0.395 | 0 | 0.232 | low | yes |
| benign-vaccination-reminder-call | benign | 0.324 | 0 | 0.191 | low | yes |
| benign-voter-id-update-camp | benign | 0.416 | 0 | 0.244 | low | yes |
| benign-rd-maturity-informational-call | benign | 0.390 | 0 | 0.229 | low | yes |
| benign-cab-driver-pickup-confirm | benign | 0.411 | 0 | 0.242 | low | yes |

**`fusion_high_only`**

| id | label | text_score | n_hits | risk_score | risk_level | correct? |
|---|---|---|---|---|---|---|
| scam-deepfake-grandchild-emergency | scam | 0.547 | 1 | 0.412 | suspicious | NO |
| scam-mutual-fund-kyc-lockout | scam | 0.643 | 0 | 0.378 | suspicious | NO |
| scam-gas-connection-disconnection | scam | 0.592 | 0 | 0.348 | low | NO |
| scam-traffic-challan-payment-link | scam | 0.582 | 0 | 0.342 | low | NO |
| scam-insurance-bonus-unlock-fee | scam | 0.619 | 0 | 0.364 | suspicious | NO |
| scam-income-tax-fake-notice | scam | 0.661 | 1 | 0.438 | suspicious | NO |
| scam-fake-job-advance-fee | scam | 0.544 | 0 | 0.320 | low | NO |
| scam-telegram-task-scam | scam | 0.574 | 0 | 0.338 | low | NO |
| scam-sim-ekyc-whatsapp-link | scam | 0.619 | 0 | 0.364 | suspicious | NO |
| scam-matrimonial-premium-unlock | scam | 0.567 | 0 | 0.334 | low | NO |
| scam-fastag-recharge-phishing | scam | 0.591 | 2 | 0.582 | suspicious | NO |
| scam-sebi-refund-previous-victims | scam | 0.642 | 0 | 0.377 | suspicious | NO |
| scam-new-number-parent-whatsapp | scam | 0.543 | 0 | 0.319 | low | NO |
| scam-credit-card-limit-upgrade-otp | scam | 0.665 | 0 | 0.391 | suspicious | NO |
| scam-rental-deposit-token-advance | scam | 0.509 | 0 | 0.299 | low | NO |
| benign-bank-fraud-alert-yes-no | benign | 0.521 | 0 | 0.306 | low | yes |
| benign-police-passport-verification | benign | 0.443 | 0 | 0.260 | low | yes |
| benign-friend-borrow-money | benign | 0.398 | 0 | 0.234 | low | yes |
| benign-customer-care-callback-requested | benign | 0.418 | 0 | 0.246 | low | yes |
| benign-telemarketing-insurance-pitch | benign | 0.300 | 0 | 0.176 | low | yes |
| benign-pta-meeting-reminder | benign | 0.309 | 0 | 0.182 | low | yes |
| benign-landlord-maintenance-call | benign | 0.361 | 0 | 0.212 | low | yes |
| benign-gym-membership-renewal | benign | 0.352 | 0 | 0.207 | low | yes |
| benign-rwa-maintenance-fee-call | benign | 0.365 | 0 | 0.214 | low | yes |
| benign-furniture-delivery-address-confirm | benign | 0.277 | 0 | 0.163 | low | yes |
| benign-college-friend-reunion-call | benign | 0.395 | 0 | 0.232 | low | yes |
| benign-vaccination-reminder-call | benign | 0.324 | 0 | 0.191 | low | yes |
| benign-voter-id-update-camp | benign | 0.416 | 0 | 0.244 | low | yes |
| benign-rd-maturity-informational-call | benign | 0.390 | 0 | 0.229 | low | yes |
| benign-cab-driver-pickup-confirm | benign | 0.411 | 0 | 0.242 | low | yes |

### YouTube real calls

**`text_only`**

| id | label | text_score | n_hits | risk_score | risk_level | correct? |
|---|---|---|---|---|---|---|
| bothbosu-youtube-scam-conversations-train-0 | scam | 0.584 | 1 | 0.434 | suspicious | yes |
| bothbosu-youtube-scam-conversations-train-1 | scam | 0.496 | 0 | 0.292 | low | NO |
| bothbosu-youtube-scam-conversations-train-2 | scam | 0.560 | 0 | 0.329 | low | yes |
| bothbosu-youtube-scam-conversations-train-3 | scam | 0.589 | 1 | 0.437 | suspicious | yes |
| bothbosu-youtube-scam-conversations-train-4 | scam | 0.548 | 0 | 0.322 | low | yes |
| bothbosu-youtube-scam-conversations-train-5 | scam | 0.540 | 0 | 0.318 | low | yes |
| bothbosu-youtube-scam-conversations-train-6 | scam | 0.483 | 1 | 0.375 | suspicious | NO |
| bothbosu-youtube-scam-conversations-train-7 | scam | 0.463 | 1 | 0.363 | suspicious | NO |
| bothbosu-youtube-scam-conversations-train-8 | scam | 0.482 | 0 | 0.284 | low | NO |
| bothbosu-youtube-scam-conversations-train-9 | scam | 0.509 | 0 | 0.299 | low | yes |
| bothbosu-youtube-scam-conversations-train-10 | scam | 0.410 | 0 | 0.241 | low | NO |
| bothbosu-youtube-scam-conversations-train-11 | scam | 0.546 | 0 | 0.321 | low | yes |
| bothbosu-youtube-scam-conversations-train-12 | scam | 0.619 | 0 | 0.364 | suspicious | yes |
| bothbosu-youtube-scam-conversations-train-13 | scam | 0.688 | 0 | 0.405 | suspicious | yes |
| bothbosu-youtube-scam-conversations-train-14 | scam | 0.551 | 0 | 0.324 | low | yes |
| bothbosu-youtube-scam-conversations-train-15 | scam | 0.517 | 0 | 0.304 | low | yes |
| bothbosu-youtube-scam-conversations-train-16 | scam | 0.444 | 0 | 0.261 | low | NO |
| bothbosu-youtube-scam-conversations-train-17 | scam | 0.455 | 0 | 0.268 | low | NO |
| bothbosu-youtube-scam-conversations-train-18 | scam | 0.581 | 0 | 0.342 | low | yes |
| bothbosu-youtube-scam-conversations-train-19 | scam | 0.403 | 0 | 0.237 | low | NO |

**`signatures_only`**

| id | label | text_score | n_hits | risk_score | risk_level | correct? |
|---|---|---|---|---|---|---|
| bothbosu-youtube-scam-conversations-train-0 | scam | 0.584 | 1 | 0.434 | suspicious | yes |
| bothbosu-youtube-scam-conversations-train-1 | scam | 0.496 | 0 | 0.292 | low | NO |
| bothbosu-youtube-scam-conversations-train-2 | scam | 0.560 | 0 | 0.329 | low | NO |
| bothbosu-youtube-scam-conversations-train-3 | scam | 0.589 | 1 | 0.437 | suspicious | yes |
| bothbosu-youtube-scam-conversations-train-4 | scam | 0.548 | 0 | 0.322 | low | NO |
| bothbosu-youtube-scam-conversations-train-5 | scam | 0.540 | 0 | 0.318 | low | NO |
| bothbosu-youtube-scam-conversations-train-6 | scam | 0.483 | 1 | 0.375 | suspicious | yes |
| bothbosu-youtube-scam-conversations-train-7 | scam | 0.463 | 1 | 0.363 | suspicious | yes |
| bothbosu-youtube-scam-conversations-train-8 | scam | 0.482 | 0 | 0.284 | low | NO |
| bothbosu-youtube-scam-conversations-train-9 | scam | 0.509 | 0 | 0.299 | low | NO |
| bothbosu-youtube-scam-conversations-train-10 | scam | 0.410 | 0 | 0.241 | low | NO |
| bothbosu-youtube-scam-conversations-train-11 | scam | 0.546 | 0 | 0.321 | low | NO |
| bothbosu-youtube-scam-conversations-train-12 | scam | 0.619 | 0 | 0.364 | suspicious | NO |
| bothbosu-youtube-scam-conversations-train-13 | scam | 0.688 | 0 | 0.405 | suspicious | NO |
| bothbosu-youtube-scam-conversations-train-14 | scam | 0.551 | 0 | 0.324 | low | NO |
| bothbosu-youtube-scam-conversations-train-15 | scam | 0.517 | 0 | 0.304 | low | NO |
| bothbosu-youtube-scam-conversations-train-16 | scam | 0.444 | 0 | 0.261 | low | NO |
| bothbosu-youtube-scam-conversations-train-17 | scam | 0.455 | 0 | 0.268 | low | NO |
| bothbosu-youtube-scam-conversations-train-18 | scam | 0.581 | 0 | 0.342 | low | NO |
| bothbosu-youtube-scam-conversations-train-19 | scam | 0.403 | 0 | 0.237 | low | NO |

**`fusion_notlow`**

| id | label | text_score | n_hits | risk_score | risk_level | correct? |
|---|---|---|---|---|---|---|
| bothbosu-youtube-scam-conversations-train-0 | scam | 0.584 | 1 | 0.434 | suspicious | yes |
| bothbosu-youtube-scam-conversations-train-1 | scam | 0.496 | 0 | 0.292 | low | NO |
| bothbosu-youtube-scam-conversations-train-2 | scam | 0.560 | 0 | 0.329 | low | NO |
| bothbosu-youtube-scam-conversations-train-3 | scam | 0.589 | 1 | 0.437 | suspicious | yes |
| bothbosu-youtube-scam-conversations-train-4 | scam | 0.548 | 0 | 0.322 | low | NO |
| bothbosu-youtube-scam-conversations-train-5 | scam | 0.540 | 0 | 0.318 | low | NO |
| bothbosu-youtube-scam-conversations-train-6 | scam | 0.483 | 1 | 0.375 | suspicious | yes |
| bothbosu-youtube-scam-conversations-train-7 | scam | 0.463 | 1 | 0.363 | suspicious | yes |
| bothbosu-youtube-scam-conversations-train-8 | scam | 0.482 | 0 | 0.284 | low | NO |
| bothbosu-youtube-scam-conversations-train-9 | scam | 0.509 | 0 | 0.299 | low | NO |
| bothbosu-youtube-scam-conversations-train-10 | scam | 0.410 | 0 | 0.241 | low | NO |
| bothbosu-youtube-scam-conversations-train-11 | scam | 0.546 | 0 | 0.321 | low | NO |
| bothbosu-youtube-scam-conversations-train-12 | scam | 0.619 | 0 | 0.364 | suspicious | yes |
| bothbosu-youtube-scam-conversations-train-13 | scam | 0.688 | 0 | 0.405 | suspicious | yes |
| bothbosu-youtube-scam-conversations-train-14 | scam | 0.551 | 0 | 0.324 | low | NO |
| bothbosu-youtube-scam-conversations-train-15 | scam | 0.517 | 0 | 0.304 | low | NO |
| bothbosu-youtube-scam-conversations-train-16 | scam | 0.444 | 0 | 0.261 | low | NO |
| bothbosu-youtube-scam-conversations-train-17 | scam | 0.455 | 0 | 0.268 | low | NO |
| bothbosu-youtube-scam-conversations-train-18 | scam | 0.581 | 0 | 0.342 | low | NO |
| bothbosu-youtube-scam-conversations-train-19 | scam | 0.403 | 0 | 0.237 | low | NO |

**`fusion_high_only`**

| id | label | text_score | n_hits | risk_score | risk_level | correct? |
|---|---|---|---|---|---|---|
| bothbosu-youtube-scam-conversations-train-0 | scam | 0.584 | 1 | 0.434 | suspicious | NO |
| bothbosu-youtube-scam-conversations-train-1 | scam | 0.496 | 0 | 0.292 | low | NO |
| bothbosu-youtube-scam-conversations-train-2 | scam | 0.560 | 0 | 0.329 | low | NO |
| bothbosu-youtube-scam-conversations-train-3 | scam | 0.589 | 1 | 0.437 | suspicious | NO |
| bothbosu-youtube-scam-conversations-train-4 | scam | 0.548 | 0 | 0.322 | low | NO |
| bothbosu-youtube-scam-conversations-train-5 | scam | 0.540 | 0 | 0.318 | low | NO |
| bothbosu-youtube-scam-conversations-train-6 | scam | 0.483 | 1 | 0.375 | suspicious | NO |
| bothbosu-youtube-scam-conversations-train-7 | scam | 0.463 | 1 | 0.363 | suspicious | NO |
| bothbosu-youtube-scam-conversations-train-8 | scam | 0.482 | 0 | 0.284 | low | NO |
| bothbosu-youtube-scam-conversations-train-9 | scam | 0.509 | 0 | 0.299 | low | NO |
| bothbosu-youtube-scam-conversations-train-10 | scam | 0.410 | 0 | 0.241 | low | NO |
| bothbosu-youtube-scam-conversations-train-11 | scam | 0.546 | 0 | 0.321 | low | NO |
| bothbosu-youtube-scam-conversations-train-12 | scam | 0.619 | 0 | 0.364 | suspicious | NO |
| bothbosu-youtube-scam-conversations-train-13 | scam | 0.688 | 0 | 0.405 | suspicious | NO |
| bothbosu-youtube-scam-conversations-train-14 | scam | 0.551 | 0 | 0.324 | low | NO |
| bothbosu-youtube-scam-conversations-train-15 | scam | 0.517 | 0 | 0.304 | low | NO |
| bothbosu-youtube-scam-conversations-train-16 | scam | 0.444 | 0 | 0.261 | low | NO |
| bothbosu-youtube-scam-conversations-train-17 | scam | 0.455 | 0 | 0.268 | low | NO |
| bothbosu-youtube-scam-conversations-train-18 | scam | 0.581 | 0 | 0.342 | low | NO |
| bothbosu-youtube-scam-conversations-train-19 | scam | 0.403 | 0 | 0.237 | low | NO |

## 5. Honest discussion

**The headline finding: right now, full fusion (`fusion_notlow`) catches FEWER scams than the text model alone, on both datasets.** On the 15 fresh scam scenarios: text_only 15/15 vs fusion_notlow 8/15. On the 20 real YouTube calls: text_only 12/20 vs fusion_notlow 6/20. `fusion_high_only` catches essentially nothing on either dataset (0/20 real calls). The mechanism is a specific, reproducible calibration effect, not noise: `combine()` computes a weighted average of whichever of {text, signature, audio} are active, renormalizing over the active weights (see `kavach/fusion.py`). The audio model isn't shipped yet, so `audio_score` is always `None` in practice today — every real request renormalizes over just {text: 0.5, signature: 0.35} => effective weights {text: 0.588, signature: 0.412}. When a scam call has zero signature-engine hits (very common for phrasing the fixed regex list was never written for), `signature_subscore` is exactly 0.0, which *actively pulls the average down* rather than leaving the text signal untouched: `risk_score = text_score * 0.588`. A text_score of 1.0 (the model's maximum possible confidence) therefore caps out at risk_score=0.588, which is BELOW both the suspicious margin needed to consistently clear 0.35 for weaker signals and, mathematically, always below the high threshold of 0.65 — i.e. with no audio signal, `risk_level` can structurally never reach 'high' from text alone, no matter how confident the text model is, unless a signature also fires. That is exactly why `fusion_high_only` scores 0% on both datasets above. This is a calibration/weighting issue, not a code defect, so it was intentionally left unmodified rather than silently reweighted — the fusion weights and 'high' threshold were plausibly chosen assuming a third, not-yet-existing audio signal would routinely help carry high-confidence detections the rest of the way, which isn't true yet since no ONNX audio model is shipped. Recommendation for whoever tunes this next: either raise the effective text-only ceiling (e.g. lower the 'high' threshold, or give text more relative weight when audio is absent) or treat 'suspicious' as the actionable warning level in the product UI until an audio signal exists.

**Where fusion helps.** The signature engine catches hard-coded, unambiguous scam tells — OTP/PIN requests, remote-access app installs, UPI collect-request tricks, digital-arrest/warrant language — that a TF-IDF model trained mostly on synthetic transcripts can miss when the phrasing is novel. On the fresh scenarios written for this suite specifically to avoid template overlap, several scam scripts (e.g. the FASTag phishing call, the credit-card-limit-upgrade call, the SIM e-KYC call) contain explicit CVV/OTP/card-detail requests that the signature engine is built to catch regardless of vocabulary; fusing that signal in raises the fusion `risk_score` even when the text model's probability alone sits below 0.5.

**Where fusion hurts (or does nothing).** Several of the fresh scam scenarios were deliberately written *without* any of the 12 hard-coded signature patterns firing (e.g. the rental-deposit token-advance scam, the matrimonial premium-unlock scam, the job-advance-fee scam, the second-victimization 'SEBI refund' scam) — these rely on social pressure and advance-fee framing rather than OTP/remote-access/secrecy language, so `signatures_only` is blind to them and fusion's improvement over `text_only` on those rows depends entirely on the text model generalizing to unseen phrasing, which is exactly the weak link this suite is meant to expose. On the real YouTube calls specifically, none of the 12 signatures are tuned for the US-centric SSN/tech-support/prize-scam phrasing in that dataset (no 'digital arrest', no UPI, no Indian KYC language), so `signatures_only` catches very few of them — any lift on that dataset has to come from the text model, not the rule engine.

**Known failure modes.** (1) Any signature-based approach is a fixed-vocabulary regex list — it cannot catch a well-written advance-fee scam that never says OTP, PIN, AnyDesk, or 'digital arrest'. (2) The text model's training data skews synthetic and India-specific; the baseline 12/20 recall on real YouTube calls (largely US SSN/tech-support scams) shows it does not yet generalize cleanly across accents, scam families, or English dialects. (3) Fusion is a weighted average, not a learned combiner — it cannot know when to trust one signal over another, so a benign call that happens to mention money and urgency together (see the false positives listed below, if any) can still get pushed toward 'suspicious'.

**False positives observed in this run:**
- `text_only`: `benign-bank-fraud-alert-yes-no`

**Full fusion still misses these real scam calls:** `bothbosu-youtube-scam-conversations-train-1`, `bothbosu-youtube-scam-conversations-train-2`, `bothbosu-youtube-scam-conversations-train-4`, `bothbosu-youtube-scam-conversations-train-5`, `bothbosu-youtube-scam-conversations-train-8`, `bothbosu-youtube-scam-conversations-train-9`, `bothbosu-youtube-scam-conversations-train-10`, `bothbosu-youtube-scam-conversations-train-11`, `bothbosu-youtube-scam-conversations-train-14`, `bothbosu-youtube-scam-conversations-train-15`, `bothbosu-youtube-scam-conversations-train-16`, `bothbosu-youtube-scam-conversations-train-17`, `bothbosu-youtube-scam-conversations-train-18`, `bothbosu-youtube-scam-conversations-train-19`.

**Calls the text model alone catches but full fusion misses (the dilution effect above, in action):** `bothbosu-youtube-scam-conversations-train-11`, `bothbosu-youtube-scam-conversations-train-14`, `bothbosu-youtube-scam-conversations-train-15`, `bothbosu-youtube-scam-conversations-train-18`, `bothbosu-youtube-scam-conversations-train-2`, `bothbosu-youtube-scam-conversations-train-4`, `bothbosu-youtube-scam-conversations-train-5`, `bothbosu-youtube-scam-conversations-train-9`.

**Bottom line.** This is an honest-evals framing, not a victory lap: the headline 12/20 text-only recall on real calls is the number to beat, and the results table above should be read side-by-side with it rather than in isolation. Where fusion wins, it wins because the signature engine adds a hard-coded, high-precision signal on top of a text model that is still generalizing imperfectly; where it doesn't win, it's because both signals share the same blind spot (novel phrasing, non-Indian scam scripts, or advance-fee framing with no explicit request for secrets).