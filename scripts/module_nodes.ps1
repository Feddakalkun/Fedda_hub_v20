function Get-FeddaNodeConfig {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RootPath,
        [bool]$EnabledOnly = $true,
        [scriptblock]$Logger = $null
    )

    function Write-ModuleNodeLog {
        param([string]$Message, [string]$Color = "Gray")
        if ($Logger) {
            & $Logger $Message $Color
        }
    }

    $NodesPath = Join-Path $RootPath "config\nodes.json"
    if (-not (Test-Path $NodesPath)) {
        throw "config/nodes.json not found"
    }

    $ParsedNodes = Get-Content $NodesPath -Raw | ConvertFrom-Json
    $AllNodes = @()
    foreach ($Node in $ParsedNodes) {
        $AllNodes += $Node
    }
    $ManifestPath = Join-Path $RootPath "config\modules.json"
    if (-not (Test-Path $ManifestPath)) {
        Write-ModuleNodeLog "Module manifest not found; installing all nodes from nodes.json." "Yellow"
        return $AllNodes
    }

    try {
        $Manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json
        $Modules = @()
        foreach ($Module in $Manifest.modules) {
            $Modules += $Module
        }
        if ($EnabledOnly) {
            $Modules = @($Modules | Where-Object { $_.enabled -ne $false })
        }

        $WantedNodeNames = [ordered]@{}
        foreach ($Module in $Modules) {
            foreach ($NodeName in @($Module.custom_nodes)) {
                if (-not [string]::IsNullOrWhiteSpace($NodeName)) {
                    $WantedNodeNames[$NodeName] = $true
                }
            }
        }

        if ($WantedNodeNames.Count -eq 0) {
            Write-ModuleNodeLog "Module manifest has no custom node entries; installing all nodes from nodes.json." "Yellow"
            return $AllNodes
        }

        $SelectedNodes = @($AllNodes | Where-Object { $WantedNodeNames.Contains($_.name) })
        $SelectedNames = @{}
        foreach ($Node in $SelectedNodes) {
            $SelectedNames[$Node.name] = $true
        }

        $MissingConfigs = @()
        foreach ($NodeName in $WantedNodeNames.Keys) {
            if (-not $SelectedNames.ContainsKey($NodeName)) {
                $MissingConfigs += $NodeName
            }
        }

        if ($MissingConfigs.Count -gt 0) {
            Write-ModuleNodeLog "Module manifest references missing node config(s): $($MissingConfigs -join ', ')" "Yellow"
        }

        Write-ModuleNodeLog "Module-aware node set: $($SelectedNodes.Count) of $($AllNodes.Count) configured nodes selected." "Green"
        return $SelectedNodes
    }
    catch {
        Write-ModuleNodeLog "Module manifest could not be read; installing all nodes from nodes.json. $_" "Yellow"
        return $AllNodes
    }
}
