"""India-specific synthetic call generator for the Kavach corpus.

The open scam-conversation datasets are US-centric (SSN, Medicare...). India's dominant
scam patterns — digital arrest, fake KYC, UPI collect-request traps, KBC lottery, courier
customs, army-officer marketplace fraud, loan-app recovery threats — are absent. This
module generates labeled multi-turn call transcripts for those patterns, plus *matched
benign counterparts* (a real bank reminder, a real courier call...) so a classifier must
learn the actual tells (OTP requests, urgency, secrecy, payment redirection) rather than
"phone call about money ⇒ scam".

Each scenario is a list of turns; each turn has alternative phrasings; phrasings have
slots filled from pools. Variety is combinatorial: alternatives^turns x slot pools.

Usage: from india_synth import generate; records = generate(n_per_scenario=120, seed=13)
"""

import random

# ---------------------------------------------------------------- slot pools
POOLS = {
    "name": ["Sharma ji", "Mr. Verma", "Mrs. Iyer", "Rahul", "Priya", "Anil Kumar",
             "Sunita ji", "Mr. Reddy", "Kavita", "Deepak", "Mr. Khan", "Meena ji"],
    "bank": ["SBI", "HDFC Bank", "ICICI Bank", "Axis Bank", "Punjab National Bank",
             "Bank of Baroda", "Kotak Bank", "Canara Bank"],
    "city": ["Mumbai", "Delhi", "Bengaluru", "Hyderabad", "Chennai", "Pune",
             "Kolkata", "Lucknow", "Jaipur", "Ahmedabad"],
    "amount_big": ["2 lakh 30 thousand rupees", "4.5 lakh rupees", "1 lakh 80 thousand rupees",
                   "7 lakh rupees", "95 thousand rupees", "3 lakh rupees"],
    "amount_small": ["4,999 rupees", "2,350 rupees", "9,999 rupees", "1,499 rupees",
                     "6,800 rupees", "3,200 rupees"],
    "courier": ["FedEx", "Blue Dart", "DTDC", "India Post", "Delhivery"],
    "agency": ["Mumbai Police cyber cell", "CBI", "Narcotics Control Bureau",
               "Delhi Police crime branch", "TRAI", "Enforcement Directorate"],
    "app": ["AnyDesk", "TeamViewer", "QuickSupport"],
    "item": ["dining table", "sofa set", "refrigerator", "washing machine", "royal enfield bike",
             "study desk", "almirah"],
    "telecom": ["Jio", "Airtel", "Vi"],
    "last4": ["4412", "8830", "1275", "9046", "3391", "5568"],
    "time": ["11 AM", "2 PM", "4:30 PM", "10:15 AM", "6 PM", "12:30 PM"],
    "day": ["tomorrow", "Monday", "Thursday", "Saturday", "day after tomorrow"],
    "doctor": ["Dr. Mehta", "Dr. Kulkarni", "Dr. Nair", "Dr. Bansal"],
    "relative": ["your son", "your daughter", "your nephew", "your grandson"],
    "gulf_country": ["Dubai", "Doha", "Riyadh", "Muscat", "Abu Dhabi"],
    "dating_app": ["MatchMate", "TrueConnect", "SoulSync"],
    "nbfc": ["Bajaj Finserv", "Home Credit", "Fullerton India", "Tata Capital"],
    "insurer": ["Max Life", "Bajaj Allianz", "Star Health", "HDFC Ergo", "ICICI Lombard"],
}

C, R = "Caller", "Receiver"  # speaker tags used in unified transcripts


def _t(speaker, *alternatives):
    return (speaker, list(alternatives))


# ------------------------------------------------------------ scam scenarios
# Every scenario: (scam_type, label, [turns]); turn = (speaker, [alt phrasings]).
SCENARIOS = {

    "digital_arrest": ("govt_impersonation", 1, [
        _t(C, "Hello, am I speaking with {name}? This is Inspector Rathore calling from {agency}.",
            "Good afternoon. This is sub-inspector Yadav, {agency}. Is this {name}?"),
        _t(R, "Yes, speaking. What is this about?", "Yes... police? What happened, sir?"),
        _t(C, "A parcel booked in your name through {courier} has been seized in {city}. It contains illegal drugs and fake passports.",
            "Your Aadhaar number has been used to open bank accounts involved in money laundering of {amount_big}. There is an arrest warrant against you.",
            "A SIM card taken on your Aadhaar was used for illegal activity. {agency} has registered an FIR against you."),
        _t(R, "What? I never sent any parcel. This must be a mistake.",
            "That's impossible, I haven't done anything like that."),
        _t(C, "That is what everyone says. This is a matter of national security. You are now under digital arrest. Do not disconnect this call and do not tell anyone, not even your family.",
            "If you are innocent, cooperate with the verification. You must stay on video call until the investigation is over. Telling anybody will be treated as leaking case information."),
        _t(R, "Digital arrest? I have never heard of that. I'm scared, what do I do?",
            "Please sir, I am a respectable person. How do I clear my name?"),
        _t(C, "To verify your innocence, your funds must be audited by RBI. Transfer {amount_big} to the secure government account I am sending you. It will be refunded after verification in 24 hours.",
            "Share your bank details and the OTP you receive so we can scan your accounts for illegal money. If you refuse, police will come to arrest you within one hour."),
        _t(R, "Okay... okay, please don't arrest me. I am doing it now. Which account do I send to?",
            "I don't know... this doesn't feel right. Why would police ask for money on the phone?"),
        _t(C, "Send to the account number I am messaging you now. Remember, do not disconnect and do not tell your family. This is a sealed investigation.",
            "Do not argue. Every minute of delay is being noted in your case file. Stay on the line and complete the transfer."),
    ]),

    "fake_kyc": ("bank_fraud", 1, [
        _t(C, "Hello sir, I am calling from {bank} head office. Your KYC has expired and your account ending {last4} will be blocked today by RBI order.",
            "Good morning, this is the {bank} verification department. Your debit card ending {last4} is suspended due to incomplete KYC."),
        _t(R, "Oh no, I use that account for everything. What should I do?",
            "Blocked? Nobody informed me. How can I fix it?"),
        _t(C, "No need to worry, it takes two minutes on the phone. Just confirm your full card number and the expiry date.",
            "I can update it right now. Please tell me your Aadhaar number and the OTP that has just come on your phone.",
            "Download the {app} app so I can complete the verification from our side. Then open your banking app."),
        _t(R, "The message says not to share the OTP with anyone...",
            "Are you sure this is safe? The bank always says don't share these things."),
        _t(C, "That warning is for strangers, sir. I am calling from the bank itself, my employee ID is 44821. If you don't verify in the next ten minutes the account gets permanently frozen.",
            "Sir, do you want your pension money stuck for six months? Then kindly cooperate quickly. Read me the six digit code."),
        _t(R, "Okay, okay. The OTP is coming now... should I read it?",
            "Fine, but I will complain if anything happens to my account."),
        _t(C, "Yes, read it immediately, it expires in sixty seconds. Also keep this call confidential — bank policy.",
            "Quickly sir. Also confirm your ATM PIN so I can reactivate the card from the backend."),
    ]),

    "upi_refund": ("refund_scam", 1, [
        _t(C, "Hello, is this {name}? I just sent {amount_small} to your UPI by mistake. It was meant for my brother, same name as you.",
            "Sir, please help, I am calling about a wrong transaction. My father accidentally paid {amount_small} to your number."),
        _t(R, "Let me check... I don't see any credit in my account.",
            "Really? I did get some notification just now."),
        _t(C, "It shows debited from my side. I am sending you a collect request of {amount_small} — just accept it and enter your UPI PIN, and the money will come back to me automatically.",
            "The bank told me the refund happens when you approve the request I sent on your UPI app. Please open the app and enter your PIN to approve."),
        _t(R, "But entering my PIN means I am paying you, not receiving...",
            "Okay wait, I am opening the app. It says 'pay {amount_small}'."),
        _t(C, "No no sir, for receiving also PIN is needed, that is the new RBI rule. Please do it fast, I need this money for a medical emergency, my mother is in hospital.",
            "Yes it will show 'pay', that is just how refund requests look. Trust me, I am also a customer like you. Please hurry, it is an emergency."),
    ]),

    "courier_customs": ("courier_scam", 1, [
        _t(C, "Hello, I am calling from {courier} customer care. A package addressed to you from Taiwan has been held at {city} customs.",
            "This is the {courier} international desk. Your parcel has been stopped by customs because the contents are suspicious."),
        _t(R, "I haven't ordered anything from abroad.",
            "A package? For me? What is inside it?"),
        _t(C, "The scan shows five expired passports, credit cards, and 200 grams of a banned substance. This is a criminal matter, I am transferring your call to the {agency}.",
            "It contains illegal medicines. Your Aadhaar and phone number were used for the booking. Please talk to the cyber police officer on this same line."),
        _t(R, "Oh god. Okay, connect me. I want to clear this up.",
            "This must be identity theft! What do I do?"),
        _t(C, "Hello, officer Kadam speaking, {agency}. To close this case before FIR, you must pay a customs clearance and verification fee of {amount_small} immediately through the link we send you. Otherwise arrest procedure starts today.",
            "This is officer Salunkhe. Your name can be cleared if you cooperate. First, how much balance is in your bank account? We need to verify your funds are not from smuggling."),
    ]),

    "army_olx": ("marketplace_scam", 1, [
        _t(C, "Hello ji, I saw your {item} listing online. I want to buy it, price is no issue. I am a CRPF jawan posted in {city}, getting transferred, so I need it urgently.",
            "Namaste, calling about the {item} you posted. I am an army officer, my unit is shifting so I cannot come personally, but I will pay full amount right now."),
        _t(R, "Okay great. You can come see it this week?",
            "Sure, when do you want to pick it up?"),
        _t(C, "Pickup my transport team will do. For payment, I am sending a QR code — scan it and enter your PIN, then {amount_small} will come to your account instantly. It is the army canteen payment system.",
            "I will pay in advance through UPI. First a small test: I send you a QR code, you scan it and approve, then you receive one rupee. After that we do the full amount."),
        _t(R, "But scanning a QR is for paying money, not receiving, no?",
            "One second, my son told me never to scan QR codes from unknown people."),
        _t(C, "Sir, army system is different, it is reverse QR. Hundreds of people sell to us like this. Do it while I am on the line, I have parade in ten minutes.",
            "Ji that is for fraud people, I am sending you my army ID card photo right now. See, fully genuine. Now please scan quickly, my commanding officer is waiting."),
    ]),

    "kbc_lottery": ("prize_scam", 1, [
        _t(C, "Congratulations {name} ji! Your mobile number has been selected in the KBC lucky draw. You have won 25 lakh rupees!",
            "Hello! I am calling from the Kaun Banega Crorepati head office {city}. Your SIM card has won the jackpot of 25 lakh in our all-India draw!"),
        _t(R, "25 lakh! Really? I never win anything!",
            "Is this a joke? I didn't enter any lottery."),
        _t(C, "No entry needed sir, it is automatic from the telecom company records. To release the prize cheque, you only pay the government tax of {amount_small} first. This is refundable rule.",
            "It is 100 percent genuine, I am sending you the winner certificate with the KBC logo on WhatsApp. Just deposit the processing fee of {amount_small} today so your file is not cancelled."),
        _t(R, "Tax first? Can't you cut the tax from the prize money itself?",
            "Let me ask my daughter first, she handles these things."),
        _t(C, "RBI rules do not allow deduction, tax must come from the winner. And sir, do not tell anyone until the money arrives, otherwise the prize gets cancelled — company policy. Many winners lost their prize by talking.",
            "Madam/sir, the draw closes at 5 PM today. If the fee does not reach by then, your 25 lakh goes to the waiting-list winner. Why lose lakhs to save thousands?"),
    ]),

    "loan_recovery": ("loan_scam", 1, [
        _t(C, "Hello {name}. You took a loan of {amount_small} from our instant loan app. It is overdue. Pay within two hours or face consequences.",
            "This is the recovery department. Your loan with penalty is now {amount_small}. Pay immediately or we start the recovery process."),
        _t(R, "I repaid that loan already! I have the receipt.",
            "The app showed 7 days interest-free. It has only been 4 days!"),
        _t(C, "Our system shows nothing. We have access to your full contact list and gallery. If payment does not come today, we will send your photos, edited in a shameful way, to every contact including your family.",
            "Receipts don't matter. We will call your office, your relatives, everyone, and tell them you are a fraud and a defaulter. Your morphed photo is ready to be circulated."),
        _t(R, "Please don't do that! This is harassment, it is illegal!",
            "Oh god. Please, I will complain to the police."),
        _t(C, "Police can do nothing to us. Save your respect, pay {amount_small} on this UPI number in the next one hour. This is your last warning.",
            "Complain wherever you want, the photos go out in one hour. Pay now and everything gets deleted."),
    ]),

    "investment_trading": ("investment_scam", 1, [
        _t(C, "Good evening {name}, I am calling from a SEBI-registered wealth advisory in {city}. Our AI trading system is giving members 30 percent returns every month, fully guaranteed.",
            "Hello sir, you were referred by a mutual friend for our exclusive stock tips group. Members doubled their money in 60 days. We have only two seats left."),
        _t(R, "30 percent monthly? That sounds too good to be true.",
            "Which company are you from exactly? Are you registered?"),
        _t(C, "Fully registered sir, I will send the certificate on WhatsApp. Big people, IAS officers, doctors, all are members. Start with just {amount_small} in our app and watch it grow this week itself.",
            "Yes, guaranteed by our algorithm, it never loses. See, I am adding you to our VIP Telegram group where daily profit screenshots are posted. Deposit {amount_small} today to activate your account."),
        _t(R, "Can I withdraw the money anytime?",
            "Let me think about it and call you back."),
        _t(C, "Anytime withdrawal, one click. But the joining bonus of 20 percent is only for today. After midnight the offer closes. Shall I send the deposit link?",
            "Sir, thinking means losing. Yesterday one member from {city} made 40 thousand in a day. Give me your UPI, I will send the payment link right now."),
    ]),

    # -------------------------------------------------------- benign scenarios
    "bank_reminder_legit": ("banking_legit", 0, [
        _t(C, "Good morning, this is a service call from {bank}. Am I speaking with the account holder {name}?",
            "Hello, I'm calling from {bank} customer service regarding your credit card ending {last4}."),
        _t(R, "Yes, speaking. What is it about?", "Yes, this is he. Go ahead."),
        _t(C, "This is a reminder that your credit card payment of {amount_small} is due on the 15th. You can pay through your banking app, net banking, or at any branch.",
            "Your fixed deposit is maturing next week. If you wish to renew or change the tenure, you can do it in the app or visit your home branch with your ID."),
        _t(R, "Oh yes, I nearly forgot. I'll pay through the app today.",
            "Alright, I will visit the branch on {day}."),
        _t(C, "Perfect. And a security reminder: {bank} never asks for your OTP, PIN, or password on calls. If anyone does, please report it. Is there anything else I can help with?",
            "Thank you. Please remember the bank never requests OTP or card details over the phone. Have a good day, sir."),
        _t(R, "Good to know. Thank you for the reminder.", "No, that's all. Thanks."),
    ]),

    "delivery_legit": ("delivery", 0, [
        _t(C, "Hello, I'm the {courier} delivery executive. I have a package for {name}, I am near your building but can't find the exact gate.",
            "Good afternoon, {courier} calling. Your parcel is out for delivery today between {time} and evening. Will someone be home?"),
        _t(R, "Yes, I'm home. Take the second gate, blue building, third floor.",
            "I'm at office right now. Can you leave it with the security guard?"),
        _t(C, "Got it, blue building. I'll be there in five minutes. It's cash on delivery, {amount_small} — you can also pay by UPI at the door on the company QR.",
            "Sure, I can leave it with security if you confirm the OTP that the app shows on your order page to the guard — standard delivery confirmation."),
        _t(R, "I'll pay by UPI when you arrive. See you soon.",
            "Alright, I'll message the code to the guard. Thank you."),
        _t(C, "Thank you sir, reaching in five minutes.",
            "Perfect, delivery will be done in an hour. Have a nice day."),
    ]),

    "clinic_appointment_legit": ("appointment", 0, [
        _t(C, "Good morning, this is {doctor}'s clinic in {city}. I'm calling to confirm your appointment {day} at {time}.",
            "Hello, calling from the City Hospital OPD desk. You have a follow-up with {doctor} scheduled {day} at {time}."),
        _t(R, "Yes, I'll be there. Should I bring the old reports?",
            "Actually, can we shift it a bit later in the day?"),
        _t(C, "Yes, please carry your previous prescription and reports. The consultation fee is {amount_small}, payable at the reception by card, cash, or UPI.",
            "Let me check... {time} is available on {day}. I've moved it. Please arrive ten minutes early for registration."),
        _t(R, "Sure, noted. Thank you for the reminder.",
            "That works. Thanks a lot."),
        _t(C, "Welcome. If you need to reschedule, just call this number. Have a good day.",
            "You're welcome. Get well soon, and see you {day}."),
    ]),

    "telecom_offer_legit": ("telemarketing", 0, [
        _t(C, "Hi, I'm calling from {telecom} regarding your prepaid number. Your current plan expires on {day} and we have a new offer with more data at the same price.",
            "Good afternoon, {telecom} customer care. As a long-time user you are eligible for a discounted annual plan. May I take one minute to explain?"),
        _t(R, "Okay, tell me. What's the offer?",
            "I'm a bit busy. Is it quick?"),
        _t(C, "The new plan gives 2.5 GB per day and unlimited calls for the same recharge. You can activate it yourself from the {telecom} app or any recharge shop — nothing needed from me.",
            "Very quick, madam. The annual plan saves about {amount_small} over monthly recharges. If interested, just recharge from the official app; no details needed on this call."),
        _t(R, "Sounds fine, I'll do it from the app tonight.",
            "Okay, I'll look at it in the app. Thanks."),
        _t(C, "Great. Thank you for choosing {telecom}. Have a nice day.",
            "Thank you for your time, sir. Goodbye."),
    ]),

    "utility_service_legit": ("utility_legit", 0, [
        _t(C, "Hello, this is the gas agency. Your cylinder booking is confirmed; the delivery person will come {day} morning.",
            "Good morning, electricity board maintenance section. There is scheduled maintenance in your area {day} from {time}, power will be off for about two hours."),
        _t(R, "Okay. How much is the cylinder now?",
            "Two hours? Alright, good you informed me."),
        _t(C, "It is {amount_small} this month, pay cash or scan the QR printed on the receipt the delivery man carries.",
            "Yes, we are informing all residents in advance. No action needed from your side. Supply resumes automatically."),
        _t(R, "Alright, someone will be home. Thank you.",
            "Thanks for letting me know."),
        _t(C, "Thank you, madam. Goodbye.", "Welcome. Have a good day."),
    ]),

    "family_call_legit": ("personal", 0, [
        _t(C, "Hello {name}! It's me. How are you? I was just thinking about you.",
            "Hi, it's your cousin from {city}. Long time! How is everyone at home?"),
        _t(R, "Arre hello! So nice to hear your voice. We are all fine. How are the kids?",
            "Hey! All good here. How have you been?"),
        _t(C, "Kids are great — {relative} got a promotion last month! Listen, we are planning to visit {city} on {day}. Are you free that weekend?",
            "All well. Actually I'm calling because we're arranging a small get-together on {day} at {time}. You must come."),
        _t(R, "Wonderful news! Yes, come over, stay with us. I'll tell everyone.",
            "That sounds lovely. I'll be there. Should I bring something?"),
        _t(C, "Perfect, I'll book the tickets and send you the details. Say hello to everyone!",
            "Just yourself! Okay, see you then. Bye!"),
    ]),

    "hr_interview_legit": ("appointment", 0, [
        _t(C, "Hello, am I speaking with {name}? I'm calling from the HR team regarding the application you submitted on our careers page.",
            "Good afternoon {name}, this is HR from the company you interviewed with last week in {city}."),
        _t(R, "Yes, speaking! Thank you for calling back.",
            "Yes, hello! I've been waiting to hear from you."),
        _t(C, "We'd like to schedule your technical interview {day} at {time}, on video call. The invite goes to the email on your application.",
            "Good news — the team wants to move forward. The next round is {day} at {time}. Does that work for you?"),
        _t(R, "That works for me. Anything to prepare?",
            "Yes, that time is fine. What are the next steps?"),
        _t(C, "Just be ready for questions on your projects. The link is in the invite; no fee, no documents needed at this stage. Best of luck!",
            "HR will email the details — please check your inbox and confirm. Talk soon, and good luck!"),
    ]),

    # ---------------------------------------------------------------------
    # Hardened scenarios (error-analysis-driven), added after an eval run
    # showed the fine-tuned text model confidently missing certain
    # advance-fee-style scam families and confidently false-alarming on
    # certain benign look-alikes. These 5 new scam + 5 new hard-negative
    # benign scenarios cover those same CATEGORIES with entirely different
    # situations, phrasing, and slot fills than evals/scenarios.py -- no
    # transcript here is copied or closely paraphrased from that file, to
    # preserve eval integrity (the eval set stays a genuinely unseen probe
    # even though the category names now overlap by design).
    # ---------------------------------------------------------------------

    "job_visa_advance_fee": ("unknown_scam", 1, [
        _t(C, "Congratulations {name}, your profile has been selected for a housekeeping staff position in {gulf_country}, salary starting at {amount_small} a month plus accommodation.",
            "Good news, an overseas placement agency has approved your application for a driver's position in {gulf_country} through our recruitment tie-up."),
        _t(R, "Really? I did apply through an agent a few months back, I'd almost given up.",
            "That's wonderful, when do I need to join?"),
        _t(C, "Your visa and medical test have already been initiated on our side. The total package — visa stamping, medical, and air ticket booking — comes to {amount_big}, but the company refunds most of it from your first three months' salary.",
            "Before we issue the offer letter, there's a one-time visa processing and medical package fee of {amount_big}, fully adjustable against your joining bonus."),
        _t(R, "That's a big amount to pay upfront, are you sure I get it back?",
            "I've read about people losing money to fake job agents, how do I know this is genuine?"),
        _t(C, "Sir, hundreds of candidates go through this every month, I can share the agency's registration certificate on WhatsApp right now for your comfort.",
            "Completely understandable, sir, that's why we only ask for it after your documents are already approved — your visa slot is confirmed, only the payment is pending."),
        _t(R, "Okay, let me think about it for a day.",
            "Can I pay half now and half later?"),
        _t(C, "Sir, the visa quota for this batch closes tomorrow, if the payment doesn't reach us today the slot goes to the next candidate on the waiting list.",
            "Half payment isn't possible, sir, the embassy processes the visa only after full payment, and the flight is already provisionally booked for next week."),
    ]),

    "hostel_pg_booking_advance": ("unknown_scam", 1, [
        _t(C, "Hello, I'm calling about the PG seat you enquired about near {city}, it's a shared room with three other students, very close to college.",
            "Namaste, this is regarding the hostel bed you asked about on the listing app, ladies-only floor, walking distance to campus."),
        _t(R, "Yes, the rent looked reasonable for that location. Can I visit and see the room?",
            "Sounds good, when can I come check the facilities?"),
        _t(C, "You can, but I have to be honest, four other students called about this exact bed this morning, it's one of our fastest-filling seats this season.",
            "Of course, but I'll be upfront, this batch of beds usually gets locked within a day of listing."),
        _t(R, "Okay, but I'd still like to see it before deciding.",
            "Understood, but I really can't decide without seeing it first."),
        _t(C, "I completely understand, but the warden only holds a seat for students who've paid the booking advance of {amount_small}, otherwise walk-ins take priority. It's fully adjustable against your first month's rent.",
            "That's fair, but our policy is a token booking amount of {amount_small} first, it secures your seat while you plan your visit, and it comes off your deposit later."),
        _t(R, "It still feels odd to pay before even seeing the room.",
            "I'm a bit hesitant to send money without seeing the place first."),
        _t(C, "I get that a lot, but I've filled twelve beds this week alone this way, and if you don't decide in the next couple of hours, I'll have to offer it to the next student in line.",
            "No pressure, but I do need to know in the next hour or so, otherwise the seat opens up to the others who already messaged me."),
    ]),

    "dating_app_video_unlock": ("unknown_scam", 1, [
        _t(C, "Hi, this is calling from {dating_app} support, we noticed you have a mutual match who's tried to video call you twice today.",
            "Hello, {dating_app} verification team here, your match, who's currently working on an oil rig project abroad, has requested a video call with you."),
        _t(R, "Oh, I saw the missed call notification but didn't know what it was for.",
            "Yes, we've been chatting for a couple of weeks, he seems genuine."),
        _t(C, "Video calls on our platform require the Elite Verified tier to protect both users' privacy, it's a one-time unlock fee of {amount_small}.",
            "For safety, direct video calls only activate once Elite Verification is unlocked on your account, it's a small one-time fee of {amount_small}."),
        _t(R, "I thought I already had a paid subscription on this app.",
            "Why would I need a separate fee just for a video call?"),
        _t(C, "Your current plan covers messaging only, ma'am, video and voice calls sit under our higher safety-verified tier, that's a platform-wide rule now.",
            "It's for both users' protection, ma'am, video call features unlock only after this one-time payment, standard across the platform."),
        _t(R, "Let me think about it, I don't want to keep spending on this app.",
            "This is starting to feel like a lot of separate charges."),
        _t(C, "Totally your call, but he did mention he's being redeployed next week and this might be the only window to actually see each other on video before that.",
            "I understand, but your match's account shows he's only active for another day or two before his rig assignment moves him out of network range."),
    ]),

    "cyber_recovery_processing_fee": ("refund_scam", 1, [
        _t(C, "Am I speaking with someone who filed a cyber-crime complaint about a UPI fraud around six months ago?",
            "Is this the person who lost money to a fake OTP call last year? I'm calling regarding your complaint reference."),
        _t(R, "Yes... I did file a complaint but nothing happened after that.",
            "Yes, that's me, I'd honestly stopped expecting any update."),
        _t(C, "We're from a special cyber-crime recovery task force reviewing old pending complaints. Your case has been shortlisted — we've traced part of the funds to a frozen wallet linked to the fraud network.",
            "Good news, our digital forensics unit managed to trace and freeze a chunk of the funds tied to your case number."),
        _t(R, "That's amazing, how much can I get back?",
            "Really? After all this time, that's such a relief."),
        _t(C, "Based on our recovery, you're eligible for {amount_big} back, but releasing frozen funds requires a mandatory processing and verification charge of {amount_small}, standard for all recovery cases.",
            "The amount eligible for release is {amount_big}, however a nominal cyber-cell processing fee of {amount_small} must be paid before the release order is signed."),
        _t(R, "I already lost money once to a fraud, I'm scared to pay anything again.",
            "That makes me nervous, why would I need to pay to get my own money back?"),
        _t(C, "That's a fair worry ma'am, but this fee goes toward the department's verification costs, not to any individual, and if it's not paid within 24 hours your file returns to the pending stack for months.",
            "I understand the hesitation, sir, but this is a one-time government-mandated charge, and delaying it means losing your place in this recovery batch."),
    ]),

    "health_insurance_bonus_unlock": ("prize_scam", 1, [
        _t(C, "Good afternoon, I'm calling from the policy benefits cell regarding your group health insurance policy through your old employer.",
            "Sir, this is regarding a health policy you or your employer took a few years back, it has an unclaimed no-claim bonus sitting against it."),
        _t(R, "I don't really remember the details of that policy anymore.",
            "I switched jobs since then, I'm not sure which policy you mean."),
        _t(C, "It's the group mediclaim policy from around three years back, it has accumulated a no-claim cashback of {amount_big} approved for release this quarter under new IRDAI norms.",
            "Records show an accumulated wellness bonus of {amount_big} on that policy, cleared for payout under this year's regulatory cycle."),
        _t(R, "Nobody ever told me about a bonus like this.",
            "That's news to me, I didn't know unused policies had a bonus."),
        _t(C, "Most policyholders don't know, sir, that's exactly why this cell reaches out directly — but to release it, there's a one-time IRDAI linking and administrative charge of {amount_small} that has to clear before the payout file closes today.",
            "It's a small regulatory unlock charge of {amount_small}, mandatory for any payout above a lakh, without it the file simply sits in the queue."),
        _t(R, "Why would I have to pay to receive my own bonus?",
            "That sounds backwards for an insurance payout."),
        _t(C, "I understand it seems unusual sir, but it's simply how the compliance process works this year, and if it isn't paid today the file resets to next quarter's batch, another long wait.",
            "Sir, I have several other policyholders waiting on this same cutoff, if you can confirm the UPI payment now I'll close your file within the hour."),
    ]),

    # -------------------------------------------------- hardened benign (hard-negative) scenarios
    "credit_card_fraud_alert_yesno": ("banking_legit", 0, [
        _t(C, "Hello, this is the fraud monitoring desk from {bank} credit cards, am I speaking with the cardholder on the card ending {last4}?",
            "Good evening, calling from {bank}'s card security team regarding a transaction on your card ending {last4}."),
        _t(R, "Yes, that's me.",
            "Yes, speaking, is everything okay?"),
        _t(C, "We've noticed an attempted transaction of {amount_big} at an electronics outlet, did you make this purchase, yes or no?",
            "There's a charge attempt of {amount_big} showing from a merchant abroad, can you confirm whether this was you, just a yes or no is fine."),
        _t(R, "No, I haven't made any purchase like that.",
            "No, I've been home all day, I didn't authorize anything."),
        _t(C, "Understood, thank you for confirming, we're declining the transaction and blocking the card right now. I want to be clear, I will never ask you for your card number, CVV, expiry, or any OTP on this call — I only needed your yes or no.",
            "Thank you, that's all I needed. Just so you know, we never ask for your PIN, OTP, or full card number over the phone, this call was only for that one confirmation."),
        _t(R, "Okay, that's reassuring. What happens to the card now?",
            "Good to know. So what's the next step?"),
        _t(C, "A replacement card will be dispatched to your registered address within a week; if you ever get a call asking for OTP or card details claiming to be us, hang up and call the number on the back of your card.",
            "We'll courier a new card to you shortly. Anytime you want to verify a call like this is genuine, just call the helpline number printed on your card directly."),
    ]),

    "tenant_document_verification_legit": ("none", 0, [
        _t(C, "Good morning, I'm calling from the local police station regarding the tenant verification form your landlord submitted for your rental agreement.",
            "Hello, this is the beat constable's office, we need to complete the routine tenant verification for your new flat."),
        _t(R, "Yes, my landlord mentioned the police would need to verify some documents.",
            "Oh right, I was told this would happen when I signed the rental agreement."),
        _t(C, "Correct, I'd like to schedule a short visit, would {day} around {time} work for you?",
            "I just need ten minutes at your convenience, is {day} {time} okay for you?"),
        _t(R, "Yes, I'll be home then. What should I keep ready?",
            "That works, what documents do you need from me?"),
        _t(C, "Please keep your Aadhaar card, the signed rental agreement, and a recent photo ready for our records.",
            "Just your ID proof, the rental agreement copy, and one passport-size photo for the verification form."),
        _t(R, "Is there any fee I need to pay for this?",
            "Do I need to pay anything for this verification?"),
        _t(C, "No sir, tenant verification is a free service, there's no charge involved at any point.",
            "No fee at all, sir, this is a standard, free process handled directly by the station."),
    ]),

    "loan_application_followup_legit": ("banking_legit", 0, [
        _t(C, "Hello, I'm calling from {nbfc} regarding the personal loan application you submitted last week.",
            "Good afternoon, this is your loan officer at {nbfc}, following up on your home loan application, reference number ending {last4}."),
        _t(R, "Yes, I've been waiting to hear back on that.",
            "Oh good, is there an update on my application?"),
        _t(C, "Your documents have been verified and the loan committee has approved it in principle, we just need your latest salary slip and bank statement to finalize.",
            "Good news, your file has cleared the initial credit check, we now need your property papers and income proof to move to disbursal."),
        _t(R, "I can send those over today, where should I email them?",
            "Sure, I'll gather those, should I bring them to the branch?"),
        _t(C, "You can upload them directly on our official app under 'my applications', or email them to the address on your application receipt — either works.",
            "Either the branch or our secure upload portal works, whichever is easier for you, no rush on timing."),
        _t(R, "Great, I'll upload them tonight.",
            "I'll drop by the branch this weekend then."),
        _t(C, "Perfect, once we receive them it usually takes 2-3 working days to process the disbursal, I'll call you once it's confirmed.",
            "Sounds good, I'll follow up once the documents come in, feel free to call this same number if you have questions."),
    ]),

    "motor_insurance_renewal_pushy_legit": ("insurance", 0, [
        _t(C, "Hello sir, this is calling from {insurer} regarding your car insurance policy that's expiring on {day}, I really need a few minutes of your time.",
            "Good afternoon, {insurer} renewals desk here, your two-wheeler policy lapses very soon and I'd strongly recommend renewing before that."),
        _t(R, "Oh, I hadn't realized it was expiring already.",
            "Right, I've been meaning to renew it, keep forgetting."),
        _t(C, "I understand you're busy, but driving without a valid policy isn't worth the risk, the renewal premium this year is {amount_small}, same coverage as before.",
            "I know these calls can be a bit much, but please don't let it lapse, the premium is {amount_small} for the same no-claim-bonus coverage you have now."),
        _t(R, "Okay, how do I actually pay it?",
            "Fine, what's the easiest way to renew?"),
        _t(C, "You can renew directly on our official app or website with your policy number, or visit any of our branches — I can't take any payment over this call, it has to go through those official channels.",
            "Please only use the official {insurer} app or your nearest branch to pay, I won't be sending any payment link on call or SMS."),
        _t(R, "Got it, I'll do it through the app tonight.",
            "Alright, I'll visit the branch this week then."),
        _t(C, "Please don't delay too long, sir, an active policy protects you and it's a quick five-minute process on the app.",
            "I'll just send a text reminder in a couple of days, but please try to get it done before the expiry date."),
    ]),

    "collections_reminder_firm_legit": ("banking_legit", 0, [
        _t(C, "Hello, this is the collections department at {bank} calling about your credit card bill of {amount_small}, which is now ten days overdue.",
            "Good afternoon, calling from {bank} regarding your personal loan EMI of {amount_small} that hasn't been received this month."),
        _t(R, "Oh, I think I missed the due date this time, sorry about that.",
            "Yes, I've been meaning to pay that, it slipped my mind."),
        _t(C, "I understand, but I do need to flag that continued delay affects your credit score and may attract late fees, so I'd request you clear it at the earliest.",
            "That's fine, but please note further delay will add a late payment charge and reflect on your credit report, so it's best to settle it soon."),
        _t(R, "Understood, I'll pay it this week.",
            "Okay, I'll clear it in the next couple of days."),
        _t(C, "You can pay through the usual net banking, the mobile app, or at any branch, whichever is convenient — there's no separate link or urgent action needed right this moment.",
            "Please pay via your regular banking app or branch as usual, I'm not sending any payment link, just wanted to make sure you're aware of the due amount."),
        _t(R, "Thanks for the reminder, I'll take care of it.",
            "Appreciate you letting me know, I'll sort it out."),
        _t(C, "Thank you, and do reach out if you're facing any difficulty, we do have restructuring options available if needed.",
            "No problem at all, and if there's a genuine hardship on your end, do call the branch, there are options to discuss."),
    ]),
}


def generate(n_per_scenario=120, seed=13):
    """Return unified-schema records (see schema.py), n per scenario, deterministic."""
    rng = random.Random(seed)
    records, seen = [], set()
    for scen_name, (scam_type, label, turns) in SCENARIOS.items():
        made, attempts = 0, 0
        while made < n_per_scenario and attempts < n_per_scenario * 30:
            attempts += 1
            fills = {k: rng.choice(v) for k, v in POOLS.items()}
            lines = []
            for speaker, alts in turns:
                text = rng.choice(alts).format(**fills)
                lines.append(f"{speaker}: {text}")
            transcript = " ".join(lines)
            if transcript in seen:
                continue
            seen.add(transcript)
            records.append({
                "id": f"kavach-india-synth-{scen_name}-{made}",
                "source": "kavach-india-synth",
                "text": transcript,
                "label": label,
                "scam_type": scam_type,
                "origin": "synthetic",
            })
            made += 1
    return records


if __name__ == "__main__":
    recs = generate()
    n_scam = sum(r["label"] for r in recs)
    print(f"generated {len(recs)} records ({n_scam} scam / {len(recs) - n_scam} legit)")
    print("scenarios:", len(SCENARIOS))
