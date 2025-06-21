# augment-splunk-ansible

Complete Windows Host Commands
Network Setup (One Time)
# Create the virtual switch and network
New-VMSwitch -Name "SplunkLabSwitch" -SwitchType Internal

# Get the virtual adapter
$adapter = Get-NetAdapter | Where-Object {$_.Name -like "*SplunkLabSwitch*"}

# Assign IP to Windows host (becomes gateway)
New-NetIPAddress -IPAddress 192.168.100.1 -PrefixLength 24 -InterfaceIndex $adapter.InterfaceIndex

# Create NAT for internet access
New-NetNat -Name "SplunkLabNAT" -InternalIPInterfaceAddressPrefix 192.168.100.0/24

# Verify setup
Get-NetIPAddress | Where-Object {$_.IPAddress -eq "192.168.100.1"}
Get-NetNat

# Setup persistant IPs for VMs
# SSH into each VM (use console if no network)
# Replace XX with last octet (5 for ansible-control, 10 for splunk-mgmt, etc.)

# Method 1: Using nmcli (preferred for RHEL 9)
sudo nmcli connection delete "System eth0" 2>/dev/null || true
sudo nmcli connection delete "Wired connection 1" 2>/dev/null || true

# Create new connection with static IP
sudo nmcli connection add \
    type ethernet \
    con-name "eth0-static" \
    ifname eth0 \
    ipv4.method manual \
    ipv4.addresses 192.168.100.XX/24 \
    ipv4.gateway 192.168.100.1 \
    ipv4.dns 8.8.8.8,8.8.4.4 \
    autoconnect yes

# Activate the connection
sudo nmcli connection up "eth0-static"

# Verify
ip addr show eth0
ping 8.8.8.8

    "ansible-control" = "192.168.100.5"
    "splunk-mgmt"     = "192.168.100.10" 
    "splunk-idx1"     = "192.168.100.11"
    "splunk-idx2"     = "192.168.100.12"
    "splunk-sh1"      = "192.168.100.13"
    "splunk-sh2"      = "192.168.100.14"
    "splunk-sh3"      = "192.168.100.15"
    "splunk-hf1"      = "192.168.100.16"
    "splunk-hf2"      = "192.168.100.17"


# Give hostname to each VM
sudo hostnamectl set-hostname splunk-idx1

Verify with:
hostnamectl status 

Make it effective with:
sudo systemctl restart systemd-hostnamed 

2. Making those names resolvable

SSH by name only works if your client can turn “splunk-idx1” → 192.168.100.11. You have two main options:
A) Edit /etc/hosts on each machine (or at least on your Ansible control)

On every server (and your laptop/Ansible‑control if you SSH from there), add lines to /etc/hosts:

# /etc/hosts
192.168.100.5    ansible-control
192.168.100.10   splunk-mgmt
192.168.100.11   splunk-idx1
192.168.100.12   splunk-idx2
192.168.100.13   splunk-sh1
192.168.100.14   splunk-sh2
192.168.100.15   splunk-hf


# Install the role (if using requirements.yml)
ansible-galaxy install -r requirements.yml --roles-path roles/

# Run the playbook
ansible-playbook -i inventory.yml splunk-standalone.yml --ask-vault-pass

# Or if you have a vault password file
ansible-playbook -i inventory.yml splunk-standalone.yml --vault-password-file ~/.vault_pass