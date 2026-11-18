param(
    [Parameter(Mandatory = $true)]
    [string]$ProjectDir
)

$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Drawing

$resolvedProject = (Resolve-Path -LiteralPath $ProjectDir).Path
$queuePath = Join-Path $resolvedProject "take_queue.json"
if (-not (Test-Path -LiteralPath $queuePath)) {
    throw "take_queue.json nao encontrado em $resolvedProject"
}

$queue = Get-Content -LiteralPath $queuePath -Raw -Encoding utf8 | ConvertFrom-Json
$outputDir = Join-Path $resolvedProject "qc\contact_sheets"
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

$tileWidth = 768
$tileHeight = 432
$labelHeight = 60
$columns = 3
$rows = 3
$sheetWidth = $tileWidth * $columns
$sheetHeight = ($tileHeight + $labelHeight) * $rows

$font = New-Object System.Drawing.Font("Segoe UI", 17, [System.Drawing.FontStyle]::Bold)
$captionFont = New-Object System.Drawing.Font("Segoe UI", 13, [System.Drawing.FontStyle]::Regular)
$whiteBrush = [System.Drawing.Brushes]::White
$grayBrush = New-Object System.Drawing.SolidBrush([System.Drawing.Color]::FromArgb(190, 205, 215))
$blackBrush = [System.Drawing.Brushes]::Black
$format = New-Object System.Drawing.StringFormat
$format.Trimming = [System.Drawing.StringTrimming]::EllipsisCharacter
$format.FormatFlags = [System.Drawing.StringFormatFlags]::NoWrap

$outputs = @()
try {
    foreach ($firstSlide in @(1, 4, 7, 10)) {
        $lastSlide = [Math]::Min($firstSlide + 2, 12)
        $sheet = New-Object System.Drawing.Bitmap($sheetWidth, $sheetHeight)
        $graphics = [System.Drawing.Graphics]::FromImage($sheet)
        try {
            $graphics.Clear([System.Drawing.Color]::FromArgb(10, 14, 20))
            $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $graphics.PixelOffsetMode = [System.Drawing.Drawing2D.PixelOffsetMode]::HighQuality
            $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::HighQuality

            for ($slide = $firstSlide; $slide -le $lastSlide; $slide++) {
                $row = $slide - $firstSlide
                foreach ($variantIndex in 0..2) {
                    $variant = @("A", "B", "C")[$variantIndex]
                    $takeId = "S{0:D2}{1}" -f $slide, $variant
                    $take = $queue.takes | Where-Object { $_.id -eq $takeId } | Select-Object -First 1
                    $x = $variantIndex * $tileWidth
                    $y = $row * ($tileHeight + $labelHeight)
                    $graphics.FillRectangle($blackBrush, $x, $y, $tileWidth, $labelHeight)

                    if ($null -eq $take) {
                        $graphics.DrawString("$takeId - ausente", $font, $whiteBrush, $x + 12, $y + 14)
                        continue
                    }

                    $imagePath = [string]$take.base_image.file
                    $labelRect = [System.Drawing.RectangleF]::new(
                        [single]($x + 12),
                        [single]($y + 5),
                        [single]($tileWidth - 24),
                        [single]26
                    )
                    $captionRect = [System.Drawing.RectangleF]::new(
                        [single]($x + 12),
                        [single]($y + 31),
                        [single]($tileWidth - 24),
                        [single]23
                    )
                    $graphics.DrawString($takeId, $font, $whiteBrush, $labelRect, $format)
                    $graphics.DrawString([string]$take.caption, $captionFont, $grayBrush, $captionRect, $format)

                    if (-not $imagePath -or -not (Test-Path -LiteralPath $imagePath)) {
                        $graphics.DrawString("candidato ainda nao disponivel", $font, $whiteBrush, $x + 12, $y + $labelHeight + 24)
                        continue
                    }

                    $source = [System.Drawing.Image]::FromFile($imagePath)
                    try {
                        $graphics.DrawImage(
                            $source,
                            ([System.Drawing.Rectangle]::new(
                                [int]$x,
                                [int]($y + $labelHeight),
                                [int]$tileWidth,
                                [int]$tileHeight
                            ))
                        )
                    }
                    finally {
                        $source.Dispose()
                    }
                }
            }

            $outputPath = Join-Path $outputDir ("slides_{0:D2}_{1:D2}.png" -f $firstSlide, $lastSlide)
            $sheet.Save($outputPath, [System.Drawing.Imaging.ImageFormat]::Png)
            $outputs += $outputPath
        }
        finally {
            $graphics.Dispose()
            $sheet.Dispose()
        }
    }
}
finally {
    $font.Dispose()
    $captionFont.Dispose()
    $grayBrush.Dispose()
    $format.Dispose()
}

$outputs
