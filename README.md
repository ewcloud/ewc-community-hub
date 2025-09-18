# EWC Community Hub Items Catalog
This repository hosts the official catalog of items offered in the [EWC Community Hub](https://europeanweather.cloud/community-hub).

## Item's Metadata
Below we show an excerpt from [items.yaml](items.yaml), to exemplify the metadata of an onboarded item.
For more details on required attributes, as well as optional ones (such as inputs specification for `ewccli` compatibility),
please refer to the items' metadata [schema definition](./schemas/items/v1alpha1.json).
```yaml
ecmwf-data-flavour:
  annotations:
    technology: "Ansible Playbook"
    category: "Compute,Data Access"
    supportLevel: "EWC"
    licenseType: "Apache License 2.0"
    others: "Deployable,EWCCLI-compatible"
  description: |
    Includes the basic ECMWF software stack, with MARS client and an environment with [ecCodes](https://github.com/ecmwf/eccodes), [Metview](https://metview.readthedocs.io/en/latest/index.html), [Earthkit](https://github.com/ecmwf/earthkit) and [Aviso](https://pyaviso.readthedocs.io/en/latest/).

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

  displayName: ECMWF Data Flavour
  ewccli:
    inputs:
      - name: reboot_if_required
        default: true
        description: Boolean to reboot the instance if required after an update.
        type: bool
      - name: ecmwf_toolbox_env_wipe
        default: false
        description: Boolean to decide whether to wipe the environment if exists prior to a reinstallation.
        type: bool
      - name: ecmwf_toolbox_env_name
        default: "ecmwf-toolbox"
        description: Name of the environment containing the ECMWF toolbox.
        type: str
      - name: ecmwf_toolbox_create_ipykernel
        default: true
        description: Boolean to create a system-wide kernel available.
        type: bool
      - name: conda_prefix
        default: "/opt/conda"
        description: Prefix where conda is installed.
        type: str
      - name: conda_user
        default: "root"
        description: User owning the conda installation.
        type: str
    pathToMainFile: playbooks/ecmwf-data-flavour/ecmwf-data-flavour.yml
    pathToRequirementsFile: requirements.yml
  home: https://github.com/ewcloud/ewc-flavours/tree/2.0.0/playbooks/ecmwf-data-flavour
  icon: https://raw.githubusercontent.com/ewcloud/ewc-community-hub/refs/heads/main/logos/EWCLogo.png
  license: https://github.com/ewcloud/ewc-flavours/blob/2.0.0/LICENSE
  maintainers:
    - name: EWC Team
      email: support@europeanweather.cloud
      url: https://github.com/ewcloud/ewc-flavours/issues
  name: "ecmwf-data-flavour"
  published: true
  sources:
    - https://github.com/ewcloud/ewc-flavours.git
  summary: Includes the basic ECMWF software stack, with MARS client and an environment with ecCodes, Metview, Earthkit and Aviso.
  version: "2.0.0"
```
>⛔ The attribute `name` within each item entry must always match the key under which the item's metadata is defined, to 
enforce uniqueness of all entries.

>⚠️ At least one of the `maintainers[*].email` or the `maintainers[*].url` attributes should be set.
These is to ensure end-users can submit inquiries or receive support, in accordance with the support level offered by Item owners.

## Schema Validation
> 💡 To learn more about how you can onboard your item into the catalog, please check the [official EWC documentation](https://confluence.ecmwf.int/display/EWCLOUDKB/Contributing+a+new+Item+to+the+EWC+Community+Hub).

This repository relies on [GitHub](./.github/workflows/validate.yml) actions to automate the process of catalog/item metadata validation.
The pipelines are configured to run upon pull request opening, subject to approval of the maintainers.

### Running Locally

If you wish to validate changes to the metadata on before opening a pull request, you can emulate the steps performed by the GitHub automation.
Make sure your working environment has [Docker](https://docs.docker.com/engine/install/) installed to
setup the validation tool locally (one time operation):

```bash
docker build --tag ewc/ajv-cli:5.0.0 .
```
Then, to validate any changes in the metadata against the expected schema, run:
```bash
docker run --rm --volume .:/tmp:ro \
  ewc/ajv-cli:5.0.0 \
  -s tmp/schemas/items/v1alpha1.json \
  -d /tmp/items.yaml \
  -c ajv-formats \
  --spec draft2020
```

If changes comply, you should see a successful run message like:
```
/tmp/items.yaml valid
```
