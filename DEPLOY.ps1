# Deploy Ratuba Pages + comments repo. Token: $env:GITHUB_TOKEN, or saved file under LocalAppData, or one-time paste.
#
# Creates public repos ratubaworld-pages and ratubaworld-comments if missing,
# rewrites REPO in index.html, pushes main, enables GitHub Pages (legacy).
# You must install Utterances in the browser once (GitHub does not automate that).

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$PagesRepo  = 'ratubaworld-pages'
$IssuesRepo = 'ratubaworld-comments'

# --- Locate git.exe
$Git = $null
foreach ($p in @(
  'C:\Program Files\Git\cmd\git.exe',
  'C:\Program Files\Git\bin\git.exe',
  'C:\Program Files (x86)\Git\cmd\git.exe'
)) {
  if (Test-Path -LiteralPath $p) { $Git = $p; break }
}
if (-not $Git) {
  $cmd = Get-Command git.exe -ErrorAction SilentlyContinue
  if ($cmd) { $Git = $cmd.Source }
}
if (-not $Git) {
  Write-Error 'Git not found. Install Git for Windows, then run again.'
}

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root

$TokenDir  = Join-Path $env:LOCALAPPDATA 'ratubaworld-pages-deploy'
$TokenFile = Join-Path $TokenDir 'github_token.txt'

function Get-GitHubTokenFromUser {
  if ($env:GITHUB_TOKEN -and $env:GITHUB_TOKEN.Trim().Length -gt 10) {
    Write-Host 'Using GITHUB_TOKEN from environment.' -ForegroundColor DarkGray
    return $env:GITHUB_TOKEN.Trim()
  }
  if (Test-Path -LiteralPath $TokenFile) {
    $cached = [System.IO.File]::ReadAllText($TokenFile).Trim()
    if ($cached.Length -gt 10) {
      Write-Host ('Using saved token: ' + $TokenFile) -ForegroundColor DarkGray
      return $cached
    }
  }
  Write-Host ''
  Write-Host 'Create a token:' -ForegroundColor Cyan
  Write-Host '  https://github.com/settings/tokens/new' -ForegroundColor Cyan
  Write-Host '  Classic: enable scope repo (full).' -ForegroundColor Gray
  Write-Host ''
  Write-Host ('Or set user env GITHUB_TOKEN, or save to: ' + $TokenFile) -ForegroundColor Gray
  Write-Host ''
  $sec = Read-Host 'Paste token here' -AsSecureString
  $bstr = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($sec)
  try {
    $plain = [Runtime.InteropServices.Marshal]::PtrToStringUni($bstr)
  }
  finally {
    [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($bstr)
  }
  if ($null -eq $plain) { return $null }
  $plain = $plain.Trim()
  if ([string]::IsNullOrWhiteSpace($plain)) { return $null }
  $save = Read-Host 'Save token on this PC for future deploys? (y/N)'
  if ($save -match '^[Yy]') {
    New-Item -ItemType Directory -Force -Path $TokenDir | Out-Null
    [System.IO.File]::WriteAllText($TokenFile, $plain, [System.Text.UTF8Encoding]::new($false))
    try {
      & icacls.exe $TokenFile /inheritance:r /grant:r ($env:USERNAME + ':(R,W)') | Out-Null
    }
    catch { }
    Write-Host ('Saved. To remove later, delete: ' + $TokenFile) -ForegroundColor Green
  }
  return $plain
}

$token = Get-GitHubTokenFromUser
if (-not $token) { Write-Error 'No token provided.' }

$headers = @{
  'Accept'               = 'application/vnd.github+json'
  'Authorization'        = 'Bearer ' + $token
  'X-GitHub-Api-Version' = '2022-11-28'
  'User-Agent'           = 'ratubaworld-pages-deploy-script'
}

$me = Invoke-RestMethod -Uri 'https://api.github.com/user' -Headers $headers -Method GET
$userLogin = $me.login
Write-Host ''
Write-Host "Signed in as: $userLogin" -ForegroundColor Green

function Test-RepoExists([string]$owner, [string]$name) {
  try {
    Invoke-RestMethod -Uri "https://api.github.com/repos/$owner/$name" -Headers $headers | Out-Null
    return $true
  }
  catch {
    $code = $null
    if ($_.Exception.Response -and $_.Exception.Response.StatusCode) {
      $code = [int]$_.Exception.Response.StatusCode
    }
    if ($code -eq 404) { return $false }
    throw
  }
}

function New-EmptyRepo([string]$name, [string]$description) {
  $bodyObj = @{ name = $name; private = $false; has_issues = $true; description = $description }
  Invoke-RestMethod -Uri 'https://api.github.com/user/repos' -Headers $headers -Method POST `
    -Body ($bodyObj | ConvertTo-Json) -ContentType 'application/json' | Out-Null
}

if (-not (Test-RepoExists $userLogin $IssuesRepo)) {
  Write-Host "Creating repo $IssuesRepo..."
  New-EmptyRepo $IssuesRepo 'Ratubaworld - Utterances (GitHub Issues)'
}
else {
  Write-Host "Repo $IssuesRepo already exists - OK"
}

if (-not (Test-RepoExists $userLogin $PagesRepo)) {
  Write-Host "Creating repo $PagesRepo..."
  New-EmptyRepo $PagesRepo 'Ratubaworld - GitHub Pages (2008-style mock)'
}
else {
  Write-Host "Repo $PagesRepo already exists - OK"
}

$idx = Join-Path $Root 'index.html'
if (-not (Test-Path -LiteralPath $idx)) { Write-Error "Missing index.html in $Root" }

$raw = Get-Content -LiteralPath $idx -Raw -Encoding UTF8
$needle = 'var REPO = "YOUR_GITHUB_USERNAME/ratubaworld-comments"'
$repl = 'var REPO = "' + $userLogin + '/' + $IssuesRepo + '"'

if ($raw.IndexOf($needle, [StringComparison]::Ordinal) -lt 0) {
  $wired = 'var REPO = "' + $userLogin + '/' + $IssuesRepo + '"'
  if ($raw.IndexOf($wired, [StringComparison]::Ordinal) -ge 0) {
    Write-Host "index.html already targets $userLogin/$IssuesRepo"
  }
  else {
    Write-Warning 'Could not find REPO placeholder; leaving index.html unchanged.'
  }
}
else {
  $raw = $raw.Replace($needle, $repl)
  [System.IO.File]::WriteAllText($idx, $raw, [System.Text.UTF8Encoding]::new($false))
}

& $Git -C $Root config user.email ($userLogin + '@users.noreply.github.com')
& $Git -C $Root config user.name $userLogin

$st = (& $Git -C $Root status --porcelain) -join "`n"
if ($st.Trim().Length -gt 0) {
  & $Git -C $Root add index.html
  if (Test-Path (Join-Path $Root 'classic-2008.html')) {
    & $Git -C $Root add classic-2008.html
  }
  if (Test-Path (Join-Path $Root 'media')) {
    & $Git -C $Root add media
  }
  if (Test-Path (Join-Path $Root 'preview-clean-mobile.html')) {
    & $Git -C $Root add preview-clean-mobile.html
  }
  $savedEap = $ErrorActionPreference
  $ErrorActionPreference = 'Continue'
  & $Git -C $Root commit -m "Configure Utterances: ${userLogin}/${IssuesRepo}" 2>&1 | Out-Null
  $ErrorActionPreference = $savedEap
  if (-not $?) {
    Write-Host 'No new commit (nothing to change or empty commit skipped).' -ForegroundColor Gray
  }
}

$encToken = [Uri]::EscapeDataString($token)
$remoteUrlPush = 'https://x-access-token:' + $encToken + '@github.com/' + $userLogin + '/' + $PagesRepo + '.git'
$remoteClean = 'https://github.com/' + $userLogin + '/' + $PagesRepo + '.git'

# "remote remove origin" errors if missing; stderr under StrictMode stops the script. Use cmd for a quiet rm.
cmd.exe /c "`"$Git`" -C `"$Root`" remote remove origin >nul 2>&1"
$saveEaRemote = $ErrorActionPreference
$ErrorActionPreference = 'SilentlyContinue'
$null = & $Git -C $Root remote add origin $remoteClean 2>&1
$addRc = $LASTEXITCODE
$ErrorActionPreference = $saveEaRemote
if ($addRc -ne 0) {
  $null = & $Git -C $Root remote set-url origin $remoteClean 2>&1
}
Write-Host ''
Write-Host 'Pushing to GitHub...'
$env:GIT_TERMINAL_PROMPT = '0'
try {
  & $Git -C $Root push --set-upstream $remoteUrlPush HEAD:main
}
finally {
  Remove-Item Env:GIT_TERMINAL_PROMPT -ErrorAction SilentlyContinue
}

Write-Host ''

try {
  $pagesBodyObj = @{ build_type = 'legacy'; source = @{ branch = 'main'; path = '/' } }
  Invoke-RestMethod -Uri ('https://api.github.com/repos/' + $userLogin + '/' + $PagesRepo + '/pages') -Headers $headers -Method POST `
    -Body ($pagesBodyObj | ConvertTo-Json -Compress -Depth 5) `
    -ContentType 'application/json' | Out-Null
  Write-Host 'GitHub Pages: enabled from main /'
}
catch {
  if ($_.Exception.Response -and [int]$_.Exception.Response.StatusCode -eq 409) {
    Write-Host 'GitHub Pages: already configured (409) - OK'
  }
  elseif ($_.ErrorDetails.Message -match '(?i)(already|409)') {
    Write-Host 'GitHub Pages: appears already configured - OK'
  }
  else {
    Write-Host ('Pages API note (enable Pages manually in repo Settings if needed): ' + $_.Exception.Message) -ForegroundColor Yellow
  }
}

$live = 'https://' + $userLogin + '.github.io/' + $PagesRepo + '/'
Write-Host ''
Write-Host 'Done. Your site URL (wait about 1-3 minutes on first publish):' -ForegroundColor Green
Write-Host ('  ' + $live) -ForegroundColor Green
Write-Host ''
Write-Host 'Browser step - install Utterances on your comments repo:' -ForegroundColor Yellow
Write-Host '  Opening https://github.com/apps/utterances/installations/new' -ForegroundColor Yellow
try {
  Start-Process 'https://github.com/apps/utterances/installations/new'
}
catch { }

Write-Host ''
Write-Host 'In that installer, choose repository:' -ForegroundColor White
Write-Host ('  ' + $userLogin + '/' + $IssuesRepo) -ForegroundColor Cyan
Write-Host ''
Write-Host 'Then reload your live URL. The yellow help box hides after Utterances is installed.' -ForegroundColor Gray

Remove-Variable token -Force -ErrorAction SilentlyContinue
$token = $null
