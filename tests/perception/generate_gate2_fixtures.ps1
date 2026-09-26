# Development-only synthetic speech. Never label these as human recordings.
Add-Type -AssemblyName System.Speech

$fixtureDirectory = Join-Path $PSScriptRoot 'fixtures\gate2'
New-Item -ItemType Directory -Path $fixtureDirectory -Force | Out-Null

$voice = 'Microsoft Zira Desktop'
$fixtures = @(
    @{
        Name = 'correction.wav'
        Ssml = '<speak version="1.0" xml:lang="en-US"><voice name="Microsoft Zira Desktop">Book a repair appointment in the mock calendar for Tuesday September twenty ninth twenty twenty six at three P M. Tuesday at three.<break time="1400ms"/>Actually, Wednesday September thirtieth twenty twenty six at five P M, India Standard Time. Use only the final date and time.</voice></speak>'
    },
    @{
        Name = 'information.wav'
        Ssml = '<speak version="1.0" xml:lang="en-US"><voice name="Microsoft Zira Desktop">What is seventeen times nineteen? Please give the numerical answer and do not create a calendar event.</voice></speak>'
    }
)

foreach ($fixture in $fixtures) {
    $destination = Join-Path $fixtureDirectory $fixture.Name
    if (Test-Path -LiteralPath $destination) {
        throw "Refusing to overwrite existing fixture: $destination"
    }
    $synthesizer = [System.Speech.Synthesis.SpeechSynthesizer]::new()
    try {
        $synthesizer.SelectVoice($voice)
        $synthesizer.SetOutputToWaveFile($destination)
        $synthesizer.SpeakSsml($fixture.Ssml)
    }
    finally {
        $synthesizer.Dispose()
    }
    Get-FileHash -Algorithm SHA256 -LiteralPath $destination |
        Select-Object Path, Hash
}
