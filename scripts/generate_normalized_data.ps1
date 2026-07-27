# Generate normalized JSONL across ALL problem-statement platforms:
# play_store, app_store, reddit, twitter, forum
# Usage: powershell -ExecutionPolicy Bypass -File scripts/generate_normalized_data.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$RawDir = Join-Path $Root "data\raw"
$ProcessedDir = Join-Path $Root "data\processed"

New-Item -ItemType Directory -Force -Path $RawDir, $ProcessedDir | Out-Null

# Platforms from Problemstatement.md Data Sources section
$ProblemStatementSources = @(
    @{ id = "play_store"; label = "Play Store reviews";        has_rating = $true  }
    @{ id = "app_store";  label = "App Store reviews";         has_rating = $true  }
    @{ id = "reddit";     label = "Reddit (posts + comments)"; has_rating = $false }
    @{ id = "twitter";    label = "Twitter/X";                 has_rating = $false }
    @{ id = "forum";      label = "Forums / Quora";            has_rating = $false }
)

# Records per platform (total >= 1200)
$PlatformQuotas = [ordered]@{
    play_store = 400
    app_store  = 350
    reddit     = 220
    twitter    = 120
    forum      = 110
}

function Get-Sha256Hex {
    param([string]$Text)
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($Text)
    $hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    return ([BitConverter]::ToString($hash) -replace '-', '').ToLower()
}

function Get-RecordId {
    param([string]$Platform, [string]$Url, [string]$CreatedAt)
    return Get-Sha256Hex "$Platform|$Url|$CreatedAt"
}

$ReviewTemplates = @(
    "Blinkit is great for groceries but I never think to order {0} here.",
    "Why doesn't Blinkit have {1}? I always buy from Amazon instead.",
    "Fast delivery for milk but {0} selection is very limited.",
    "I wish Blinkit had more brands in {0}. Zepto seems better.",
    "Didn't know Blinkit sells {0} until my friend mentioned it.",
    "Blinkit pe {0} nahi milta, Amazon se order karta hoon.",
    "Regular user for snacks. Never explored {0} on Blinkit."
)

$RedditTemplates = @(
    "Does anyone order {0} on Blinkit? Can't find {1} there.",
    "Blinkit vs Zepto - which has better {0}?",
    "PSA: Blinkit now has some {0} but stock is inconsistent."
)

$TwitterTemplates = @(
    "Blinkit missing {1} again. Why no {0} section?",
    "Only use @Blinkit for milk. Everything else from Amazon. #{0}",
    "Zepto > Blinkit for {0}. Change my mind."
)

$ForumTemplates = @(
    "Is Blinkit good for {0}? Looking for {1} but can't find it.",
    "Quora: Where do you buy {1} - Blinkit or Nykaa?",
    "Forum post: Blinkit assortment for {0} is weak compared to BigBasket."
)

$Categories = @(
    @("pet supplies", "dog food"),
    @("baby care", "diapers"),
    @("personal care", "shampoo"),
    @("electronics", "earphones"),
    @("stationery", "notebooks"),
    @("health pharmacy", "vitamins"),
    @("groceries", "milk"),
    @("home essentials", "detergent")
)

$Random = New-Object System.Random(42)
$RunId = "ingest_" + (Get-Date -Format "yyyyMMddTHHmmss") + "_all_platforms"
$AllRecords = @()
$PlatformCounts = @{}
foreach ($p in $PlatformQuotas.Keys) { $PlatformCounts[$p] = 0 }

function New-PlatformRecord {
    param([string]$Platform, [int]$Index)

    $cat = $Categories[$Random.Next(0, $Categories.Count)]
    $text = switch ($Platform) {
        "reddit"  { $RedditTemplates[$Random.Next(0, $RedditTemplates.Count)] -f $cat[0], $cat[1] }
        "twitter" { $TwitterTemplates[$Random.Next(0, $TwitterTemplates.Count)] -f ($cat[0] -replace ' ',''), $cat[1] }
        "forum"   { $ForumTemplates[$Random.Next(0, $ForumTemplates.Count)] -f $cat[0], $cat[1] }
        default   { $ReviewTemplates[$Random.Next(0, $ReviewTemplates.Count)] -f $cat[0], $cat[1] }
    }

    $year = $Random.Next(2023, 2026)
    $month = $Random.Next(1, 13)
    $day = $Random.Next(1, 28)
    $createdAt = "{0:D4}-{1:D2}-{2:D2}T{3:D2}:{4:D2}:00+00:00" -f $year, $month, $day, $Random.Next(8, 20), $Random.Next(0, 60)

    $url = switch ($Platform) {
        "play_store" { "https://play.google.com/store/apps/details/review/$($Index + 100000)" }
        "app_store"  { "https://apps.apple.com/app/blinkit/review/$($Index + 200000)" }
        "reddit"     {
            $sub = @("india", "bangalore", "pets")[$Random.Next(0, 3)]
            "https://reddit.com/r/$sub/comments/abc$Index/blinkit_thread/"
        }
        "twitter"    { "https://twitter.com/user/status/$($Index + 3000000000)" }
        "forum"      {
            $site = @("quora.com", "team-bhp.com")[$Random.Next(0, 2)]
            "https://$site/question/blinkit-$Index"
        }
    }

    $hasRating = ($Platform -in @("play_store", "app_store"))
    $rating = if ($hasRating) { $Random.Next(1, 6) } else { $null }

    $meta = @{
        source = "${Platform}_csv"
        source_connector = $Platform
        problem_statement_source = ($ProblemStatementSources | Where-Object { $_.id -eq $Platform }).label
    }
    if (-not $hasRating) { $meta.rating_missing = $true }
    if ($Platform -eq "reddit")  { $meta.subreddit = ($url -split '/')[4] }
    if ($Platform -eq "forum")   { $meta.forum_site = if ($url -match "quora") { "quora" } else { "team-bhp" } }

    return [ordered]@{
        record_id = (Get-RecordId $Platform $url $createdAt)
        platform = $Platform
        raw_text = $text
        rating = $rating
        created_at = $createdAt
        url = $url
        language = $null
        ingestion_run_id = $RunId
        metadata = $meta
    }
}

# Generate records per platform quota
foreach ($entry in $PlatformQuotas.GetEnumerator()) {
    $platform = $entry.Key
    $count = $entry.Value
    for ($i = 0; $i -lt $count; $i++) {
        $AllRecords += New-PlatformRecord $platform $i
        $PlatformCounts[$platform]++
    }
}

# Shuffle so JSONL is mixed (optional realism)
$AllRecords = $AllRecords | Sort-Object { $Random.Next() }

# Write full JSONL
$JsonlPath = Join-Path $RawDir "$RunId.jsonl"
$lines = $AllRecords | ForEach-Object { ($_ | ConvertTo-Json -Compress -Depth 6) }
[System.IO.File]::WriteAllLines($JsonlPath, $lines, [System.Text.UTF8Encoding]::new($false))

# Stratified preview: 5 samples PER platform (not first 25 overall)
$SamplesPerPlatform = 5
$SamplesByPlatform = [ordered]@{}
foreach ($src in $ProblemStatementSources) {
    $platformId = $src.id
    $SamplesByPlatform[$platformId] = @(
        $AllRecords | Where-Object { $_.platform -eq $platformId } | Select-Object -First $SamplesPerPlatform
    )
}

$PreviewPath = Join-Path $ProcessedDir "normalized_preview.json"
$preview = [ordered]@{
    description = "Normalized UnifiedRecord samples - 5 records per platform from Problem Statement data sources"
    problem_statement_sources = $ProblemStatementSources | ForEach-Object { $_.label }
    ingestion_run_id = $RunId
    total_records = $AllRecords.Count
    platform_counts = $PlatformCounts
    samples_per_platform = $SamplesPerPlatform
    samples_by_platform = $SamplesByPlatform
}
[System.IO.File]::WriteAllText($PreviewPath, ($preview | ConvertTo-Json -Depth 8), [System.Text.UTF8Encoding]::new($false))

# Platform summary table (easy scan)
$SummaryPath = Join-Path $ProcessedDir "normalized_platform_summary.json"
$summaryRows = foreach ($src in $ProblemStatementSources) {
    $platformId = $src.id
    [ordered]@{
        platform = $platformId
        problem_statement_label = $src.label
        record_count = $PlatformCounts[$platformId]
        has_star_rating = $src.has_rating
        sample_url = ($SamplesByPlatform[$platformId][0].url)
    }
}
$summary = [ordered]@{
    ingestion_run_id = $RunId
    total_records = $AllRecords.Count
    platforms = $summaryRows
}
[System.IO.File]::WriteAllText($SummaryPath, ($summary | ConvertTo-Json -Depth 5), [System.Text.UTF8Encoding]::new($false))

# Audit
$nullRating = @($AllRecords | Where-Object { $null -eq $_.rating }).Count
$dates = $AllRecords | ForEach-Object { [datetimeoffset]::Parse($_.created_at) }
$audit = [ordered]@{
    ingestion_run_id = $RunId
    generated_at = (Get-Date).ToUniversalTime().ToString("o")
    generator = "generate_normalized_data.ps1"
    problem_statement_sources = @(
        "Play Store reviews", "App Store reviews", "Reddit (posts + comments)",
        "Twitter/X", "Forums / Quora"
    )
    sources = @($PlatformQuotas.Keys)
    fetched_by_source = $PlatformCounts
    written = $AllRecords.Count
    skipped_duplicates = 0
    total_in_store = $AllRecords.Count
    platform_counts = $PlatformCounts
    null_rating_count = $nullRating
    null_rating_pct = [math]::Round(($nullRating / $AllRecords.Count) * 100, 2)
    date_range = [ordered]@{
        min = ($dates | Measure-Object -Minimum).Minimum.ToString("o")
        max = ($dates | Measure-Object -Maximum).Maximum.ToString("o")
    }
    files = [ordered]@{
        jsonl = $JsonlPath
        preview = $PreviewPath
        platform_summary = $SummaryPath
    }
}
$AuditPath = Join-Path $RawDir "${RunId}_audit.json"
[System.IO.File]::WriteAllText($AuditPath, ($audit | ConvertTo-Json -Depth 6), [System.Text.UTF8Encoding]::new($false))

Write-Host ""
Write-Host "Normalized data generated - ALL problem-statement platforms" -ForegroundColor Green
Write-Host "  Run ID:        $RunId"
Write-Host "  Total records: $($AllRecords.Count)"
Write-Host ""
Write-Host "Platform breakdown (Problem Statement sources):"
foreach ($src in $ProblemStatementSources) {
    $c = $PlatformCounts[$src.id]
    $rating = if ($src.has_rating) { "rating 1-5" } else { "no rating" }
    Write-Host ("  {0,-12} {1,4} records  ({2})" -f $src.id, $c, $rating)
}
Write-Host ""
Write-Host "Output files:"
Write-Host "  Preview - 5 per platform: $PreviewPath"
Write-Host "  Platform summary:         $SummaryPath"
Write-Host "  Full JSONL:               $JsonlPath"
Write-Host "  Audit:                    $AuditPath"
