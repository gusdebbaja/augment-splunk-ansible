# Splunk App State Tracking System

## Overview

The `playbooks/state/` directory contains state tracking files that record which Splunk apps are managed by Ansible. This system enables safe, idempotent deployments and automated cleanup of orphaned apps.

### Why This Was Developed

This state tracking system solves several critical operational challenges:

1. **Idempotency**: Know what's already deployed to avoid unnecessary restarts
2. **Safe Cleanup**: Automatically remove apps that are no longer in source control
3. **Audit Trail**: Maintain chronological history of all deployments
4. **Multi-environment Support**: Track separate state per environment
5. **Drift Detection**: Compare desired state vs actual state across hosts

Without state tracking, Ansible would either:
- Deploy everything every time (causing unnecessary Splunk restarts)
- Leave orphaned apps on servers when removed from source control
- Lack visibility into deployment history

## Architecture

### State File Location

```
playbooks/state/
└── <environment>_managed_apps.yml
```

Examples:
- `playbooks/state/production_managed_apps.yml`
- `playbooks/state/dev_managed_apps.yml`
- `playbooks/state/test_managed_apps.yml`

### Workflow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Load Previous State (manage_app_state.yml)              │
│    • Read state file for current environment                │
│    • Initialize empty state if first run                    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 2. Deploy Apps (deploy_static_apps.yml, etc.)              │
│    • Deploy apps from source directories                    │
│    • Track which apps were deployed this run                │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 3. Cleanup Orphans (cleanup_orphaned_apps.yml)             │
│    • Compare previous state vs current deployment           │
│    • Identify apps that were managed but not deployed       │
│    • Remove orphaned apps (if cleanup_managed_apps=true)    │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│ 4. Update State (update_app_state.yml)                     │
│    • Record current deployment in state file                │
│    • Append to deployment history                           │
│    • Update last_deployment metadata                        │
└─────────────────────────────────────────────────────────────┘
```

## State File Schema

### Structure

```yaml
ansible_managed_apps:
  <hostname>:
    <deployment_path>:
      - app1
      - app2

deployment_history:
  - id: deploy-<timestamp>
    timestamp: <iso8601>
    host: <hostname>
    path: <deployment_path>
    apps:
      - app1
      - app2

last_deployment:
  id: deploy-<timestamp>
  timestamp: <iso8601>
  playbook: <playbook_path>
  user: <ansible_user>
  environment: <environment_name>
```

### Fields Explained

#### `ansible_managed_apps`
Current state of managed apps per host and deployment path.

**Deployment Paths:**
- `deployment-apps` - Deployment Server apps (pushed to forwarders)
- `master-apps` - Indexer Cluster Manager apps (pushed to indexers)
- `shcluster/apps` - Search Head Cluster Deployer apps (pushed to SHC members)
- `apps` - Standalone Search Head apps (local installation)

#### `deployment_history`
Chronological log of every deployment with:
- **id**: Unique deployment identifier (deploy-<epoch>)
- **timestamp**: ISO8601 timestamp of deployment
- **host**: Target host for this deployment
- **path**: Deployment path used
- **apps**: List of apps deployed in this operation

#### `last_deployment`
Metadata about the most recent deployment:
- **id**: Last deployment ID
- **timestamp**: When it occurred
- **playbook**: Which playbook executed it
- **user**: Who ran the playbook
- **environment**: Target environment

### Example State File

```yaml
ansible_managed_apps:
  splunk-mgmt:
    deployment-apps:
      - Splunk_TA_otel
      - augment_hec_inputs
      - deployment_client
      - ssl_enablement
    master-apps:
      - common_indexes
      - indexer_config
    shcluster/apps:
      - global-dashboards
  splunk-sh1:
    apps:
      - global-dashboards

deployment_history:
  - apps:
      - Splunk_TA_otel
      - augment_hec_inputs
    host: splunk-mgmt
    id: deploy-1759985134
    path: deployment-apps
    timestamp: '2025-10-09T04:45:34Z'
  - apps:
      - common_indexes
      - indexer_config
    host: splunk-mgmt
    id: deploy-1759985134
    path: master-apps
    timestamp: '2025-10-09T04:45:34Z'

last_deployment:
  environment: production
  id: deploy-1759985150
  playbook: /usr/bin/python3
  timestamp: '2025-10-09T04:45:50Z'
  user: root
```

## Task Files

### `manage_app_state.yml`
**Purpose**: Initialize state tracking for deployment run

**Key Functions:**
1. Sets state file path based on environment
2. Creates state directory if needed
3. Loads previous state from file
4. Initializes empty state for first run
5. Determines deployment path based on Splunk component type
6. Prepares data structures for tracking

**Location**: `custom_roles/splunk_apps/tasks/manage_app_state.yml:10-70`

### `update_app_state.yml`
**Purpose**: Record deployment results in state file

**Key Functions:**
1. Updates `ansible_managed_apps` with current deployment
2. Appends to `deployment_history` array
3. Updates `last_deployment` metadata
4. Writes state file back to disk

**Location**: `custom_roles/splunk_apps/tasks/update_app_state.yml:8-37`

### `cleanup_orphaned_apps.yml`
**Purpose**: Remove apps no longer managed by Ansible

**Key Functions:**
1. Compares previous state vs current deployment
2. Identifies orphaned apps (previously managed but not currently deployed)
3. Removes orphaned apps from Splunk directories
4. Requires `-e cleanup_managed_apps=true` for safety

**Formula**: `orphaned_apps = previously_managed - currently_deployed`

**Location**: `custom_roles/splunk_apps/tasks/cleanup_orphaned_apps.yml:9-51`

### `deploy_static_apps.yml`
**Purpose**: Deploy apps from static source directories

Integrates with state tracking by:
- Calling `manage_app_state.yml` to load previous state
- Tracking which apps are deployed in `apps_deployed_this_run`
- Calling `cleanup_orphaned_apps.yml` to remove orphans
- Calling `update_app_state.yml` to record results

### `deploy_templated_apps.yml`
**Purpose**: Deploy apps with Jinja2 template processing

Similar integration as `deploy_static_apps.yml` but for templated apps.

## Usage

### Normal Deployment

State tracking happens automatically during app deployment:

```bash
ansible-playbook playbooks/splunk_deploy_apps.yml
```

This will:
1. Load previous state
2. Deploy apps
3. Identify orphaned apps (but not remove them)
4. Update state

### With Orphan Cleanup

To actually remove orphaned apps:

```bash
ansible-playbook playbooks/splunk_deploy_apps.yml -e cleanup_managed_apps=true
```

This enables the removal of apps that were previously managed but are no longer in source control.

### Multi-Environment

Specify environment to use different state files:

```bash
ansible-playbook playbooks/splunk_deploy_apps.yml -e environment=dev
```

This uses `playbooks/state/dev_managed_apps.yml` instead of production.

### Debug Mode

Enable debug output to see state tracking details:

```bash
ansible-playbook playbooks/splunk_deploy_apps.yml -e debug_enabled=true
```

## Benefits

### 1. Idempotency
Only deploy apps that changed or are new. Prevents unnecessary Splunk restarts which can disrupt:
- Active searches
- Data forwarding
- Cluster operations

### 2. Safe Cleanup
When you delete an app from source control, Ansible will:
- Detect it's no longer managed
- Mark it as orphaned
- Remove it from Splunk (when cleanup enabled)

**Example Scenario:**
```
Day 1: Deploy app_foo
Day 2: Delete app_foo from git
Day 3: Run playbook with cleanup_managed_apps=true
Result: app_foo automatically removed from all Splunk servers
```

### 3. Audit Trail
The `deployment_history` provides:
- Complete chronological record
- Which apps were deployed when
- Which user ran the deployment
- Which hosts were affected

Useful for:
- Troubleshooting issues after deployments
- Compliance auditing
- Understanding change history

### 4. Drift Detection
Compare state file against actual Splunk directories to detect:
- Manual changes outside Ansible
- Apps deployed by other means
- Configuration drift

### 5. Rollback Capability
Historical state enables:
- Understanding what was deployed previously
- Identifying what changed between deployments
- Rolling back to previous app versions

## Safety Features

### 1. Opt-in Cleanup
Orphaned app removal requires explicit flag:
```bash
-e cleanup_managed_apps=true
```

Without this flag, orphaned apps are detected but NOT removed. This prevents accidental deletions.

### 2. Only Remove Ansible-Managed Apps
The system ONLY tracks and removes apps that Ansible deployed. Apps manually installed or deployed by other tools are never touched.

### 3. Per-Host, Per-Path Tracking
State is tracked separately for each:
- Host (splunk-mgmt, splunk-sh1, etc.)
- Deployment path (deployment-apps, master-apps, etc.)

This prevents cross-contamination between different Splunk components.

## Troubleshooting

### State File Corrupted

If the state file becomes corrupted:

1. Review the file: `playbooks/state/production_managed_apps.yml`
2. Fix YAML syntax errors
3. Or delete and let Ansible recreate on next run (loses history)

### Orphaned Apps Not Detected

Check:
1. Is `manage_app_state.yml` being called before deployment?
2. Is `update_app_state.yml` being called after deployment?
3. Is the state file being written correctly?

Enable debug mode to investigate:
```bash
ansible-playbook playbooks/splunk_deploy_apps.yml -e debug_enabled=true
```

### Apps Removed Unexpectedly

If apps are being removed that shouldn't be:

1. Check the state file to see what's tracked
2. Verify app names match exactly (case-sensitive)
3. Ensure you're using correct environment
4. Review deployment history to see what changed

### First Deployment After Implementing State Tracking

On the first run after adding state tracking:
- Previous state will be empty
- All apps will be deployed (as expected)
- No orphans will be detected
- Future runs will use this as baseline

## Related Documentation

- Splunk App Deployment: See main README.md
- Templating System: See docs on app templating
- Environment Configuration: See `environments/` directory structure

## Version History

- **Initial Implementation**: October 2025
  - Basic state tracking
  - Orphan detection and cleanup
  - Multi-environment support
  - Deployment history logging
