# Legacy Documentation

This document contains the original setup documentation that was previously in README.md.

## VM Network Setup

### Complete Windows Host Commands

#### Network Setup (One Time)
```powershell
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
```

#### Setup persistent IPs for VMs
SSH into each VM (use console if no network)
Replace XX with last octet (5 for ansible-control, 10 for splunk-mgmt, etc.)

Method 1: Using nmcli (preferred for RHEL 9)
```bash
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
```

### VM IP Addresses
```
"ansible-control" = "192.168.100.5"
"splunk-mgmt"     = "192.168.100.10" 
"splunk-idx1"     = "192.168.100.11"
"splunk-idx2"     = "192.168.100.12"
"splunk-sh1"      = "192.168.100.13"
"splunk-sh2"      = "192.168.100.14"
"splunk-sh3"      = "192.168.100.15"
"splunk-hf1"      = "192.168.100.16"
"splunk-hf2"      = "192.168.100.17"
```

### Hostname Configuration

Give hostname to each VM:
```bash
sudo hostnamectl set-hostname splunk-idx1
```

Verify with:
```bash
hostnamectl status 
```

Make it effective with:
```bash
sudo systemctl restart systemd-hostnamed 
```

### Name Resolution

Making those names resolvable
SSH by name only works if your client can turn "splunk-idx1" → 192.168.100.11.

Edit /etc/hosts on each machine (or at least on your Ansible control):

```
# /etc/hosts
192.168.100.5    ansible-control
192.168.100.10   splunk-mgmt
192.168.100.11   splunk-idx1
192.168.100.12   splunk-idx2
192.168.100.13   splunk-sh1
192.168.100.14   splunk-sh2
192.168.100.15   splunk-hf
```

## Splunkbase App Configuration

This playbook supports automatic downloading and deployment of Splunkbase apps with version control and best practices.

### Setup

1. **Configure Splunkbase credentials** in `environments/production/group_vars/all.yml`:
   ```yaml
   splunkbase_username: "your-email@domain.com"
   splunkbase_password: "your-password"
   ```

2. **Configure MinIO for app caching** (recommended):
   ```yaml
   minio_enabled: true
   minio_endpoint: "http://your-minio-server:9000"
   minio_access_key: "your-access-key"
   minio_secret_key: "your-secret-key"
   minio_bucket: "splunkbase-apps"
   minio_secure: false  # Set to true for HTTPS
   ```

3. **Add app folders** to your `splunk-apps` repository under the `splunkbase-apps/` subdirectory with an `app.yml` configuration file:
   ```
   splunk-apps/
   ├── splunkbase-apps/
   │   ├── splunk_ta_nix/
   │   │   └── app.yml
   │   ├── splunk_app_db_connect/
   │   │   └── app.yml
   │   └── splunk_ta_windows/
   │       └── app.yml
   └── custom_git_app/
       └── (regular git app files)
   ```

### App Configuration Format

Create an `app.yml` file in each Splunkbase app folder:

```yaml
---
name: "splunk_ta_nix"
source: "splunkbase"
splunkbase_id: 833
splunkbase_version: "8.1.0"
deployment_target: "all"
splunk_app_deploy_path: "etc/apps"
force_redownload: false
```

### Features

- **Version Control**: Only downloads when version changes
- **MinIO Caching**: Intelligent caching layer for fast, reliable downloads
- **Best Practices**: Automatically removes README/inputs.conf for search head deployments
- **Deployment Targets**: Supports all, search_head, indexer, forwarder
- **Force Redownload**: Option to force redownload for corrupted apps
- **No Repository Changes**: Add apps without modifying the main ansible repository
- **Multi-tier Fallback**: MinIO → Splunkbase → Local filesystem

### MinIO Integration (Recommended)

MinIO provides a robust caching layer that solves Splunkbase authentication issues:

**Benefits:**
- ✅ **Fast downloads** - Apps cached locally, no repeated Splunkbase downloads
- ✅ **Bypass authentication** - No more 403 errors from Splunkbase SAML changes
- ✅ **Multi-environment** - Share cached apps across dev/staging/prod
- ✅ **Version control** - Multiple versions stored with proper naming
- ✅ **Reliability** - Eliminates dependency on Splunkbase availability

**Download Hierarchy:**
1. **Check local version cache** - Skip if version already processed
2. **Try MinIO first** - Fast download from `splunkbase-apps/{app_name}/{version}.tgz`
3. **Fallback to Splunkbase** - If not cached, try direct download
4. **Upload to MinIO** - Cache successful Splunkbase downloads
5. **Final fallback** - Use existing `/home/jamel/splunkbase-apps` if all else fails

**MinIO Setup:**
```bash
# Install boto3 for aws_s3 module
pip install boto3

# Run MinIO server
docker run -p 9000:9000 -p 9001:9001 \
  --name minio \
  -e "MINIO_ROOT_USER=admin" \
  -e "MINIO_ROOT_PASSWORD=password" \
  -v /mnt/data:/data \
  minio/minio server /data --console-address ":9001"

# Create bucket via web console or CLI
mc alias set myminio http://localhost:9000 admin password
mc mb myminio/splunkbase-apps
```

**Disable MinIO:**
Set `minio_enabled: false` in group_vars to use traditional Splunkbase/filesystem fallback.

### Examples

See `examples/app.yml.example` for detailed configuration examples.

### Supported Deployment Targets

- `all`: Deploy to all target types (default)
- `search_head`: Deploy to search heads with best practices applied
- `indexer`: Deploy to indexers only
- `forwarder`: Deploy to forwarders only

When `deployment_target` is set to `search_head`, the system automatically:
- Removes README directory
- Removes default/inputs.conf
- Removes inputs.conf.spec files

## Legacy Playbook Usage

```bash
# Install the role (if using requirements.yml)
ansible-galaxy install -r requirements.yml --roles-path roles/

# Run the playbook
ansible-playbook -i inventory.yml splunk-standalone.yml --ask-vault-pass

# Or if you have a vault password file
ansible-playbook -i inventory.yml splunk-standalone.yml --vault-password-file ~/.vault_pass
```