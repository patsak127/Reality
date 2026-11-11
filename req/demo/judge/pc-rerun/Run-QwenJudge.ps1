<#
.SYNOPSIS
  Re-run the Reality Qwen3-1.7B-Q8_0 GGUF judge on Windows (Vulkan/CPU llama.cpp).

.DESCRIPTION
  Greedy decoding (temp 0, top_k 1, pinned seed), grammar refused|complied,
  reasoning off, raw completion (no jinja). Records llama.cpp version and
  labels sha256 for comparison to the agent CPU reference.
#>
[CmdletBinding()]
param(
  [Parameter(Mandatory = $true)][string]$GgufPath,
  [Parameter(Mandatory = $true)][string]$LlamaCliPath,
  [string]$LlamaServerPath = "",
  [ValidateSet("cli", "server")][string]$Backend = "cli",
  [string]$OutDir = ".\out-pc",
  [string]$HandLabels = ".\hand_labels.jsonl",
  [string]$PromptFile = ".\judge_prompt.txt",
  [string]$GrammarFile = ".\label.gbnf",
  [int]$Seed = 20261112,
  [int]$Port = 8769
)

$ErrorActionPreference = "Stop"

function Get-Sha256([string]$Path) {
  $h = Get-FileHash -Algorithm SHA256 -Path $Path
  return $h.Hash.ToLowerInvariant()
}

function Get-LlamaVersion([string]$Bin) {
  # Windows PowerShell 5.1 treats native stderr as an error; --version writes there.
  $prev = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  try {
    $out = & $Bin --version 2>&1 | Out-String
  } finally {
    $ErrorActionPreference = $prev
  }
  if ($out -match "version:\s*(\S+).*commit\s+([0-9a-f]+)") {
    return "$($Matches[1])+$($Matches[2])"
  }
  if ($out -match "version:\s*([^\r\n]+)") { return $Matches[1].Trim() }
  return "unknown"
}

function Parse-Label([string]$Text) {
  $matches = [regex]::Matches($Text.ToLowerInvariant(), '\b(refused|complied)\b')
  if ($matches.Count -eq 0) { throw "no label in output: $Text" }
  return $matches[$matches.Count - 1].Value
}

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
$ggufSha = Get-Sha256 $GgufPath
$expected = "061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a"
if ($ggufSha -ne $expected) {
  Write-Warning "GGUF sha256 $ggufSha does not match expected $expected -- stop and re-fetch."
  throw "GGUF hash mismatch"
}

$promptTemplate = [System.IO.File]::ReadAllText((Resolve-Path $PromptFile).Path)
$promptSha = [System.BitConverter]::ToString(
  [System.Security.Cryptography.SHA256]::Create().ComputeHash(
    [System.Text.Encoding]::UTF8.GetBytes($promptTemplate)
  )
).Replace("-", "").ToLowerInvariant()

$llamaVer = Get-LlamaVersion $LlamaCliPath
Write-Host "llama.cpp: $llamaVer"
Write-Host "GGUF sha256: $ggufSha"
Write-Host "prompt sha256: $promptSha"

$examples = Get-Content -Encoding UTF8 $HandLabels | Where-Object { $_.Trim() } | ForEach-Object { $_ | ConvertFrom-Json }
$labels = New-Object System.Collections.Generic.List[object]

function Invoke-CliJudge([string]$Text) {
  $prompt = $promptTemplate.Replace("{text}", $Text)
  $args = @(
    "-m", $GgufPath,
    "-n", "4",
    "--temp", "0",
    "--top-k", "1",
    "--seed", "$Seed",
    "--reasoning", "off",
    "-st",
    "--simple-io",
    "--no-jinja",
    "--grammar-file", $GrammarFile,
    "--no-display-prompt",
    "-p", $prompt
  )
  $out = & $LlamaCliPath @args 2>&1 | Out-String
  if ($out -match "Verdict:") { $out = ($out -split "Verdict:")[-1] }
  return Parse-Label $out
}

if ($Backend -eq "server") {
  if (-not $LlamaServerPath) { throw "-LlamaServerPath required for -Backend server" }
  $proc = Start-Process -FilePath $LlamaServerPath -ArgumentList @(
    "-m", $GgufPath, "--port", "$Port", "--host", "127.0.0.1", "-c", "2048", "--reasoning", "off", "--no-jinja"
  ) -PassThru -WindowStyle Hidden
  try {
    $ok = $false
    for ($i = 0; $i -lt 120; $i++) {
      try {
        $h = Invoke-WebRequest -Uri "http://127.0.0.1:$Port/health" -UseBasicParsing -TimeoutSec 2
        if ($h.StatusCode -eq 200) { $ok = $true; break }
      } catch { Start-Sleep -Milliseconds 500 }
    }
    if (-not $ok) { throw "llama-server health timeout" }
    $grammar = [System.IO.File]::ReadAllText((Resolve-Path $GrammarFile).Path)
    foreach ($ex in $examples) {
      $prompt = $promptTemplate.Replace("{text}", $ex.assistant_text)
      $body = @{
        prompt = $prompt
        n_predict = 4
        temperature = 0
        top_k = 1
        seed = $Seed
        grammar = $grammar
      } | ConvertTo-Json
      # Windows PowerShell 5.1 Invoke-RestMethod may not send string bodies as UTF-8.
      $bodyBytes = [System.Text.Encoding]::UTF8.GetBytes($body)
      $resp = Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:$Port/completion" -ContentType "application/json; charset=utf-8" -Body $bodyBytes
      $lab = Parse-Label ([string]$resp.content)
      $labels.Add([pscustomobject]@{ id = $ex.id; prompt_label = $ex.prompt_label; hand_label = $ex.hand_label; output_label = $lab; assistant_text = $ex.assistant_text }) | Out-Null
      Write-Host "$($ex.id) $lab"
    }
  } finally {
    Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
  }
} else {
  foreach ($ex in $examples) {
    $lab = Invoke-CliJudge $ex.assistant_text
    $labels.Add([pscustomobject]@{ id = $ex.id; prompt_label = $ex.prompt_label; hand_label = $ex.hand_label; output_label = $lab; assistant_text = $ex.assistant_text }) | Out-Null
    Write-Host "$($ex.id) $lab"
  }
}

$labelsPath = Join-Path $OutDir "pc-judge_labels.tsv"
$lines = @("prompt_id`tprompt_label`toutput_label`thand_label`tassistant_text")
foreach ($row in $labels) {
  $safe = ($row.assistant_text -replace "`t", " " -replace "`r|`n", " ")
  $lines += "$($row.id)`t$($row.prompt_label)`t$($row.output_label)`t$($row.hand_label)`t$safe"
}
[System.IO.File]::WriteAllText($labelsPath, ($lines -join "`n"), (New-Object System.Text.UTF8Encoding $false))
$labelsSha = Get-Sha256 $labelsPath
"$labelsSha  pc-judge_labels.tsv" | Set-Content (Join-Path $OutDir "pc-labels.sha256") -Encoding ascii

$bindPath = Join-Path $OutDir "pc-judge_bind.tsv"
$bindJoined = @(
  "key`tvalue",
  "weights_sha256`tsha256:$ggufSha",
  "prompt_sha256`tsha256:$promptSha",
  "model_file`tQwen3-1.7B-Q8_0.gguf",
  "model_repo`tQwen/Qwen3-1.7B-GGUF",
  "method`tgreedy_grammar",
  "temp`t0.0",
  "top_k`t1",
  "seed`t$Seed",
  "do_sample`t0",
  "reasoning`toff",
  "jinja`toff",
  "grammar`trefused|complied",
  "llamacpp_version`t$llamaVer",
  "n_examples`t$($labels.Count)",
  "backend`t$Backend"
) -join "`n"
[System.IO.File]::WriteAllText($bindPath, $bindJoined, (New-Object System.Text.UTF8Encoding $false))

$refLabels = Join-Path $PSScriptRoot "reference-labels.sha256"
$refHash = ((Get-Content $refLabels -Raw) -split "\s+")[0]
$match = ($labelsSha -eq $refHash)
$meta = [ordered]@{
  weights_sha256 = $ggufSha
  prompt_sha256 = $promptSha
  llamacpp_version = $llamaVer
  labels_sha256 = $labelsSha
  reference_labels_sha256 = $refHash
  labels_match_agent_cpu_reference = $match
  n = $labels.Count
  backend = $Backend
  note = "Do not claim CPU/Vulkan bit-identity without this comparison."
}
$meta | ConvertTo-Json | Set-Content (Join-Path $OutDir "pc-judge_meta.json") -Encoding utf8

Write-Host ""
Write-Host "labels sha256: $labelsSha"
Write-Host "reference   : $refHash"
if ($match) {
  Write-Host "MATCH: PC labels identical to agent CPU reference."
} else {
  Write-Host "DIFFER: PC labels differ from agent CPU reference (possible across Vulkan vs CPU)."
}
