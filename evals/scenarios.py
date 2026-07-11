"""Fresh, hand-written eval scenarios for Kavach — 15 scam + 15 benign call
transcripts, none copied or lightly reworded from data_pipeline/india_synth.py.
Written specifically to probe the text model + signature engine + fusion with
scenario *twists* the training/synthesis templates never saw (deepfake-style
family-emergency calls, mutual-fund KYC, FASTag phishing, task-job scams,
rental-deposit fraud, matrimonial-site advance fees, a second-victimization
"SEBI refund" trap, etc.) and with a few genuinely hard benign calls that
superficially resemble scam scripts (a real bank fraud-alert yes/no call, a
real refund callback, a friend asking to borrow money, a telemarketing pitch)
so the evaluation isn't just measuring "does it fire on the word refund".

Schema per record: {id, label, scam_type, description, transcript}
  - label: 1 = scam, 0 = benign
  - scam_type: tag from data_pipeline/schema.py's TAXONOMY (best-fit; "none"
    or "unknown_scam" used where no category fits cleanly)
  - transcript: "Caller: ... Receiver: ..." turns, matching the format the
    backend's text model and signature engine expect.

3 scam + 2 benign scenarios below use natural Hinglish code-mixing (flagged
in their `description`).
"""

SCAM_SCENARIOS = [
    {
        "id": "scam-deepfake-grandchild-emergency",
        "label": 1,
        "scam_type": "unknown_scam",
        "description": (
            "AI-cloned/impersonated grandchild voice, accident-abroad emergency, "
            "urgent money + secrecy demand. Hinglish code-mixing."
        ),
        "transcript": (
            "Caller: Nani, nani please listen to me, it's me, everything happened so fast. "
            "Receiver: Beta? Is that you? Your voice sounds strange, thoda different lag raha hai. "
            "Caller: Nani main hi hoon, please, I got into an accident here in Dubai, my phone broke, I'm calling from a stranger's number. "
            "Receiver: Accident?! Are you hurt? Where are you, I'll call your mother right now. "
            "Caller: No no, please don't call mama, she'll panic and I don't want her stressed, please, I'm begging you, just help me first. "
            "Caller: The hospital won't release me until the bill is cleared, it's only 45,000 rupees, my friend Rohan is with me, he'll share his account number. "
            "Receiver: But beta why does your voice keep breaking up like that... "
            "Caller: Bad network here nani, please hurry, they are asking us to pay in the next twenty minutes or they will call the local police about an unpaid bill. "
            "Receiver: Okay okay, don't worry, tell me the account details, I'm getting my passbook. "
            "Caller: Please don't tell papa or anyone right now, I'll explain everything once I'm out, just trust me this one time."
        ),
    },
    {
        "id": "scam-mutual-fund-kyc-lockout",
        "label": 1,
        "scam_type": "investment_scam",
        "description": "Fake mutual-fund RTA claiming folio KYC lapsed; pushes app install + PAN/OTP.",
        "transcript": (
            "Caller: Good afternoon, I'm calling from the Investor Services desk regarding your mutual fund folio ending 7734. "
            "Receiver: Yes, what's the issue? "
            "Caller: As per the new SEBI KYC validation rules that came into effect this quarter, your folio has been flagged as non-compliant and all future redemptions are on hold. "
            "Receiver: Nobody told me about this. What do I need to do? "
            "Caller: It's a simple two-minute re-validation, ma'am. I'll need you to confirm your PAN number and the code that will arrive on your registered mobile in the next moment. "
            "Receiver: A code? For KYC? That seems unusual. "
            "Caller: This is just our internal OTP-based identity check, it's standard across all AMCs now. If it isn't completed before end of day, your folio gets permanently frozen and your existing units may be forfeited under the new circular. "
            "Receiver: Forfeited? That's my retirement savings in there. "
            "Caller: Exactly why I'm trying to help you avoid that, ma'am. Also install our verification app, Folio-Connect, from the link I'm sending — it lets our backend team confirm the KYC instantly. "
            "Receiver: I don't think I've heard of that app. "
            "Caller: It's used internally, ma'am, please don't mention this call to your relationship manager, this channel is a priority fast-track and we don't want it flooded with other requests."
        ),
    },
    {
        "id": "scam-gas-connection-disconnection",
        "label": 1,
        "scam_type": "unknown_scam",
        "description": (
            "Fake LPG gas agency safety-audit disconnection threat with a paid link. "
            "Hinglish code-mixing."
        ),
        "transcript": (
            "Caller: Namaste ji, main aapke gas agency se bol raha hoon, aapka connection number match nahi kar raha hai hamare naye safety audit mein. "
            "Receiver: Safety audit? Humein toh kuch bataya nahi gaya. "
            "Caller: Sabko bata rahe hain madam, har cylinder holder ko iss hafte apna Aadhaar-linked verification complete karna hai, warna aapka gas connection aaj hi disconnect ho jayega. "
            "Receiver: Disconnect? But I just got a refill last week. "
            "Caller: That doesn't matter ma'am, this is a mandatory subsidy re-verification. I'm sending a link on this number right now, just open it and pay the 149 rupee verification charge to lock your slot before 6 PM. "
            "Receiver: Why would verification need a payment? "
            "Caller: It's a processing charge for the digital safety certificate, ma'am, without it the delivery boy will not be authorized to refill your cylinder in future ever again. "
            "Receiver: This is very sudden, let me call the agency office directly. "
            "Caller: Ma'am please don't waste time, the office lines are jammed today because of this new circular, just click the link now, I'm holding your slot for the next ten minutes only."
        ),
    },
    {
        "id": "scam-traffic-challan-payment-link",
        "label": 1,
        "scam_type": "govt_impersonation",
        "description": "Fake traffic-enforcement e-challan call pressuring an off-portal payment link before licence suspension.",
        "transcript": (
            "Caller: Good morning, this is Traffic Enforcement Cell calling regarding an e-challan issued against your vehicle registration. "
            "Receiver: A challan? For what? "
            "Caller: Signal jump captured on camera last month, sir. The fine is 1,500 rupees but since it wasn't settled within the deadline, it has now been escalated to the regional court and your driving licence is scheduled for suspension in 24 hours. "
            "Receiver: Nobody sent me any challan notice. "
            "Caller: It would have gone to your registered address, sir, but to save you the court visit, I can settle it right now on this call — I'm sending you a payment link over SMS, just complete it in the next few minutes before the file moves to the magistrate. "
            "Receiver: Shouldn't I pay through the official Parivahan website? "
            "Caller: That portal is down for maintenance today, sir, this is our department's temporary collection link, fully authorized, and it closes the case immediately so there's no complication with your licence renewal. "
            "Receiver: This really feels rushed. "
            "Caller: Sir, court cases are not something to delay, click the link, enter your card details, and I'll mark the challan cleared on my end right now."
        ),
    },
    {
        "id": "scam-insurance-bonus-unlock-fee",
        "label": 1,
        "scam_type": "prize_scam",
        "description": "Fake 'lapsed policy loyalty bonus' unlock scam demanding an upfront processing fee.",
        "transcript": (
            "Caller: Sir, I'm calling from the policyholder bonus cell regarding your old LIC policy that lapsed a few years back. "
            "Receiver: I don't really remember which policy you mean. "
            "Caller: It's the one you took around 2016, sir, it has accumulated a loyalty bonus of 1 lakh 20 thousand rupees that IRDAI has approved for release to policyholders like you this quarter. "
            "Receiver: Really? Nobody ever mentioned a bonus. "
            "Caller: Most people don't know, sir, that's exactly why we're calling — but to release the amount, there's a one-time GST and administrative charge of 3,500 rupees that needs to be paid before the disbursal file is closed today. "
            "Receiver: Why would I need to pay to receive my own bonus? "
            "Caller: It's a government-mandated processing charge, sir, every insurance payout above 1 lakh has this rule now. If you don't complete it today, the file goes back into the pending queue for another six months. "
            "Receiver: That seems odd for an insurance company. "
            "Caller: Sir, this window closes at 5 PM, I have forty other policyholders waiting, please just make the payment on the UPI ID I'm sending you now so I can confirm your bonus release immediately."
        ),
    },
    {
        "id": "scam-income-tax-fake-notice",
        "label": 1,
        "scam_type": "govt_impersonation",
        "description": "Fake IT-department scrutiny-notice/raid threat with a 'compounding fee' payoff — no 'digital arrest' wording, different flavor of authority impersonation.",
        "transcript": (
            "Caller: This is Deputy Commissioner Malhotra from the Income Tax Investigation Wing. I'm calling about a scrutiny notice under your PAN. "
            "Receiver: A notice? I haven't received anything by post. "
            "Caller: This came up in our system flag for undeclared foreign remittance of 8 lakh rupees linked to your PAN. A search team has already been assigned to your address for tomorrow morning. "
            "Receiver: That's impossible, I've never had any foreign transactions. "
            "Caller: That is exactly what the system flagged, sir, which is why I'm giving you a chance to resolve this before the search team is dispatched. You can avoid the raid by paying a compounding fee today so the case is closed administratively instead of criminally. "
            "Receiver: This sounds very serious, shouldn't I speak to a chartered accountant first? "
            "Caller: Sir, there's no time for that, once the search team leaves headquarters I cannot recall them. Just transfer the compounding fee of 60,000 rupees to the department's clearance account I'm sending you, and I'll mark this file settled on my end. "
            "Receiver: I really don't feel comfortable doing this over a phone call. "
            "Caller: I understand your hesitation, sir, but please don't discuss this with anyone until it's resolved, tax matters are strictly confidential until closure — I need your decision in the next ten minutes."
        ),
    },
    {
        "id": "scam-fake-job-advance-fee",
        "label": 1,
        "scam_type": "unknown_scam",
        "description": (
            "Work-from-home data-entry job offer requiring an upfront 'registration kit' fee. "
            "Hinglish code-mixing."
        ),
        "transcript": (
            "Caller: Hi, congratulations! Aapka resume humari HR team ne shortlist kiya hai for our part-time data entry program, work from home, sirf 2-3 hours daily. "
            "Receiver: Oh nice, which company is this? "
            "Caller: Ye ek outsourcing firm hai jo Amazon aur Flipkart ke liye product listing ka kaam karti hai, payment daily 800 se 1500 rupees tak. "
            "Receiver: Sounds interesting, what do I need to do? "
            "Caller: Bas ek chhota sa registration kit lena padta hai, 999 rupees ka, usme aapka training material aur login ID milega, ye fully refundable hai first week ki salary ke saath. "
            "Receiver: Refundable, are you sure? I've heard of scams like this before. "
            "Caller: Bilkul sir, humare paas hazaron log already kaam kar rahe hain, aap Google pe hamari company ka naam bhi search kar sakte hain, lekin abhi registration slot sirf aaj tak open hai, kal se naye batch ka rate badh jayega. "
            "Receiver: Let me think about it and call back tomorrow. "
            "Caller: Sir slot limited hai, agar aaj shaam tak payment nahi hua toh aapka naam waiting list mein chala jayega aur phir agla batch next month hi khulega."
        ),
    },
    {
        "id": "scam-telegram-task-scam",
        "label": 1,
        "scam_type": "investment_scam",
        "description": "'Like and earn' Telegram task job pivoting into a wallet-deposit-to-unlock investment trap.",
        "transcript": (
            "Caller: Hello ma'am, I'm following up on the YouTube-like task job you signed up for on our Telegram channel yesterday. "
            "Receiver: Yes, I liked a few videos and got paid 50 rupees, that was nice. "
            "Caller: Great, you're doing well! Now you're eligible for our premium task batch, where each task pays 300 to 500 rupees instead of 10. "
            "Receiver: Oh wow, what do I need to do differently? "
            "Caller: For the premium batch, you first need to add 2,000 rupees to your task wallet inside our app — this unlocks higher-value tasks and the money plus your earnings can be withdrawn together at the end of the day. "
            "Receiver: Wait, so I have to put my own money in first? "
            "Caller: Yes ma'am, it's just to activate the batch, thousands of members are already earning 3-4 thousand daily this way, I can send you screenshots of other members' withdrawals if you want proof. "
            "Receiver: I don't know, this feels like it's turning into something else. "
            "Caller: It's completely safe ma'am, and if you deposit before the batch closes in fifteen minutes, we'll also add a 10% bonus to your wallet — but the offer resets every hour so I'd suggest deciding quickly."
        ),
    },
    {
        "id": "scam-sim-ekyc-whatsapp-link",
        "label": 1,
        "scam_type": "unknown_scam",
        "description": "Fake telecom SIM e-KYC deactivation threat, tricking the receiver into reading out an OTP framed as a 'telecom code'.",
        "transcript": (
            "Caller: Sir, this is a courtesy call from your telecom provider's compliance department regarding SIM re-verification. "
            "Receiver: Re-verification? I already did my KYC when I bought the SIM. "
            "Caller: As per the latest TRAI directive, all SIMs older than two years need a fresh digital e-KYC, otherwise the number gets deactivated within 24 hours for regulatory non-compliance. "
            "Receiver: Nobody mentioned this rule to me before. "
            "Caller: It rolled out this month, sir, that's why we're proactively calling eligible customers. I've just sent a link on WhatsApp — please open it, it will trigger a verification code to this same number. "
            "Receiver: Okay, I see a message just came in with a six digit code. "
            "Caller: Perfect sir, please read that code out to me so I can complete the e-KYC linking on our system before the deactivation job runs tonight. "
            "Receiver: Isn't the code supposed to stay private? "
            "Caller: Only for banking OTPs, sir, this is a telecom verification code, completely different — read it out quickly, the deactivation batch runs at midnight sharp and I can't stop it once it starts."
        ),
    },
    {
        "id": "scam-matrimonial-premium-unlock",
        "label": 1,
        "scam_type": "unknown_scam",
        "description": "Matrimonial-site 'relationship manager' demanding a premium-unlock fee to reveal a match's contact details.",
        "transcript": (
            "Caller: Good evening, I'm calling from the matrimony platform regarding your profile, we've found an excellent match for you. "
            "Receiver: Oh really, tell me more. "
            "Caller: She's a doctor, verified profile, based in Pune, and she has already shown interest after seeing your profile photo. "
            "Receiver: That's great, can you share her contact number? "
            "Caller: I can, but her contact details are locked under our premium membership, sir, which needs to be activated with a one-time payment of 5,999 rupees. "
            "Receiver: I thought I already had a paid account. "
            "Caller: Your basic plan doesn't include verified premium matches, sir, this is a separate tier. And I should mention, three other members have already requested to view her profile today, so slots are limited. "
            "Receiver: Let me think about it, I don't want to rush into paying more. "
            "Caller: Sir, if you don't upgrade in the next hour, her profile moves to the other interested members and you'll lose this match completely, this is honestly a rare opportunity given her profile score."
        ),
    },
    {
        "id": "scam-fastag-recharge-phishing",
        "label": 1,
        "scam_type": "bank_fraud",
        "description": "FASTag KYC/recharge-failure phishing scam ending in a card-number, expiry, and OTP request.",
        "transcript": (
            "Caller: Hello, this is regarding your FASTag account, your last recharge attempt of 500 rupees failed due to incomplete KYC. "
            "Receiver: I didn't try to recharge my FASTag recently. "
            "Caller: Our system shows an auto-debit attempt this morning, sir, and because the KYC is incomplete, your tag will be blacklisted at the next toll plaza, which means double penalty charges. "
            "Receiver: That would be a problem, I drive through toll booths every day for work. "
            "Caller: Exactly why I'm calling, sir, I've sent you a secure link to complete the KYC and recharge in one step — just enter your card number and expiry date there, and confirm the OTP that arrives to finalize it. "
            "Receiver: Do I really need to give my card number for this? "
            "Caller: Yes sir, that's how the recharge gateway verifies the linked account, without it the tag stays blacklisted starting tomorrow, and NHAI toll plazas don't accept cash anymore at the FASTag lane. "
            "Receiver: Okay, let me open the link. "
            "Caller: Take your time sir, but please complete it before midnight, after that the blacklist entry becomes permanent for thirty days."
        ),
    },
    {
        "id": "scam-sebi-refund-previous-victims",
        "label": 1,
        "scam_type": "refund_scam",
        "description": "Second-victimization scam: a fake 'SEBI recovery cell' promises to refund a past trading-app loss, for an upfront processing tax.",
        "transcript": (
            "Caller: Am I speaking with someone who lost money in an online trading app around eight months back? "
            "Receiver: Yes... how do you know that? "
            "Caller: We're a SEBI-appointed grievance and recovery cell set up specifically for victims of fraudulent trading platforms. Your case came up in our recovered database. "
            "Receiver: Recovered database? What does that mean for me? "
            "Caller: It means we've successfully traced part of the funds from the fraudulent operator and your name is on the list eligible for a partial refund of 85,000 rupees. "
            "Receiver: That's almost exactly what I lost. This is unbelievable. "
            "Caller: I understand it's a relief, ma'am, but before we can release it, there's a mandatory refund-processing tax of 4,200 rupees that SEBI requires — this is standard for all recovery cases above 50,000 rupees. "
            "Receiver: I already lost money once, I'm nervous about paying anything again. "
            "Caller: That's a fair concern, ma'am, but this is a government-mandated fee, not a company charge, and if it isn't paid within 24 hours, your case gets reassigned to next quarter's recovery batch — meaning another six-month wait. "
            "Receiver: Okay... where do I send the payment?"
        ),
    },
    {
        "id": "scam-new-number-parent-whatsapp",
        "label": 1,
        "scam_type": "unknown_scam",
        "description": "'Hi mum, new number' text-to-call bridge scam asking the parent to pay a landlord bill on the child's behalf.",
        "transcript": (
            "Caller: Mumma, hi, it's me, I dropped my old phone in the toilet yesterday, this is a temporary number I borrowed from a colleague. "
            "Receiver: Oh no, are you okay? Why didn't you call from your office landline? "
            "Caller: I'm fine, just really stressed, my new SIM hasn't activated banking apps yet and I have an urgent payment due today for my landlord, otherwise he's going to charge a late penalty. "
            "Receiver: How much do you need? "
            "Caller: It's only 18,500 rupees, can you UPI it directly to my landlord's account, I'll send you the UPI ID right now and pay you back the moment my bank app starts working again. "
            "Receiver: Okay, but let me just call your regular number to double check. "
            "Caller: Please don't, mumma, that phone is with the repair shop and if anyone answers it might be a stranger, just trust me and send it fast, my landlord is literally waiting on the other line. "
            "Receiver: Alright, sending it now, let me know when your old number is back. "
            "Caller: Will do, thank you so much, and please don't mention this to papa, he'll just lecture me about phone insurance again."
        ),
    },
    {
        "id": "scam-credit-card-limit-upgrade-otp",
        "label": 1,
        "scam_type": "bank_fraud",
        "description": "'Pre-approved credit limit upgrade' reward-framed scam asking for CVV and an activation OTP.",
        "transcript": (
            "Caller: Good afternoon, congratulations, your credit card has been pre-approved for a limit upgrade to 3 lakh rupees based on your excellent repayment history. "
            "Receiver: Oh, that's good news, how does it work? "
            "Caller: It's instant, sir, I just need to verify your card details on our side and then activate it through your registered mobile. "
            "Receiver: What kind of verification exactly? "
            "Caller: Just your card number, the expiry date printed on the front, and the CVV at the back for our system to match records — then a confirmation code will arrive which finalizes the upgrade. "
            "Receiver: I thought CVV wasn't supposed to be shared with anyone. "
            "Caller: That rule is for online shopping websites, sir, this is our internal bank verification line, completely different process, fully secure on our end. "
            "Receiver: Let me just check with my branch first. "
            "Caller: Sir, this offer window is only valid for the next fifteen minutes since it's tied to today's batch processing, if it lapses you'll have to reapply from scratch and wait 90 days again. "
            "Receiver: Okay, the card number is... and the CVV is... "
            "Caller: Perfect sir, now the code that just came to your phone, please read that out so I can complete the activation."
        ),
    },
    {
        "id": "scam-rental-deposit-token-advance",
        "label": 1,
        "scam_type": "unknown_scam",
        "description": "Property-rental broker scam demanding a 'token advance' to hold a flat viewing slot before ever showing the flat.",
        "transcript": (
            "Caller: Hi, I'm calling about the 2BHK flat you enquired about on the rental listing site, near the tech park. "
            "Receiver: Yes, I saw it, the rent looked quite reasonable for that location. "
            "Caller: It's owned by an NRI client currently abroad, that's why it's priced lower than the market rate, but I've had six other calls about it just this morning. "
            "Receiver: Can I come see the flat this weekend? "
            "Caller: Of course, but honestly it will be gone by then, sir, this is one of the fastest-moving listings we have. If you're serious, I'd suggest sending a token advance of 5,000 rupees right now to block the slot, and I'll personally hold the viewing exclusively for you on Saturday. "
            "Receiver: I'd rather see it before paying anything. "
            "Caller: I completely understand, sir, but the owner has instructed us to only reserve viewings for token-paid candidates because too many people were wasting his caretaker's time. It's fully adjustable against your deposit later. "
            "Receiver: This still feels a bit backwards to pay before seeing the place. "
            "Caller: I get a lot of hesitant clients, sir, but I've closed twenty deals this way already this month, and if you don't decide in the next hour, I'll have to offer the slot to the next person in queue."
        ),
    },
]

BENIGN_SCENARIOS = [
    {
        "id": "benign-bank-fraud-alert-yes-no",
        "label": 0,
        "scam_type": "banking_legit",
        "description": "Real bank fraud-prevention call that only asks a yes/no confirmation — no OTP, PIN, or link, ever.",
        "transcript": (
            "Caller: Hello, this is the fraud prevention team from your bank, am I speaking with the cardholder on account ending 2291? "
            "Receiver: Yes, that's me. "
            "Caller: We've flagged a transaction of 42,999 rupees at an electronics store in Bangkok about ten minutes ago. Did you authorize this purchase? "
            "Receiver: No, I haven't left the country, I didn't make that. "
            "Caller: Understood, thank you for confirming. We're blocking the card right now and reversing that transaction. You do not need to share your card number, PIN, or any OTP with me for this — I just needed your yes or no. "
            "Receiver: Okay, that's a relief. What happens next? "
            "Caller: A new card will be couriered to your registered address within five to seven working days. If you ever want to double check a call like this is genuine, you can hang up and call the number on the back of your card directly. "
            "Receiver: Thank you so much for catching this quickly. "
            "Caller: That's what we're here for. Is there anything else flagged you'd like me to walk through? "
            "Receiver: No, that covers it, thanks again."
        ),
    },
    {
        "id": "benign-police-passport-verification",
        "label": 0,
        "scam_type": "none",
        "description": "Genuine local police call scheduling the standard in-person passport address verification — no fee, no threats.",
        "transcript": (
            "Caller: Good morning, I'm calling from the local police station regarding your passport application, we need to do the address verification. "
            "Receiver: Yes, I was told this would happen after I applied. "
            "Caller: Correct, sir. I'd like to schedule a home visit for the verification, would tomorrow between 11 and 1 work for you? "
            "Receiver: Yes, I should be home then. What do I need to keep ready? "
            "Caller: Please keep your original Aadhaar card, a recent utility bill, and the passport application receipt ready for the constable to see and note down. "
            "Receiver: Is there any fee for this verification? "
            "Caller: No, sir, this verification is part of the standard process and there's no fee involved, it's covered under your application charges already paid to the passport office. "
            "Receiver: Understood, I'll make sure someone is home tomorrow. "
            "Caller: Thank you, sir. The constable will just check your documents and take a photo of your residence for the record, it takes about ten minutes. "
            "Receiver: Sounds simple enough, see you tomorrow then."
        ),
    },
    {
        "id": "benign-friend-borrow-money",
        "label": 0,
        "scam_type": "personal",
        "description": (
            "A real friend asking to borrow money for a father's medical bill — no pressure tactics, no "
            "secrecy demand, natural back-and-forth. Hinglish code-mixing."
        ),
        "transcript": (
            "Caller: Arre yaar, kaise ho? Ek chhota sa favor chahiye tha tumse. "
            "Receiver: Bol na, sab thik toh hai? "
            "Caller: Papa ko achanak hospital le jana pada kal raat, kuch tests ke paise abhi turant chahiye, around 15,000 rupees, agle hafte salary aate hi laut dunga. "
            "Receiver: Arre koi baat nahi, itni si baat ke liye tension mat le. Kaise hai uncle ab? "
            "Caller: Ab thoda better hai, doctors bol rahe hain kal tak discharge ho sakta hai. Thank you yaar, tumhe pata hai main jaldi hi wapas kar dunga. "
            "Receiver: Chill kar, family hai apni, koi jaldi nahi hai wapas karne ki. Bata UPI ID de deta hoon abhi. "
            "Caller: Bas mera regular number wala UPI hi hai, wahi bhej dena, aur agar time mile toh ek baar call karke uncle se baat kar lena, unko accha lagega. "
            "Receiver: Zaroor karunga, tu bas apna khayal rakh, main abhi bhejta hoon."
        ),
    },
    {
        "id": "benign-customer-care-callback-requested",
        "label": 0,
        "scam_type": "none",
        "description": "Legitimate telecom customer-care callback the user themselves requested, resolving a real billing complaint.",
        "transcript": (
            "Caller: Hello, this is customer support calling back regarding the billing complaint you raised yesterday, ticket number 88213456. "
            "Receiver: Oh yes, I requested this callback for around this time, thanks for calling. "
            "Caller: Of course. I've reviewed your case — you were charged twice for the same recharge due to a payment gateway glitch on our end. "
            "Receiver: Yes exactly, that's what happened, I have both the transaction messages. "
            "Caller: I can see both entries on our system too. I've processed a refund for the duplicate charge, it should reflect in your account within 3 to 5 business days. "
            "Receiver: That's great, thank you for sorting it out. "
            "Caller: You're welcome. Do you want me to email you the refund confirmation as well for your records? "
            "Receiver: Yes please, that would be helpful. "
            "Caller: Done, you'll receive it in the next few minutes. Is there anything else I can help you with today? "
            "Receiver: No, that's everything, thanks again for the quick callback."
        ),
    },
    {
        "id": "benign-telemarketing-insurance-pitch",
        "label": 0,
        "scam_type": "telemarketing",
        "description": "Ordinary, slightly pushy but legitimate telemarketing pitch for a term insurance plan — no threats, no guarantees, easy opt-out.",
        "transcript": (
            "Caller: Good afternoon, I'm calling from a life insurance provider regarding a term plan that might interest you given your age group. "
            "Receiver: I already have a term policy actually, but go ahead. "
            "Caller: No problem at all, this one offers a slightly higher cover for a similar premium, about 1 crore cover for around 700 rupees a month if you're a non-smoker. "
            "Receiver: That is a decent rate. What's the catch? "
            "Caller: No catch, sir, it's a standard online term plan, medical tests may be required depending on the cover amount, and you can compare it with your existing policy at your own pace. "
            "Receiver: I'll need to think about it, I'm not in a rush to decide today. "
            "Caller: Absolutely, take your time. Would it be okay if I email you the brochure and follow up next week instead of calling again today? "
            "Receiver: Yes, that works, please email it. "
            "Caller: Great, I'll send that over shortly. Thanks for your time, and have a good day. "
            "Receiver: You too, thanks for calling."
        ),
    },
    {
        "id": "benign-pta-meeting-reminder",
        "label": 0,
        "scam_type": "appointment",
        "description": "Routine school call reminding a parent of the parent-teacher meeting slot.",
        "transcript": (
            "Caller: Good evening, this is calling from your child's school regarding the parent-teacher meeting this Saturday. "
            "Receiver: Yes, I saw the note in the diary. What time is it again? "
            "Caller: It starts at 9 AM sharp, class-wise slots have been assigned, yours is at 10:15 with the class teacher. "
            "Receiver: Got it, I'll be there by 10. "
            "Caller: Great, please bring the last term's report card if you have it handy, it helps the discussion go faster. "
            "Receiver: Sure, I'll dig that out tonight. "
            "Caller: Wonderful. If anything changes and you can't make it, just let the school office know and we can reschedule. "
            "Receiver: Will do, thank you for the reminder call. "
            "Caller: You're welcome, see you Saturday."
        ),
    },
    {
        "id": "benign-landlord-maintenance-call",
        "label": 0,
        "scam_type": "none",
        "description": "Everyday landlord call about a plumbing fix and the regular monthly rent date.",
        "transcript": (
            "Caller: Hi, it's your landlord here, just wanted to check if the plumber I sent last week actually fixed that kitchen leak properly. "
            "Receiver: Yes, he sorted it out, no more dripping since then. "
            "Caller: Good to hear. Also just a reminder, rent is due on the 5th as usual, same account as always. "
            "Receiver: Yes, I'll transfer it like every month, no changes there right? "
            "Caller: No changes, same account. Also, I might send the society plumber again next month for the annual pipe check, I'll let you know the date in advance. "
            "Receiver: Sounds good, just give me a day's notice so I can be home. "
            "Caller: Will do. Anything else on your end that needs fixing? "
            "Receiver: Not right now, everything else is fine. Thanks for following up. "
            "Caller: No problem, take care."
        ),
    },
    {
        "id": "benign-gym-membership-renewal",
        "label": 0,
        "scam_type": "telemarketing",
        "description": "Low-pressure gym front-desk call about an expiring membership and a modest early-renewal discount.",
        "transcript": (
            "Caller: Hi, this is calling from the front desk at your gym, just letting you know your annual membership expires at the end of this month. "
            "Receiver: Oh right, I hadn't checked, thanks for the heads up. "
            "Caller: No problem. If you renew before the 25th, there's a small early-renewal discount, about 10 percent off the annual fee. "
            "Receiver: That's a nice bonus, what's the total with the discount? "
            "Caller: It comes to around 9,000 rupees for the year instead of 10,000, payable at the counter or through the app whenever you're free. "
            "Receiver: I'll drop by this weekend and sort it out then. "
            "Caller: Sounds good, no rush at all, the discount is valid until the 25th so you've got time. "
            "Receiver: Perfect, see you this weekend. "
            "Caller: See you then, have a good workout today."
        ),
    },
    {
        "id": "benign-rwa-maintenance-fee-call",
        "label": 0,
        "scam_type": "none",
        "description": "Routine housing-society maintenance-dues reminder and general-body meeting notice.",
        "transcript": (
            "Caller: Hello, this is from the residents' welfare association, calling about this quarter's maintenance dues. "
            "Receiver: Yes, I think I'm slightly behind on that, sorry, been busy. "
            "Caller: No worries, it's 3,200 rupees for this quarter, you can pay it the same way as always, either at the office or through the society app. "
            "Receiver: I'll clear it this week through the app. "
            "Caller: Perfect, thank you. Also wanted to remind you there's a general body meeting this Sunday evening in the clubhouse to discuss the new parking rules. "
            "Receiver: Oh I saw the notice on the board, I'll try to attend. "
            "Caller: Great, your input would help, quite a few residents have opinions on the visitor parking changes. "
            "Receiver: Understood, I'll be there if I can make it. "
            "Caller: Thanks, and don't forget the dues whenever convenient, no rush on that either. "
            "Receiver: Will do, thanks for calling."
        ),
    },
    {
        "id": "benign-furniture-delivery-address-confirm",
        "label": 0,
        "scam_type": "delivery",
        "description": "Furniture-store delivery coordinator confirming address and time slot — payment only in person at delivery, no OTP.",
        "transcript": (
            "Caller: Hi, calling regarding the dining table you ordered from us last week, we wanted to confirm the delivery address before dispatch. "
            "Receiver: Yes, sure, go ahead. "
            "Caller: I have it as flat 402, Lotus Residency, near the main market — is that correct? "
            "Receiver: That's right, but the gate is easier to find from the back lane, I can share a pin location if that helps. "
            "Caller: That would be great, please share it on this number after the call. Also, would tomorrow afternoon or the day after work better for delivery? "
            "Receiver: Tomorrow afternoon works fine for me. "
            "Caller: Perfect, I'll book you in for tomorrow between 2 and 5 PM. The delivery team will call you about half an hour before arriving. "
            "Receiver: Sounds good, I'll keep the phone handy. "
            "Caller: Great, and just a reminder, the balance amount can be paid to the delivery team directly by card, cash, or UPI once the table is set up and you're satisfied. "
            "Receiver: Understood, thanks for confirming everything."
        ),
    },
    {
        "id": "benign-college-friend-reunion-call",
        "label": 0,
        "scam_type": "personal",
        "description": (
            "Old college friend catching up and proposing a reunion trip — purely social, no money involved. "
            "Hinglish code-mixing."
        ),
        "transcript": (
            "Caller: Oye, pehchana kya, itne saalon baad call kar raha hoon! "
            "Receiver: Arre yaar, kaise bhool sakta hoon tumhari awaaz, kaisa hai sab? "
            "Caller: Sab badhiya hai, bas kaam mein busy tha, tabhi itna time nikal nahi paya. Suna hai batch ke kuch log reunion plan kar rahe hain? "
            "Receiver: Haan yaar, group mein baat ho rahi thi, Goa ya Manali, abhi decide nahi hua. "
            "Caller: Mujhe bhi include kar lena, main December mein free rahunga, jo bhi dates decide ho, bata dena. "
            "Receiver: Zaroor, main tujhe group mein add kar deta hoon, sab log excited hain milne ke liye. "
            "Caller: Perfect, aur suna tera naya ghar kaisa chal raha hai, shift ho gaye poori tarah? "
            "Receiver: Haan bas thoda saaman set karna baaki hai, aa jaana kabhi, chai pi kar jaana. "
            "Caller: Zaroor aaunga, chalo phir milte hain jald hi, group mein active rehna."
        ),
    },
    {
        "id": "benign-vaccination-reminder-call",
        "label": 0,
        "scam_type": "appointment",
        "description": "Pediatric clinic reminder call for a child's scheduled vaccination dose — routine, no fee pressure.",
        "transcript": (
            "Caller: Good morning, this is calling from Dr. Kapoor's pediatric clinic, just confirming your daughter's vaccination appointment this Friday. "
            "Receiver: Yes, I have it noted, it's the second dose right? "
            "Caller: That's right, at 4 PM. Please make sure she's had a light meal before coming, and bring the vaccination card so we can update it. "
            "Receiver: Will do, is there anything specific I should watch for after the shot? "
            "Caller: Mild fever or a bit of fussiness is normal for a day, the doctor will go over the details again at the visit and give you paracetamol dosage instructions if needed. "
            "Receiver: Sounds good, we'll be there by 4. "
            "Caller: Perfect, and if Friday doesn't work anymore for some reason, just call the clinic to reschedule, no issue at all. "
            "Receiver: Thanks for the reminder, appreciate it. "
            "Caller: Of course, see you both on Friday."
        ),
    },
    {
        "id": "benign-voter-id-update-camp",
        "label": 0,
        "scam_type": "none",
        "description": "Municipal ward-office announcement about a free voter-ID/Aadhaar update camp — informational, no fee.",
        "transcript": (
            "Caller: Good afternoon, this is an announcement call from the ward office regarding a voter list and Aadhaar update camp this weekend. "
            "Receiver: Oh okay, where is it being held? "
            "Caller: It's at the community hall near the ward office, open from 10 AM to 4 PM on both Saturday and Sunday. "
            "Receiver: What do I need to bring if I want to update my address on my voter ID? "
            "Caller: Just your existing voter ID card and a recent proof of address, like a utility bill or rent agreement, the volunteers will help you fill the form on the spot. "
            "Receiver: Is there any charge for this? "
            "Caller: No, it's completely free, run by the ward office and election commission volunteers, no charge at all. "
            "Receiver: Good to know, I'll try to drop by on Saturday morning. "
            "Caller: Sounds good, no appointment needed, just walk in anytime during those hours. "
            "Receiver: Thanks for letting us know."
        ),
    },
    {
        "id": "benign-rd-maturity-informational-call",
        "label": 0,
        "scam_type": "banking_legit",
        "description": "Bank relationship manager informing the customer their recurring deposit matured — no OTP, no urgency.",
        "transcript": (
            "Caller: Good morning, this is your relationship manager calling from the bank, your recurring deposit account is maturing next week. "
            "Receiver: Oh right, I'd almost forgotten about that one. "
            "Caller: It's matured to about 1 lakh 10 thousand rupees including interest. Would you like to renew it for another term, or should we credit it to your savings account? "
            "Receiver: What are the current interest rates looking like for a new term? "
            "Caller: For a 3-year RD it's around 7.1 percent right now, slightly better than what you started with two years ago. "
            "Receiver: That sounds decent, let me think about it over the weekend and let you know. "
            "Caller: No problem at all, take your time, the maturity amount will simply sit in your savings account until you decide either way. "
            "Receiver: Sounds good, I'll call the branch directly once I've decided. "
            "Caller: Perfect, feel free to call this same number too, I handle your account directly. Have a good day. "
            "Receiver: Thanks for letting me know, you too."
        ),
    },
    {
        "id": "benign-cab-driver-pickup-confirm",
        "label": 0,
        "scam_type": "none",
        "description": "Mundane cab-driver call confirming the exact pickup point — no financial or personal-data requests.",
        "transcript": (
            "Caller: Hello, I'm your driver for the cab you booked, just outside the main gate now, which side should I come to? "
            "Receiver: I'm near the coffee shop entrance, on the left side of the main gate. "
            "Caller: Got it, I see the coffee shop, give me two minutes, there's a bit of traffic near the roundabout. "
            "Receiver: No rush, I'm still finishing my coffee anyway. "
            "Caller: Great, I'm in a white sedan, last four of the plate are 7743, I'll flash my lights when I'm close. "
            "Receiver: Perfect, I'll keep an eye out. "
            "Caller: Almost there now, I can see the entrance. "
            "Receiver: I see you, coming out now."
        ),
    },
]

ALL_SCENARIOS = SCAM_SCENARIOS + BENIGN_SCENARIOS

assert len(SCAM_SCENARIOS) == 15, len(SCAM_SCENARIOS)
assert len(BENIGN_SCENARIOS) == 15, len(BENIGN_SCENARIOS)
assert all(s["label"] == 1 for s in SCAM_SCENARIOS)
assert all(s["label"] == 0 for s in BENIGN_SCENARIOS)
assert len({s["id"] for s in ALL_SCENARIOS}) == len(ALL_SCENARIOS), "duplicate scenario ids"


if __name__ == "__main__":
    print(f"{len(SCAM_SCENARIOS)} scam + {len(BENIGN_SCENARIOS)} benign = {len(ALL_SCENARIOS)} scenarios")
