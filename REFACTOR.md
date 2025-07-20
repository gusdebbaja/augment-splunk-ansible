While in general the ansible project works to install Splunk Enterprise in a clustered distributed deployment, it is quite messy. 

The current structure and the design of repo is the following: 
Use the open source Splunk role ansible-role-for-splunk to install Splunk. 
A limitation of 
Another limitation with that role is when it comes to installing Splunk apps, it expects one app per git repo and we want to create one repo for all splunk apps with the following structure. 

splunk-apps
- deploymentserver/
	- my-uf-app/
- clustermaster/
	- my-idx-app/
- shdeployer/
	- my-sh-app/
- indexers/
- searchheads/
- standalone/
- splunk-app-templates/
	- my-app-template/
		- app.yml
		- default/

First, this splunk-apps will not manage large files (not even with LFS). If a Splunk app has large files (like Splunk_TA_otel), the large files will be on the ansible control node under /home/jamel/splunkbase-apps/ where the app with the same name will be there and ansible will simply merge those large files with the splunk-apps cloned repo before rsyncing it to the appropriate target server. 

With deploymentserver/ folder containing apps that will be deployed via the deployment server. More specifically, these apps will be distributed in the serverclass that will be under environment/<env>/host_vars/splunk-dps.yml. These apps will be rsynced to deploymentserver and afterwards the handler "reload deployment server" is triggered.

Clustermanager/ folder will be used if the splunk deployment has an indexer cluster and these apps will be deployed to clustermanager and afterwards the handler "apply indexer cluster bundle"

shdeployer/ folder will be used if the splunk deployment has an searchhead cluster and these apps will be deployed to shdeployer and afterwards the handler "apply indexer cluster bundle"

indexers/ folder is for splunk deployment with individual indexers (not clustered) distributed environment. The apps will be rsynced to the indexer and splunk handler "restart splunk will be called". 

searchhead/ folder is for splunk deployment with individual search heads (not clustered) distributed environment. The apps will be rsynced to the search head and splunk handler "restart splunk" will be called. 

standalone/ is for standalone instances where all apps will be deployed to the single instance and then the "restart splunk" handler will be called. 

splunk-app-templates/ contain template splunk apps where app.yml contain variables that be populated. Below is an example of app.yml 

```
# ===============================================================================
# Enhanced App Template Example - Terraform-style format
# This example shows the new enhanced format supporting role-specific apps
# ===============================================================================
# Application metadata (similar to your Terraform example)
tenant: company1
business_unit: e-commerce
app_name: TestPaymentService
description: "Test payment processing microservice for e-commerce platform"
team: "Backend Team"
owner_email: "backend-team@company.com"
environment: "production"
classification: "high"
cost_center: "CC-12345"
app_version: "1.0.0"

# Base template variables available to all generated apps
template_vars:
  service_port: 8080
  log_retention_days: 90
  monitoring_enabled: true
  ssl_enabled: true

# Indexer-specific configuration
indexers:
  platform: enterprise
  indexes:
    payment_logs:
      max_data_size_mb: 2000
      retention_period: "90D"
      description: "Payment service application logs"
      max_hot_buckets: 10
      max_warm_buckets: 300
    payment_transactions:
      max_data_size_mb: 5000
      retention_period: "7Y"
      description: "Payment transaction records"
      max_hot_buckets: 15
      max_warm_buckets: 500
      enable_data_integrity_control: true

# Search head-specific apps
search_heads:
  app:
    - name: "payment-service-ops"
      template: "analytics-dashboard"
      template_vars:
        dashboard_title: "Payment Service Operations"
        search_indexes: "payment_logs,payment_transactions"
        alert_threshold: 100
    - name: "payment-service-security"
      template: "security-monitoring"
      template_vars:
        security_indexes: "payment_logs"
        threat_detection: true

# Universal forwarder configuration
universal_forwarders:
  inputs_configs:
    "[monitor:///var/log/payment-service/*.log]":
      sourcetype: "payment_service_logs"
      index: "payment_logs"
      disabled: "false"
      whitelist: "\.log$"

    "[monitor:///var/log/payment-service/transactions/*.json]":
      sourcetype: "payment_transactions"
      index: "payment_transactions"
      disabled: "false"
      whitelist: "\.json$"

  apps:
    - name: "security-data-collection"
      template_vars:
        tenant: "company1"
        app_name: "TestPaymentService"
        collection_interval: 60

# Heavy forwarder configuration (optional)
heavy_forwarders:
  processing_enabled: true

# Deployment server serverclass configuration
serverclasses:
  - "backend_team_api_servers"
  - "payment_service_nodes"
```

Another limitation of ansible-role-for-splunk is necessity to modify the group_vars when adding apps to splunk components, an example is shown below:
```
git_apps:
  - name: ssl_enablement
    app_relative_path: /common/ssl_enablement/
    git_server: "git@github.com:gusdebbaja"  
    git_project: "splunk-apps"               
    splunk_app_deploy_path: etc/apps
  - name: heavy_forwarder_apps
    git_server: "git@github.com:gusdebbaja" 
    git_project: "splunk-apps"               
    app_relative_path: /deployment_server/heavy_forwarders/
    splunk_app_deploy_path: etc/apps
```

but this is not needed when we have the splunk-apps repository structure above, because we can infer which component should have which app. 

Therefore, we have built a custom_role, which is a different implementation of ansible-role-for-splunk's way of managing splunk-apps. This changes mostly the implementation of configure_apps tasks within ansible-role-for-splunk. As not to reinvest the wheel, the custom role should be minimal and we should use ansible-role-for-splunk when possible. Finally, whenever we are using these custom roles in our playbooks, we may need use ansible-role-for-splunk handlers. we can do this by copy pasting the handlers of ansible-role-for-splunk but ideally we want to avoid copy pasting code. We may need to uise of the method above to selectively use handlers and tasks between the 2 roles. 
When you start mixing upstream roles and your own “tweaks” roles, the biggest headache you’ll run into is exactly what you describe: both roles shipping handlers with the same names, and Ansible treating all handler names as global. You have basically three paths forward:

---
## 1) Namespace your handlers (the “best practice”)
Give every handler a role-unique name. For example, in `roles/galaxy_role/handlers/main.yml`:
```yaml
# roles/galaxy_role/handlers/main.yml
- name: galaxy_role: restart foo
  service:
    name: foo
    state: restarted
```
…and in your own `roles/my_role/handlers/main.yml`:
```yaml
- name: my_role: restart foo
  service:
    name: foo
    state: restarted
```
Then everywhere you notify, use the fully-qualified handler name:
```yaml
- name: configure foo.conf
  template:
    src: foo.conf.j2
    dest: /etc/foo.conf
  notify:
    - galaxy_role: restart foo
    - my_role:   restart foo
```
**Pros:**
- Zero chance of collision
- Crystal-clear which role’s handler you’re firing
- Scales to tens of roles without name clashes
- 
**Cons:**
- Must refactor existing handler names (but IMHO, worth it for long-term maintainability)
---
## 2) Use `include_role` with `handlers_from`
Ansible 2.7+ lets you pull in a role’s handlers explicitly, so you can decide which set runs. For example, in your playbook or wrapper task:

```yaml
- hosts: all
  tasks:
    - name: run just the tasks of galaxy_role
      include_role:
        name: galaxy_role
        tasks_from: main

    - name: also load galaxy_role’s handlers
      include_role:
        name: galaxy_role
        handlers_from: main

    - name: run your custom role tasks
      include_role:
        name: my_role
        tasks_from: main

    - name: load my_role handlers
      include_role:
        name: my_role
        handlers_from: main
```

Then notifications in each role only fire the handlers you explicitly pulled in.
**Pros:**
- No refactoring of handler names
- Complete control over exactly which handlers get registered

**Cons:**
- A bit more verbose in your playbook or wrapper role
- You must remember to load handlers separately
---
## 3) Override in a dependent role
If your custom role really _is_ meant to tweak an existing role, you can make it a dependency of that role in its `meta/main.yml`. Ansible will then merge handlers in the order listed, and your last one will “win” when names collide:

```yaml
# roles/galaxy_role/meta/main.yml
dependencies:
  - role: my_overrides
```

In `roles/my_overrides/handlers/main.yml` you simply declare a handler with the _same_ name:

```yaml
- name: restart foo
  service:
    name: foo
    state: restarted
```

Because `my_overrides` comes _after_ the other handlers, its definition replaces the original.

**Pros:**
- Minimal changes to existing playbooks
- You keep the same “short” handler names

**Cons:**
- Implicit magic ordering; can be confusing later
- Still a global namespace, so any other role calling “restart foo” will hit your override

---

### Which approach to pick?
- **Greenfield or actively maintained upstream roles** → **Namespace** your handlers.
- **Quick fork or short-lived project** → Use **`include_role`** with `handlers_from`.
- **You’re truly “patching” an existing role** → Use **meta-dependencies** to override.

In most medium-to-large Ansible codebases I end up namespacing—yes, it feels verbose at first, but it pays back in zero handler collisions and crystal-clear playbooks.
. 

Finally, 

The playbooks should be modular in a sense that we must be able to leverage tags and --limit to selectively run playbooks for specific targets and specific use cases. 

For instance, having 1 master playbook that checks splunk installation, upgrade if version dont match, redeploy all app in one go is rarely what we want. 

Many times we just want to push some apps to some splunk component like search heads. for this reason, i recommend having these playbooks. 
- check_splunk.yml # Check splunk current environment and output information of how it is configured (systemd, etc..), what kind of deployment (clustered, distributed, etc..), etc... 
- install_splunk.yml # install splunk or upgrade splunk if its installed with lower version 
- deploy_apps.yml # deploy apps, this should be dynamic (meaning, we should be able to selectively deploy only search head apps  or clustermanager apps etc... maybe using tags or --limits).
- check_install_deploy_apps.yml # apply all above.

Playbooks currently are very verbose by default. it is good to have this verbosity when troubleshooting. but this should be toggleable. Ideally, we should be able to adjust verbosity levels via a variable or similar and also assign different verbosity level to different components, like deploy_apps for search heads, or install of universal forwarders etc...


it may be that the current ansible project has a lot of dead code and can be slimmed down, streamlined to adhere to the above structure and design. Remember to never modify code under roles/ansible-role-for-splunk. 