# Enhanced Splunk Ansible Deployment

[![Ansible](https://img.shields.io/badge/ansible-%E2%89%A52.9-blue.svg)](https://www.ansible.com/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A streamlined and modular Ansible project for deploying Splunk Enterprise in clustered, distributed, and standalone configurations. This project has been refactored for better maintainability, modularity, and ease of use.

## 🚀 Quick Start

```bash
# Check current Splunk environment
ansible-playbook playbooks/check_splunk.yml -i environments/production/inventory.yml

# Install/upgrade Splunk software
ansible-playbook playbooks/install_splunk.yml -i environments/production/inventory.yml

# Deploy applications
ansible-playbook playbooks/deploy_apps.yml -i environments/production/inventory.yml

# Complete deployment (all phases)
ansible-playbook playbooks/check_install_deploy_apps.yml -i environments/production/inventory.yml
```

## 📋 Table of Contents

- [Architecture](#-architecture)
- [Modular Playbooks](#-modular-playbooks)
- [App Deployment Strategy](#-app-deployment-strategy)
- [Usage Examples](#-usage-examples)
- [Configuration](#-configuration)
- [Custom Roles](#-custom-roles)
- [Best Practices](#-best-practices)
- [Troubleshooting](#-troubleshooting)

## 🏗️ Architecture

This project is built around the official [ansible-role-for-splunk](https://github.com/splunk/ansible-role-for-splunk) with enhanced custom roles for advanced app deployment and management.

### Components

- **Core Role**: `roles/ansible-role-for-splunk` - Official Splunk role for installation and configuration
- **Custom Roles**: Enhanced functionality for app deployment and templating
  - `custom_roles/splunk_apps` - Enhanced app deployment with permission management
  - `custom_roles/deployment_server_sync` - Deployment server synchronization
  - `custom_roles/splunk_app_templates` - Template-based app generation

### Supported Deployments

- ✅ **Standalone** - Single instance deployments
- ✅ **Distributed** - Multi-component deployments (indexers, search heads, etc.)
- ✅ **Clustered** - Indexer clusters and search head clusters
- ✅ **Mixed** - Combination of clustered and distributed components

## 🎯 Modular Playbooks

The project now uses a modular approach with four core playbooks:

### 1. `check_splunk.yml`
**Purpose**: Comprehensive environment health check and configuration discovery

```bash
# Basic health check
ansible-playbook playbooks/check_splunk.yml -i inventory.yml

# Detailed check with verbose output
ansible-playbook playbooks/check_splunk.yml -i inventory.yml \
  -e check_verbosity=verbose --tags detailed

# Quick status check only
ansible-playbook playbooks/check_splunk.yml -i inventory.yml \
  -e check_verbosity=quiet --tags basic
```

**Features**:
- **Smart role detection** based on group membership and configuration
- **Universal Forwarder aware** - correct paths and checks for UF vs full Splunk
- **Detailed process information** - shows all running Splunk PIDs
- **Accurate disk usage** - shows actual Splunk directory size
- **Web interface testing** - properly detects accessibility per component type
- Configuration file analysis
- Service status validation
- App inventory

### 2. `install_splunk.yml`
**Purpose**: Install or upgrade Splunk software with proper ordering

```bash
# Complete installation
ansible-playbook playbooks/install_splunk.yml -i inventory.yml

# Install specific components only
ansible-playbook playbooks/install_splunk.yml -i inventory.yml \
  --tags "licensemaster,clustermanager"

# Upgrade existing installations
ansible-playbook playbooks/install_splunk.yml -i inventory.yml \
  -e force_upgrade=true --tags upgrade_only
```

**Features**:
- Phased deployment with proper dependencies
- Automatic clustering configuration
- Version validation and upgrade detection
- Component-specific deployment strategies

### 3. `deploy_apps.yml`
**Purpose**: Dynamic app deployment with role-based distribution

```bash
# Deploy all apps
ansible-playbook playbooks/deploy_apps.yml -i inventory.yml

# Deploy only search head apps
ansible-playbook playbooks/deploy_apps.yml -i inventory.yml \
  --tags searchheads

# Deploy without template generation
ansible-playbook playbooks/deploy_apps.yml -i inventory.yml \
  -e skip_templates=true

# Deploy with custom git settings
ansible-playbook playbooks/deploy_apps.yml -i inventory.yml \
  -e git_server=git@github.com:myorg \
  -e git_project=my-splunk-apps
```

**Features**:
- Automatic role-based app distribution
- Template generation and customization
- Splunkbase app merging
- Handler-based service management

### 4. `check_install_deploy_apps.yml`
**Purpose**: Complete orchestrated deployment

```bash
# Full deployment with all phases
ansible-playbook playbooks/check_install_deploy_apps.yml -i inventory.yml

# Skip initial checks
ansible-playbook playbooks/check_install_deploy_apps.yml -i inventory.yml \
  --tags "install,deploy" -e skip_check=true

# Apps deployment only
ansible-playbook playbooks/check_install_deploy_apps.yml -i inventory.yml \
  --tags apps_only
```

## 📱 App Deployment Strategy

### Splunk Apps Repository Structure

The project expects a `splunk-apps` repository with the following structure:

```
splunk-apps/
├── deploymentserver/     # Apps distributed via deployment server
│   ├── my-uf-app/
│   └── another-uf-app/
├── clustermaster/        # Apps for indexer clusters
│   ├── my-idx-app/
│   └── cluster-config/
├── shdeployer/          # Apps for search head clusters
│   ├── my-sh-app/
│   └── dashboards/
├── indexers/            # Apps for individual indexers
├── searchheads/         # Apps for individual search heads
├── standalone/          # Apps for standalone instances
└── splunk-app-templates/ # Template definitions
    ├── my-app-template/
    │   ├── app.yml
    │   └── default/
    └── another-template/
```

### App Deployment Flow

1. **Repository Clone**: Clone the splunk-apps repository
2. **Splunkbase Merge**: Merge large apps from `/home/jamel/splunkbase-apps/`
3. **Template Generation**: Generate apps from templates based on `app.yml` definitions
4. **Role-Based Distribution**: Deploy apps to appropriate Splunk components
5. **Handler Execution**: Trigger appropriate restart/reload handlers

### Template System

Apps can be generated from templates using an enhanced metadata format:

```yaml
# app.yml example
tenant: company1
business_unit: e-commerce
app_name: TestPaymentService
description: "Payment processing microservice"
team: "Backend Team"

# Indexer-specific configuration
indexers:
  indexes:
    payment_logs:
      max_data_size_mb: 2000
      retention_period: "90D"

# Search head apps
search_heads:
  app:
    - name: "payment-service-ops"
      template: "analytics-dashboard"
      template_vars:
        dashboard_title: "Payment Service Operations"

# Universal forwarder configuration
universal_forwarders:
  inputs_configs:
    "[monitor:///var/log/payment-service/*.log]":
      sourcetype: "payment_service_logs"
      index: "payment_logs"
```

## 🔧 Configuration

### Verbosity Controls

All playbooks support verbosity controls:

```yaml
# In group_vars or command line
check_verbosity: "normal"        # quiet, normal, verbose
install_verbosity: "normal"      # quiet, normal, verbose  
deploy_verbosity: "normal"       # quiet, normal, verbose
orchestrator_verbosity: "normal" # quiet, normal, verbose
```

### Custom Variables

```yaml
# Git repository settings
splunk_apps_git_server: "git@github.com:myorg"
splunk_apps_git_project: "splunk-apps"
splunk_apps_git_version: "main"

# Deployment options
skip_templates: false
splunkbase_merge: true
deployment_validation: true
setup_monitoring: false

# Force options
force_upgrade: false
force_reinstall: false
```

## 🛠️ Custom Roles

### Automatic Path Detection
All playbooks automatically detect the correct Splunk installation path:
- **Universal Forwarders**: `/opt/splunkforwarder` (when `universalforwarder` or `uf` in group_names)
- **Full Splunk**: `/opt/splunk` (default for all other components)
- **Custom Path**: Uses `splunk.home` variable if defined

### splunk_apps
Enhanced app deployment with namespaced handlers:

```yaml
# Usage
- include_role:
    name: splunk_apps
  vars:
    app_source_path: "/tmp/splunk-apps/searchheads"
    app_dest_path: "{{ splunk_home }}/etc/apps"
    splunk_component: "search_head"
```

**Handlers**: All prefixed with `splunk_apps:` to avoid conflicts

### deployment_server_sync
Deployment server synchronization:

```yaml
# Usage
- include_role:
    name: deployment_server_sync
  vars:
    sync_source: "/tmp/splunk-apps/deploymentserver"
```

**Handlers**: All prefixed with `deployment_sync:` to avoid conflicts

### splunk_app_templates
Template-based app generation:

```yaml
# Usage
- include_role:
    name: splunk_app_templates
  vars:
    app_templates_path: "/tmp/splunk-apps/splunk-app-templates"
    generated_apps_path: "/tmp/splunk-apps/searchheads"
    target_deployment_type: "searchheads"
```

## 📝 Usage Examples

### Environment-Specific Deployments

```bash
# Production deployment
ansible-playbook playbooks/check_install_deploy_apps.yml \
  -i environments/production/inventory.yml \
  -e orchestrator_verbosity=normal

# Standalone environment
ansible-playbook playbooks/check_install_deploy_apps.yml \
  -i environments/standalone/inventory.yml \
  -e orchestrator_verbosity=verbose
```

### Selective Component Deployment

```bash
# Deploy only to search heads
ansible-playbook playbooks/deploy_apps.yml \
  -i inventory.yml \
  --limit search \
  --tags searchheads

# Install only cluster managers and indexers
ansible-playbook playbooks/install_splunk.yml \
  -i inventory.yml \
  --tags "clustermanager,indexer"
```

### Maintenance Operations

```bash
# Health check all components
ansible-playbook playbooks/check_splunk.yml \
  -i inventory.yml \
  --tags detailed

# Upgrade check
ansible-playbook playbooks/install_splunk.yml \
  -i inventory.yml \
  --check \
  -e force_upgrade=true
```

## ⚙️ Best Practices

### 1. Use Verbosity Appropriately
- **quiet**: Automated deployments, minimal output
- **normal**: Regular operations, balanced output
- **verbose**: Troubleshooting, maximum detail

### 2. Tag-Based Execution
Always use tags for selective operations:
```bash
# Good: Specific component deployment
ansible-playbook deploy_apps.yml --tags searchheads

# Avoid: Deploying everything when you need specific components
ansible-playbook deploy_apps.yml
```

### 3. Environment Separation
Keep environment-specific configurations separate:
```
environments/
├── production/
│   ├── inventory.yml
│   └── group_vars/
└── standalone/
    ├── inventory.yml
    └── group_vars/
```

### 4. Handler Namespacing
When creating custom handlers, always use role prefixes:
```yaml
# Good
- name: my_role: restart splunk
  
# Bad
- name: restart splunk
```

## 🐛 Troubleshooting

### Common Issues

1. **Handler Conflicts**
   ```bash
   # Check for duplicate handler names
   grep -r "name:" custom_roles/*/handlers/
   ```

2. **App Deployment Failures**
   ```bash
   # Verbose app deployment
   ansible-playbook deploy_apps.yml -e deploy_verbosity=verbose --tags validation
   ```

3. **Permission Issues**
   ```bash
   # Check app permissions
   ansible-playbook check_splunk.yml --tags detailed
   ```

### Debug Mode

```bash
# Enable maximum verbosity for troubleshooting
ansible-playbook playbooks/check_install_deploy_apps.yml \
  -i inventory.yml \
  -e orchestrator_verbosity=verbose \
  -vvv
```

### Validation

```bash
# Validate configuration without making changes
ansible-playbook playbooks/install_splunk.yml \
  -i inventory.yml \
  --check \
  --diff
```

## 📚 Legacy Documentation

The original documentation for VM setup, networking, and Splunkbase configuration has been moved to [LEGACY.md](LEGACY.md) for reference.

## 🤝 Contributing

1. Follow the established modular structure
2. Use proper handler namespacing
3. Include appropriate tags for selective execution
4. Add verbosity controls to new playbooks
5. Update this README with any new features

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.