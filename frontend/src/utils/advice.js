// Very short, plain-language one-liners for elderly mode's simplified view.
export function oneLineAdvice(level) {
  switch (level) {
    case 'high':
      return 'Hang up now. Do not share any OTP, PIN or make any payment.';
    case 'suspicious':
      return 'Be careful. Do not share OTP or pay until you confirm independently.';
    default:
      return 'This call looks safe so far. Stay alert if anything changes.';
  }
}
