# augment-splunk-ansible

# Install the role (if using requirements.yml)
ansible-galaxy install -r requirements.yml --roles-path roles/

# Run the playbook
ansible-playbook -i inventory.yml splunk-standalone.yml --ask-vault-pass

# Or if you have a vault password file
ansible-playbook -i inventory.yml splunk-standalone.yml --vault-password-file ~/.vault_pass