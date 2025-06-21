# PowerShell script to create Red Hat VMs on Windows using Hyper-V
# Run as Administrator

param(
    [string]$RhelImagePath = "C:\VMs\Images\rhel-9.6-x86_64-dvd.iso",
    [string]$VMPath = "C:\VMs",
    [int]$MemoryGB = 4,
    [int]$ProcessorCount = 2,
    [string]$SwitchName = "SplunkVMSwitch"
)

# Check if running as Administrator
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Error "This script must be run as Administrator"
    exit 1
}

# VM Configuration
$VMs = @{
    "ansible-control" = @{ IP = "192.168.100.5"; Memory = 2GB; CPUs = 2 }
    "splunk-mgmt"     = @{ IP = "192.168.100.10"; Memory = 4GB; CPUs = 2 }
    "splunk-idx1"     = @{ IP = "192.168.100.11"; Memory = 4GB; CPUs = 2 }
    "splunk-idx2"     = @{ IP = "192.168.100.12"; Memory = 4GB; CPUs = 2 }
    "splunk-sh1"      = @{ IP = "192.168.100.13"; Memory = 4GB; CPUs = 2 }
    "splunk-sh2"      = @{ IP = "192.168.100.14"; Memory = 4GB; CPUs = 2 }
    "splunk-hf"       = @{ IP = "192.168.100.15"; Memory = 4GB; CPUs = 2 }
}

Write-Host "=== Red Hat Splunk VM Creator for Windows ===" -ForegroundColor Green
Write-Host "This will create 7 VMs with Red Hat Enterprise Linux 9" -ForegroundColor Yellow
Write-Host ""

# Check if RHEL image exists
if (-not (Test-Path $RhelImagePath)) {
    Write-Error "RHEL image not found at: $RhelImagePath"
    Write-Host "Download from: https://developers.redhat.com/products/rhel/download" -ForegroundColor Yellow
    exit 1
}

# Create VM directory
if (-not (Test-Path $VMPath)) {
    New-Item -ItemType Directory -Path $VMPath -Force
}

# Create virtual switch if it doesn't exist
$existingSwitch = Get-VMSwitch -Name $SwitchName -ErrorAction SilentlyContinue
if (-not $existingSwitch) {
    Write-Host "Creating virtual switch: $SwitchName" -ForegroundColor Yellow
    New-VMSwitch -Name $SwitchName -SwitchType Internal
    
    # Configure NAT network
    New-NetIPAddress -IPAddress 192.168.100.1 -PrefixLength 24 -InterfaceAlias "vEthernet ($SwitchName)"
    New-NetNat -Name "SplunkVMNAT" -InternalIPInterfaceAddressPrefix 192.168.100.0/24
}

# Function to convert qcow2 to VHD
function Convert-QCow2ToVHD {
    param(
        [string]$SourcePath,
        [string]$DestinationPath
    )
    
    # Check if qemu-img is available (install QEMU for Windows)
    $qemuImg = Get-Command "qemu-img" -ErrorAction SilentlyContinue
    if (-not $qemuImg) {
        Write-Error "qemu-img not found. Please install QEMU for Windows: https://qemu.weilnetz.de/w64/"
        Write-Host "Or use: choco install qemu" -ForegroundColor Yellow
        return $false
    }
    
    Write-Host "Converting $SourcePath to VHD format..." -ForegroundColor Yellow
    & qemu-img convert -f qcow2 -O vhdx "$SourcePath" "$DestinationPath"
    
    return $?
}

# Function to create cloud-init ISO
function Create-CloudInitISO {
    param(
        [string]$VMName,
        [string]$IPAddress,
        [string]$OutputPath
    )
    
    $tempDir = "$env:TEMP\$VMName-cloudinit"
    New-Item -ItemType Directory -Path $tempDir -Force
    
    # Create user-data
    $userData = @"
#cloud-config
hostname: $VMName
fqdn: $VMName.local
manage_etc_hosts: true

# Create ansible user (this is done on redhat side)
#users:
#  - name: ansible
#    groups: wheel
#    shell: /bin/bash
#    sudo: ALL=(ALL) NOPASSWD:ALL
#    ssh_authorized_keys:
#      - ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC... # Add your SSH public key here

# Register with Red Hat (using your developer account) (this is done on redhat side)
#rh_subscription:
#  username: YOUR_RH_USERNAME
#  password: YOUR_RH_PASSWORD
#  auto-attach: true

package_update: true
packages:
  - python3
  - python3-pip
  - curl
  - wget
  - vim

# Configure static IP
write_files:
  - path: /etc/NetworkManager/system-connections/eth0.nmconnection
    content: |
      [connection]
      id=eth0
      type=ethernet
      interface-name=eth0
      
      [ethernet]
      
      [ipv4]
      method=manual
      addresses=$IPAddress/24
      gateway=192.168.100.1
      dns=8.8.8.8;8.8.4.4
      
      [ipv6]
      method=ignore
    permissions: '0600'

runcmd:
  - nmcli connection reload
  - nmcli connection up eth0
  - systemctl enable sshd
  - systemctl start sshd
  - firewall-cmd --permanent --add-service=ssh
  - firewall-cmd --reload
"@

    $userData | Out-File -FilePath "$tempDir\user-data" -Encoding UTF8

    # Create meta-data
    $metaData = @"
instance-id: $VMName
local-hostname: $VMName
"@

    $metaData | Out-File -FilePath "$tempDir\meta-data" -Encoding UTF8

    # Create ISO (requires oscdimg from Windows ADK or use mkisofs alternative)
    # Alternative: Use ImgBurn or create manually
    Write-Host "Cloud-init files created in: $tempDir" -ForegroundColor Green
    Write-Host "Manual step: Create ISO from $tempDir contents and save as $OutputPath" -ForegroundColor Yellow
    
    return $tempDir
}

# Create VMs
foreach ($vmName in $VMs.Keys) {
    $vmConfig = $VMs[$vmName]
    $vmDir = "$VMPath\$vmName"
    
    Write-Host "Creating VM: $vmName" -ForegroundColor Green
    
    # Create VM directory
    New-Item -ItemType Directory -Path $vmDir -Force
    
    # Convert RHEL image to VHD
    $vhdPath = "$vmDir\$vmName.vhdx"
    if (-not (Test-Path $vhdPath)) {
        $success = Convert-QCow2ToVHD -SourcePath $RhelImagePath -DestinationPath $vhdPath
        if (-not $success) {
            Write-Error "Failed to convert image for $vmName"
            continue
        }
    }
    
    # Create cloud-init ISO
    $cloudInitPath = "$vmDir\$vmName-cloudinit.iso"
    $tempDir = Create-CloudInitISO -VMName $vmName -IPAddress $vmConfig.IP -OutputPath $cloudInitPath
    
    # Create the VM
    $vm = New-VM -Name $vmName -MemoryStartupBytes $vmConfig.Memory -Path $vmDir -Generation 2
    
    # Configure VM
    Set-VM -VM $vm -ProcessorCount $vmConfig.CPUs
    Set-VM -VM $vm -AutomaticStartAction Nothing
    Set-VM -VM $vm -AutomaticStopAction ShutDown
    
    # Add hard drive
    Add-VMHardDiskDrive -VM $vm -Path $vhdPath
    
    # Add cloud-init ISO (create manually for now)
    Write-Host "Manual step: Add $cloudInitPath as DVD drive to $vmName" -ForegroundColor Yellow
    
    # Connect to switch
    Get-VMNetworkAdapter -VM $vm | Connect-VMNetworkAdapter -SwitchName $SwitchName
    
    # Disable Secure Boot for Linux
    Set-VMFirmware -VM $vm -EnableSecureBoot Off
    
    # Set boot order
    $hdBoot = Get-VMHardDiskDrive -VM $vm
    $dvdBoot = Get-VMDvdDrive -VM $vm
    Set-VMFirmware -VM $vm -BootOrder $hdBoot, $dvdBoot
    
    Write-Host "VM $vmName created successfully" -ForegroundColor Green
    Write-Host "IP Address: $($vmConfig.IP)" -ForegroundColor Cyan
    Write-Host ""
}

Write-Host "=== VM Creation Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "Next Steps:" -ForegroundColor Yellow
Write-Host "1. Create cloud-init ISOs manually for each VM"
Write-Host "2. Attach ISOs to VMs as DVD drives"
Write-Host "3. Start VMs: Get-VM | Start-VM"
Write-Host "4. Wait for cloud-init to complete (5-10 minutes)"
Write-Host "5. Test SSH connectivity"
Write-Host ""
Write-Host "VM Management Commands:" -ForegroundColor Green
Write-Host "Start all VMs:    Get-VM | Where-Object {$_.Name -like 'splunk-*' -or $_.Name -eq 'ansible-control'} | Start-VM"
Write-Host "Stop all VMs:     Get-VM | Where-Object {$_.Name -like 'splunk-*' -or $_.Name -eq 'ansible-control'} | Stop-VM"
Write-Host "Remove all VMs:   Get-VM | Where-Object {$_.Name -like 'splunk-*' -or $_.Name -eq 'ansible-control'} | Remove-VM -Force"