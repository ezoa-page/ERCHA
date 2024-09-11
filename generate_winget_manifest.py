import sys
import config_gen
import version
import hashlib
import os

def compute_sha256(file_path):
    """Compute the SHA-256 hash of the specified file."""
    sha256_hash = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            # Read and update the hash in chunks of 4K
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)

def replace_template(template_file, output_file, release_version, installer_sha):
    """Replace the placeholders in the template with actual values."""
    # Read the specified template file
    try:
        with open(template_file, 'r') as file:
            template_content = file.read()
    except FileNotFoundError:
        print(f"Error: Template file '{template_file}' not found.")
        sys.exit(1)

    # Replace the placeholders with actual values
    template_content = template_content.replace('{{version}}', release_version)
    template_content = template_content.replace('{{name}}', config_gen.NAME)
    template_content = template_content.replace('{{namelc}}', config_gen.NAMELC)
    template_content = template_content.replace('{{author}}', config_gen.AUTHOR)
    template_content = template_content.replace('{{author_email}}', config_gen.AUTHOR_EMAIL)
    template_content = template_content.replace('{{description}}', config_gen.DESCRIPTION)
    template_content = template_content.replace('{{url}}', config_gen.URL)
    template_content = template_content.replace('{{upgradecode}}', config_gen.UPGRADECODE)
    template_content = template_content.replace('{{installersha}}', installer_sha)

    # Write the content to the corresponding output file
    with open(output_file, 'w') as file:
        file.write(template_content)

    print(f"{output_file} generated with version {release_version}")

if __name__ == "__main__":

    release_version = str(version.ercha_version)

    if not os.path.exists('winget/'+release_version):
        os.makedirs('winget/'+release_version)
    # Compute the SHA-256 hash of ERCHA.msi
    installer_sha = compute_sha256("ERCHA.msi")

    TEMPLATES = {
        'template.winget-version.yaml': 'winget/'+release_version+'/'+config_gen.AUTHOR+'.'+config_gen.NAME+'.yaml',
        'template.winget-locale.yaml': 'winget/'+release_version+'/'+config_gen.AUTHOR+'.'+config_gen.NAME+'.locale.en-US.yaml',
        'template.winget-installer.yaml': 'winget/'+release_version+'/'+config_gen.AUTHOR+'.'+config_gen.NAME+'.installer.yaml',
    }

    # Loop through the hardcoded templates and generate the corresponding files
    for template_file, output_file in TEMPLATES.items():
        replace_template(template_file, output_file, release_version, installer_sha)

