# Splunk App Templates Role

This Ansible role generates and deploys Splunk applications from Jinja2 templates with environment-aware configurations.

## Features

- **Environment-Aware**: Different configurations for production, staging, development
- **Multi-Tenant Support**: Support for multiple tenants and organizations
- **Conditional Templates**: Dynamic configurations based on host roles and environment
- **Team-Based Deployment**: Automatic targeting based on team and role
- **Variable Hierarchy**: Sophisticated variable merging from multiple sources

## Quick Start

### 1. Directory Structure
```
splunk-apps/
└── app-templates/
    └── monitoring_template/
        ├── app.yml                 # Template metadata
        ├── default/
        │   ├── server.conf.j2
        │   └── inputs.conf.j2
        └── metadata/
            └── default.meta.j2
```

### 2. Template Metadata (app.yml)
```yaml
---
app_name: "{{ tenant }}_{{ organization_name }}_{{ team_name }}_monitoring"
app_version: "1.0.0"
description: "Auto-generated monitoring app"

# Deployment targeting
splunk_roles:
  - search
  - indexer
  
# Environment targeting
environments:
  - production
  - staging

# Template variables
template_vars:
  log_level: INFO
  retention_days: 90
```

### 3. Template File Example
```ini
# default/server.conf.j2
[general]
serverName = {{ ansible_hostname }}

{% if environment == 'production' %}
# Production settings
pass4SymmKey = {{ vault_production_key }}
{% else %}
# Non-production settings
pass4SymmKey = {{ default_test_key }}
{% endif %}

{% if 'indexer' in group_names %}
[clustering]
mode = peer
master_uri = {{ splunk_uri_cm }}
{% endif %}
```

## Usage in Playbooks

### Standalone Usage
```yaml
- hosts: all
  roles:
    - role: splunk_app_templates
      vars:
        app_templates_path: "../splunk-apps/app-templates"
        cleanup_generated_apps: false
```

### With Splunk Installation
```yaml
- hosts: all
  roles:
    - role: ansible-role-for-splunk
      vars:
        deployment_task: check_splunk.yml
    - role: splunk_app_templates
```

## Variable Configuration

### Required Variables
Define these in `group_vars/all.yml`:
```yaml
tenant: "mycompany"
organization_name: "MyCompany"
team_name: "operations"
environment: "production"
```

### Automatic Variable Derivation
From hostname pattern `splunk-TENANT-TEAM-ROLE-NUM`:
```yaml
# group_vars/all.yml
tenant: "{{ inventory_hostname.split('-')[1] if inventory_hostname.split('-')|length >= 4 else 'default' }}"
team_name: "{{ inventory_hostname.split('-')[2] if inventory_hostname.split('-')|length >= 4 else 'default' }}"
organization_name: "{{ tenant | title }}_Corp"
```

### Environment-Specific Variables
```yaml
# group_vars/production.yml
environment: production
template_vars:
  log_level: WARN
  ssl_enabled: true
  backup_enabled: true

# group_vars/staging.yml  
environment: staging
template_vars:
  log_level: DEBUG
  ssl_enabled: false
  backup_enabled: false
```

## Template Features

### 1. Conditional Blocks
```ini
{% if environment == 'production' %}
# Production-only configuration
{% endif %}

{% if 'search' in group_names %}
# Search head specific settings
{% endif %}

{% if team_name == 'security' %}
# Security team specific settings
{% endif %}
```

### 2. Variable Hierarchy
Variables are merged in this order (highest to lowest precedence):
1. `additional_template_vars` (host_vars)
2. `template_vars` (group_vars) 
3. Environment-specific vars from app.yml
4. Base template_vars from app.yml
5. `default_template_vars` (role defaults)

### 3. Available Template Variables
All templates have access to:
- `ansible_hostname`, `inventory_hostname`
- `group_names`, `environment`
- `tenant`, `organization_name`, `team_name`
- `template_vars` (merged from all sources)
- `app_metadata` (from app.yml)
- `host_vars` (all host variables)

## App Metadata Reference

### Full app.yml Example
```yaml
---
app_name: "{{ tenant }}_{{ organization_name }}_{{ team_name }}_monitoring"
app_version: "1.0.0"
description: "Auto-generated monitoring app for {{ team_name }} team"

# Deployment targeting
splunk_roles:
  - search
  - indexer
  - heavyforwarder

# Specific host targeting (optional)
target_hosts:
  - splunk-sh1
  - splunk-sh2

# Environment targeting
environments:
  - production
  - staging

# Environment-specific variables
environments:
  production:
    template_vars:
      log_level: WARN
      ssl_enabled: true
      retention_days: 365
  staging:
    template_vars:
      log_level: DEBUG
      ssl_enabled: false
      retention_days: 30

# Base template variables
template_vars:
  monitoring_enabled: true
  alert_threshold: 1000
  custom_index: "{{ team_name }}_events"

# Dependencies (informational)
requires:
  - Splunk_TA_nix
  - ssl_enablement
```

## Role Variables

### Paths
- `app_templates_path`: Path to template directories (default: `../splunk-apps/app-templates`)
- `generated_apps_path`: Temporary generation path (default: `/tmp/generated-splunk-apps`)

### Processing Options
- `cleanup_generated_apps`: Clean up temporary files (default: `true`)
- `debug_enabled`: Enable debug output (default: `false`)

### Splunk Configuration
- `splunk_home`: Splunk installation path (default: `/opt/splunk`)
- `splunk_nix_user`: Splunk user (default: `splunk`)
- `splunk_nix_group`: Splunk group (default: `splunk`)

## Examples

### Multi-Environment Setup
```yaml
# group_vars/all.yml
tenant: "{{ inventory_hostname.split('-')[1] if inventory_hostname.split('-')|length >= 4 else 'default' }}"
team_name: "{{ inventory_hostname.split('-')[2] if inventory_hostname.split('-')|length >= 4 else 'default' }}"
organization_name: "{{ tenant | title }}_Corp"

# group_vars/production.yml
environment: production
template_vars:
  log_level: WARN
  compliance_enabled: true

# group_vars/staging.yml
environment: staging
template_vars:
  log_level: DEBUG
  test_mode: true
```

### Team-Specific Overrides
```yaml
# host_vars/splunk-acme-finance-sh1.yml
additional_template_vars:
  department: "finance"
  pci_compliance: true
  audit_level: "strict"
```

### Complex Template Example
```ini
# app-templates/compliance_monitoring/default/server.conf.j2
[general]
serverName = {{ ansible_hostname }}

{% if environment == 'production' %}
pass4SymmKey = {{ vault_production_key }}
{% else %}
pass4SymmKey = {{ default_test_key }}
{% endif %}

{% if team_name == 'finance' and template_vars.pci_compliance | default(false) %}
[pci_compliance]
enabled = true
audit_level = {{ template_vars.audit_level | default('normal') }}
{% endif %}

{% if 'indexer' in group_names %}
[clustering]
mode = peer
replication_port = {{ splunk_idxc_rep_port | default(9887) }}
{% endif %}

# Environment-specific tuning
{% if environment == 'production' %}
[performance]
max_searches = 100
search_timeout = 3600
{% elif environment == 'staging' %}
[performance]  
max_searches = 10
search_timeout = 300
{% endif %}
```

## Troubleshooting

### Debug Mode
Enable debug output to see variable merging:
```yaml
- role: splunk_app_templates
  vars:
    debug_enabled: true
```

### Common Issues

1. **Templates not found**: Check `app_templates_path` points to correct directory
2. **Apps not deploying**: Verify `splunk_roles` in app.yml match host groups
3. **Variable not available**: Check variable hierarchy and spelling
4. **Permission errors**: Ensure Ansible user can write to Splunk directories

### Validation
```bash
# Test template generation without deployment
ansible-playbook splunk_template_apps_only.yml --check

# Verify generated apps
ls -la /tmp/generated-splunk-apps/

# Check deployed apps
ansible all -m find -a "paths=/opt/splunk/etc/apps file_type=directory"
```

## Contributing

1. Add new features to task files
2. Update defaults/main.yml with new variables
3. Add examples to this README
4. Test with different environments and host configurations

## License

Apache 2.0