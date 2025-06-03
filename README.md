# ewc-community-hub
EWC Community Hub

This repository hosts the structure of the items for the EWC Community Hub.

# Item structure

```yaml
unique-item-name:
  annotations: # (MANDATORY)
    licenseType: "Apache License 2.0"  # (MANDATORY)
    category: "Ansible Playbook" # Flexible values that will multiply as the community start contributing
    supportLevel: "EWC"  # (MANDATORY) EWC Or Community. INDICATE the level of assistance and maintenance provided.
    type: "Virtual Machines" # Takes on one of few possible values (i.e. Virtual Machines, Kubernetes Apps, Container Images, Notebooks, Saas & APIs, Datasets, Others)
  displayName: "EWC Flavour"  # (MANDATORY)
  description: # (MANDATORY) LONG DESCRIPTION OF THE ITEM's purpose, features, and functionality."
  home: https://github.com/ewcloud/ewc-flavours  # (MANDATORY) URL TO THE PUBLIC REPOSITORY
  license: https://github.com/ewcloud/ewc-flavours/blob/main/LICENSE # (MANDATORY) URL TO THE LICENSE (e.g. ).
  icon: "http://placehold.it/200"  # (MANDATORY) URL TO /logos in this repository or another pointer
  maintainers:  # (MANDATORY)
    - name: EWC Team
      email: support@ewcloud.int
      url: https://github.com/ewcloud/ewc-flavours/issues
  name: unique-item-name  # (MANDATORY)
  published: false  # (MANDATORY) if true item is published on the website, if false, created but only visible to admins
  sources:  # (MANDATORY)
    - https://github.com/ewcloud/ewc-flavours/blob/main/ecmwf-data-flavour.yml
  summary: "SHORT DESCRIPTION OF THE ITEM."  # (MANDATORY)
  version: "1.0.0" # (MANDATORY) Wrapping the version in quotes is highly recommended.
```
