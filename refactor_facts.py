import os
import re

targets = [
    'roles/common',
    'roles/webserver',
    'roles/database',
    'playbooks',
    '.ansible/roles/geerlingguy.docker',
    'examples',
    'molecule'
]

replacements = {
    r'\bansible_os_family\b': "ansible_facts['os_family']",
    r'\bansible_distribution\b': "ansible_facts['distribution']",
    r'\bansible_distribution_version\b': "ansible_facts['distribution_version']",
    r'\bansible_distribution_major_version\b': "ansible_facts['distribution_major_version']",
    r'\bansible_architecture\b': "ansible_facts['architecture']",
    r'\bansible_check_mode\b': "ansible_check_mode",
    r'\bansible_processor_vcpus\b': "ansible_facts['processor_vcpus']",
    r'\bansible_memtotal_mb\b': "ansible_facts['memtotal_mb']",
}

modified_files = []

for target in targets:
    if not os.path.exists(target):
        print(f"Warning: Target path {target} does not exist.")
        continue
    for root, dirs, files in os.walk(target):
        for file in files:
            if file.endswith(('.yml', '.yaml', '.j2', '.md')):
                file_path = os.path.join(root, file)
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                original_content = content
                for pattern, replacement in replacements.items():
                    content = re.sub(pattern, replacement, content)
                
                if content != original_content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    modified_files.append(file_path)
                    print(f"Modified: {file_path}")

print("\nSummary of modified files:")
for f in sorted(modified_files):
    print(f)
