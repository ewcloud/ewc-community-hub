# EWC Community Hub Items Catalog
This repository hosts the official catalog of [items](./items.yaml) offered in the [EWC Community Hub](https://europeanweather.cloud/about).

## Item's Metadata
> 💡 At least the `maintainers[*].email` or the `maintainers[*].url` property value should always be set.
These to ensure end-users of the item can submit inquiries or receive request support, in accordance with the support level offered by the maintainer(s).

The following example shows information that an onboarded item should typically include.
For detailed information on the required and optional metadata, checkout the [catalog schema](./schemas/catalog/v1alpha1.json).
```yaml
ecmwf-data-flavour:
  annotations:
    licenseType: "Apache License 2.0"
    category: Compute,Data Access
    supportLevel: EWC
    technology: Ansible Playbook
  displayName: EWC Flavour
  description: |
    # ECMWF data flavour
    Includes the basic ECMWF software stack, with MARS client and an environment with ecCodes, Metview, Earthkit and Aviso.

    ## Usage
    Example usage:
      ```bash
      ansible-playbook -i inventory ecmwf-data-flavour.yml
      ```
    ## Inputs
    You may use the following ansible variables to customize this playbook:

    - `reboot_if_required`: Boolean to reboot the instance if required after an update. Default: `true`
    - `ecmwf_toolbox_env_wipe`: Boolean to decide whether to wipe the environment if exists prior to a reinstallation. Default: `false`
    - `ecmwf_toolbox_env_name`: Name of the environment containing the ECMWF toolbox. Default: `ecmwf-toolbox`
    - `ecmwf_toolbox_create_ipykernel`: Boolean to create a system-wide kernel available. Default: `true`
    - `conda_prefix`: Prefix where conda is installed. Default: `/opt/conda`
    - `conda_user`: User owning the conda installation. Default: `root`
  home: https://github.com/ewcloud/ewc-flavours
  license: https://github.com/ewcloud/ewc-flavours/blob/main/LICENSE
  icon: https://raw.githubusercontent.com/ewcloud/ewc-community-hub/refs/heads/main/logos/EWCLogo.png
  maintainers:
    - name: EWC Team
      email: support@ewcloud.int
      url: https://github.com/ewcloud/ewc-flavours/issues
  name: ecmwf-data-flavour
  published: false
  sources:
    - https://github.com/ewcloud/ewc-flavours/blob/main/playbooks/ecmwf-data-flavour/ecmwf-data-flavour.yml
  summary: Includes the basic ECMWF software stack, with MARS client and an environment with ecCodes, Metview, Earthkit and Aviso.
  version: "1.0.0"
```

## Schema Validation
> 💡 To learn more about how you can onboard your item into the catalog, please check the [official EWC documentation](https://confluence.ecmwf.int/display/EWCLOUDKB/Contributing+a+new+Item+to+the+EWC+Community+Hub).

This repository relies on [GitHub](./.github/workflows/validate.yml) actions to automate the process of catalog/item metadata validation.
The pipelines are configured to run upon pull request opening, subject to approval of the maintainers.

### Running Locally

If you wish to validate changes to the metadata on your own, you can emulate the steps performed by the automation.
Make sure your working environment has [Docker](https://docs.docker.com/engine/install/) installed.
Then, to validate any changes in the metadata against the expected schema, simply run:

```bash
docker run --rm \
  -v .:/tmp:ro \
  weibeld/ajv-cli:5.0.0 \
  ajv \
  -s tmp/schemas/catalog/v1alpha1.json \
  -d /tmp/items.yaml \
  -c ajv-formats \
  --spec draft2020
```

If changes comply, you should see a successful run message like:
```
/tmp/items.yaml valid
```
