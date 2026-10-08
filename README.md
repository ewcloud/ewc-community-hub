# EWC Community Hub Items Catalog
This repository hosts the official catalog of items offered in the [EWC Community Hub](https://europeanweather.cloud/community-hub).

## Item's Metadata
Below we show an excerpt from [items.yaml](items.yaml), to exemplify the metadata of an onboarded item.
For more details on required attributes, as well as optional ones (such as inputs specification for deployment and `EWCCLI` compatibility),
please refer to the items' metadata [schema definition](./schemas/items/v1alpha1.json).

>⛔ The attribute `name` within each item entry must always match the key under which the item's metadata is defined, to 
enforce entry uniqueness.

```yaml
apiVersion: communityhub.europeanweather.cloud/v1alpha1
kind: CommunityHubCatalog
spec:
  items:
    my-item:
      annotations:
        category: "My Category"
        licenseType: "My Open Source License (SPDX full name)"
        others: "Deployable,EWCCLI-compatible"
        supportLevel: "Community"
        technology: "My Technology"
      displayName:  My Item
      description: |
        My first ever Item contributed to...
        the EWC Community Hub.

      ewccli:
        defaultSecurityGroups:
          - ssh
        externalIP: false
      home: https://my-public-git-server.com/my-repo
      license: https://my-public-git-server.com/my-repo/blob/main/LICENSE
      icon: https://raw.my-public-git-server.com/my-repo/refs/heads/main/icon.png
      maintainers:
        - email: name@organization.com
          name: my name or my organization
          url: https://my-public-git-server.com/my-repo/issues
      name: "my-item"
      published: true
      sources:
        - https://my-public-git-server.com/my-repo.git
        - https://my-public-git-server-mirror.com/my-repo.git
      summary:  My 1st EWC Community Hub Item
            values:
        inputSpec:
          - name: my_required_input
            description: "My required input."
            type: str
          - name: my_optional_input
            description: "My optional input. The default value implies this input is optional."
            type: str
            default: "my default value"
        osImageName: Ubuntu-24.04-20260519071420
        pathToRequirementsFile: path/to/my/requirements/file
        pathToMainFile: path/to/my/main/file
      version: "0.0.1"
```

>⚠️ At least one of the `maintainers[*].email` or the `maintainers[*].url` attributes should be set to ensure end-users can submit inquiries or receive support, in accordance with the support level offered by Item owners.

## Schema Validation
> 💡 To learn more about how you can onboard your item into the catalog, please check the [official EWC documentation](https://confluence.ecmwf.int/x/wyLOIQ).

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
