# Export PPTX slides to PNG via PowerPoint COM
param(
    [Parameter(Mandatory = $true)][string]$Pptx,
    [Parameter(Mandatory = $true)][string]$OutDir
)

$Pptx = (Resolve-Path $Pptx).Path
if (-not (Test-Path $OutDir)) {
    New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
}
$OutDir = (Resolve-Path $OutDir).Path

$ppt = New-Object -ComObject PowerPoint.Application
try {
    $pres = $ppt.Presentations.Open($Pptx, $true, $true, $false)  # ReadOnly, Untitled, WithWindow=false
    # Export as PNG (ppShapeFormatPNG = 17, PpSaveAsFileType.ppSaveAsPNG = 18)
    $pres.SaveAs($OutDir, 18)
    Write-Output "OK: exported PNGs to $OutDir"
    $pres.Close()
} finally {
    $ppt.Quit()
    [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null
}
