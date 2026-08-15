# Regenerates the demo call recordings used by DEMO_SCRIPT.md.
#
# The .wav files themselves are gitignored (binary, regenerable), so run this once
# before recording the demo:   powershell -File demo_assets\make_demo_audio.ps1
#
# Uses the Windows built-in speech synthesizer, so the voices are genuinely
# synthetic -- which is the point: the voice-forensics model should score them
# as AI-generated. That is also why the benign sample is a useful test, since a
# synthetic voice alone must NOT be enough to declare a call a scam.

Add-Type -AssemblyName System.Speech

function New-DemoClip {
    param([string]$Voice, [string]$Path, [string]$Text)
    $synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
    try {
        $synth.SelectVoice($Voice)
    } catch {
        Write-Warning "Voice '$Voice' unavailable; using the system default."
    }
    $synth.SetOutputToWaveFile($Path)
    $synth.Speak($Text)
    $synth.Dispose()
    Write-Host "wrote $Path"
}

$here = Split-Path -Parent $MyInvocation.MyCommand.Path

New-DemoClip -Voice 'Microsoft David Desktop' -Path "$here\demo_scam_call_short.wav" -Text @'
This is Inspector Sharma from the Cyber Crime Cell. Your Aadhaar number is linked to a
money laundering case, and you are now under digital arrest. Do not disconnect, and do not
tell anyone, not even your family. Transfer your balance to the R B I verification account
now, and read me the O T P sent to your phone.
'@

New-DemoClip -Voice 'Microsoft Zira Desktop' -Path "$here\demo_benign_call.wav" -Text @'
Good morning, this is Ritu calling from Apollo Clinic. I am calling to confirm your health
checkup appointment with Doctor Mehta on Friday at eleven A M. Please carry your previous
reports with you. The consultation fee can be paid at the reception by cash or card. If you
need to reschedule, just call this number back. Thank you and have a good day.
'@

Write-Host ""
Write-Host "Expected results when uploaded to POST /analyze/recording:"
Write-Host "  demo_scam_call_short.wav -> risk ~1.00  'high'        (4 signature hits)"
Write-Host "  demo_benign_call.wav     -> risk ~0.55  'suspicious'  (0 hits; synthetic voice only)"
