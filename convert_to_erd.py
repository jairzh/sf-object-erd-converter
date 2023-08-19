import os
import xml.etree.ElementTree as ET
import zipfile
import sys

# Check if a zip file or a folder is provided
if len(sys.argv) < 2:
    print("Please provide a path to a zip file or a folder as an argument.")
    sys.exit(1)

# Check if the keep_all_fields argument is provided
keep_all_fields = False
if len(sys.argv) > 2 and sys.argv[2].lower() == 'true':
    keep_all_fields = True


path = sys.argv[1]

# Unzip the file if a zip file is provided
if path.endswith('.zip'):
    with zipfile.ZipFile(path, 'r') as zip_ref:
        zip_ref.extractall()
    path = '.'

# Walk through the unzipped directory and get all XML files
object_files = []
field_files = []
for root, dirs, files in os.walk(path):
    if "__MACOSX" in root:  # ignore __MACOSX folder
        continue
    for file in files:
        if file.endswith('object-meta.xml'):
            object_files.append(os.path.join(root, file))
        elif file.endswith('field-meta.xml'):
            field_files.append(os.path.join(root, file))

# Define a function to extract 'label' from an object file


def parse_object_file(file_path):
    # Parse the XML file
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Find the 'label' element
    label_element = root.find(
        './/{http://soap.sforce.com/2006/04/metadata}label')

    # Return the 'label' value
    return label_element.text.replace(" ", "") if label_element is not None else None


# Extract data from each object file
objects_data = [parse_object_file(file_path) for file_path in object_files]

# Define a function to extract 'label', 'type', and 'referenceTo' from a field file


def parse_field_file(file_path):
    # Parse the XML file
    tree = ET.parse(file_path)
    root = tree.getroot()

    # Find the 'label', 'type', and 'referenceTo' elements
    label_element = root.find(
        './/{http://soap.sforce.com/2006/04/metadata}label')
    type_element = root.find(
        './/{http://soap.sforce.com/2006/04/metadata}type')
    reference_to_elements = root.findall(
        './/{http://soap.sforce.com/2006/04/metadata}referenceTo')

    # Extract 'referenceTo' values
    reference_to = [element.text.replace("__c", "")
                    for element in reference_to_elements]

    # Extract object name from the file path
    object_name = os.path.basename(os.path.dirname(
        os.path.dirname(file_path))).replace("__c", "")

    # Return the 'label', 'type', 'referenceTo', and 'objectName' values
    return {
        'label': label_element.text.replace(" ", "") if label_element is not None else None,
        'type': type_element.text if type_element is not None else None,
        'referenceTo': reference_to,
        'objectName': object_name,
    }


# Extract data from each field file
fields_data = [parse_field_file(file_path) for file_path in field_files]

# Group fields by their respective objects
fields_by_object = {}
for field in fields_data:
    # If the object is not already in the dictionary, add it
    if field['objectName'] not in fields_by_object:
        fields_by_object[field['objectName']] = []
    # Add the field to the object's list of fields
    fields_by_object[field['objectName']].append(field)

# Initialize a list to hold the relationship definitions
relationships = []

# Define the relationships
for fields in fields_by_object.values():
    for field in fields:
        for reference in field['referenceTo']:
            # Determine the relationship syntax based on the type
            if field['type'] == 'MasterDetail':
                relationship_syntax = '||--}|'
            elif field['type'] == 'Lookup':
                relationship_syntax = 'o|--o{'
            else:
                continue
            # Define the relationship
            relationships.append(
                f"  {reference} {relationship_syntax} {field['objectName']} : contains")

# Define the entities and their attributes without the 'class' keyword
entities_no_class = {}
for object_name, fields in fields_by_object.items():
    # Start the entity definition
    entity_definition = f"  {object_name} {{"
    # Add the attributes
    for field in fields:
        # ship if the field label contains (Obsolete)
        if "(Obsolete)" in field['label']:
            continue
        # if keep_all_fields is False, only keep relationship fields
        if not keep_all_fields and len(field['referenceTo']) == 0:
            continue
        # remove all not alphanumeric characters from the field label
        field['label'] = ''.join(ch for ch in field['label'] if ch.isalnum())
        entity_definition += f"\n    {field['type']} {field['label']}"
    # End the entity definition
    entity_definition += "\n  }"
    # Add the entity definition to the dictionary
    entities_no_class[object_name] = entity_definition

# Add 'erDiagram' at the beginning and combine the entity and relationship definitions to form the ER diagram source code
er_diagram_source_code_no_class = "erDiagram\n" + \
    "\n".join(list(entities_no_class.values()) + relationships)

os.makedirs('output', exist_ok=True)

# Write the mermaid code to a .txt file
with open("output/sf_object_erd_mermaid_code.txt", "w") as file:
    file.write(er_diagram_source_code_no_class)
