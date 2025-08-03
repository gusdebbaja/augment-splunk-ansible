# Ansible App State Tracking

This directory contains state files that track which Splunk apps are managed by Ansible.

## How It Works

### State Files
- **Format**: `{environment}_managed_apps.yml`
- **Examples**: 
  - `production_managed_apps.yml`
  - `development_managed_apps.yml`
  - `staging_managed_apps.yml`

### State Structure
```yaml
ansible_managed_apps:
  splunk-mgmt:
    manager-apps:
      - company1_testpaymentservice_indexer
      - company1_security-data-collection
    shcluster/apps:
      - company1_testpaymentservice_search
    deployment-apps:
      - company1_testpaymentservice_inputs
  splunk-sh1:
    apps:
      - standalone_app_example

last_deployment:
  id: deploy-1721567890
  timestamp: "2025-07-20T15:30:00Z"
  environment: production
  user: jamel

deployment_history:
  - id: deploy-1721567890
    timestamp: "2025-07-20T15:30:00Z"
    host: splunk-mgmt
    path: manager-apps
    apps:
      - company1_testpaymentservice_indexer
```

## Usage

### Safe Cleanup (Default)
```bash
# Deploy apps but don't remove orphaned ones
ansible-playbook deploy_apps.yml -i inventory.yml
```
- Deploys new/updated apps
- **Does NOT remove** apps deleted from repo
- Safe for production use

### Cleanup Mode
```bash
# Enable cleanup of orphaned ansible-managed apps
ansible-playbook deploy_apps.yml -i inventory.yml -e cleanup_managed_apps=true
```
- Deploys new/updated apps
- **Removes apps** that were previously deployed by Ansible but no longer in repo
- **Preserves** manually installed apps and built-in apps

## Safety Features

1. **Only Manages Ansible Apps**: Never touches manually installed or built-in apps
2. **Tracks History**: Full audit trail of deployments
3. **Environment Separation**: Separate state per environment
4. **Gradual Adoption**: Starts tracking from first deployment

## Example Scenario

1. **Initial Deployment**: App1, App2 deployed → State file tracks both
2. **Update Deployment**: App1 updated, App3 added → App1 updated, App3 deployed
3. **Cleanup Deployment**: Remove App2 from repo → Run with `cleanup_managed_apps=true` → App2 removed from Splunk

## Troubleshooting

### View Current State
```bash
cat state/production_managed_apps.yml
```

### Reset State (Emergency)
```bash
# Backup first!
cp state/production_managed_apps.yml state/production_managed_apps.yml.backup
# Remove state file to start fresh
rm state/production_managed_apps.yml
```

### Debug Mode
```bash
ansible-playbook deploy_apps.yml -i inventory.yml -e debug_enabled=true
```