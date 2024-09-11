import sys
import config_gen

# Define the hardcoded template files and their output names
TEMPLATES = {
    'template.setup.py': 'setup.py',
    'template.installer.wxs': 'installer.wxs',
    'template.version.py': 'version.py',
}

def replace_template(template_file, output_file, version):
    # Read the specified template file
    try:
        with open(template_file, 'r') as file:
            template_content = file.read()
    except FileNotFoundError:
        print(f"Error: Template file '{template_file}' not found.")
        sys.exit(1)

    # Replace the placeholders with actual values
    template_content = template_content.replace('{{version}}', version)
    template_content = template_content.replace('{{name}}', config_gen.NAME)
    template_content = template_content.replace('{{namelc}}', config_gen.NAMELC)
    template_content = template_content.replace('{{author}}', config_gen.AUTHOR)
    template_content = template_content.replace('{{author_email}}', config_gen.AUTHOR_EMAIL)
    template_content = template_content.replace('{{description}}', config_gen.DESCRIPTION)
    template_content = template_content.replace('{{url}}', config_gen.URL)
    template_content = template_content.replace('{{upgradecode}}', config_gen.UPGRADECODE)

    # Write the content to the corresponding output file
    with open(output_file, 'w') as file:
        file.write(template_content)

    print(f"{output_file} generated with version {version}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python generate_configuration.py <version>")
        sys.exit(1)

    version = sys.argv[1]

    # Loop through the hardcoded templates and generate the corresponding files
    for template_file, output_file in TEMPLATES.items():
        replace_template(template_file, output_file, version)
