# ewc-community-hub
EWC Community Hub

This repository hosts the structure of the items for the EWC Community Hub.

# Item structure

## Mandatory metadata
Each item shall have the following mandatory parameter:

```yaml
items:
  ecmwf-data-flavour:
    contacts: "CONTACTS (e.g. email, Github issues, etc.)."
    description: "SHORT DESCRIPTION OF THE ITEM."
    description_long: "LONG DESCRIPTION OF THE ITEM's purpose, features, and functionality."
    license: "NAME OF THE LICENSE (e.g. Apache License 2.0)."
    license_url: "URL TO THE LICENSE (e.g. https://github.com/ewcloud/ewc-flavours/blob/main/LICENSE)."
    logo_url: "URL TO /logos in this repository or another pointer (e.g. http://placehold.it/200)."
    maintainer: "ORGANIZATION OR PERSON (e.g. EWC Team)"
    name: "NAME OF THE ITEM."
    repository_url: "URL TO THE PUBCLI REPOSITORY (e.g. https://github.com/ewcloud/ewc-flavours/tree/main)."
    support_level: "INDICATE the level of assistance and maintenance provided."
    tag_technology: 
      - "SEE BELOW FOR A COMPLETE LIST"
    tag_category:
      - "SEE BELOW FOR A COMPLETE LIST"
    version: "SOFTWARE VERSION"
```

### Tags for filters and categories

Tags provide different dimensions to browse and filter the content. Currently the following categories of filters are defined:

- `TECHNOLOGY` -> 
    - Ansible Playbooks
    - Terraform modules
    - Dataset

- `CATEGORY` -> 
    - Compute
    - Storage
    - Data Access

## Admins metadata

The following parameters are required by EWC admins for automations and tests:

```yaml
    _main_file_path:    # (OPTIONAL)PATH TO THE MAIN FILE (if any) e.g. ./ewc-ecmwf-flavours/data-flavour.yml)
    _inputs:    # (OPTIONAL)(LIST OF VARIABLES INPUTS for the templates (if any))
        - INPUT_1
        - INPUT_2
    _published: false   # (mandatory) false: item is created in the website but not published, true: item is create and published to the website
```
