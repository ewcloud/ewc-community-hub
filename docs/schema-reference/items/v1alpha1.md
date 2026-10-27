# EWC Community Hub Catalog

Schema for `items.yaml`, the catalog of items offered in the EWC Community Hub.

### Type: `object`

> ⚠️ Additional properties are not allowed.

| Property | Type | Required | Possible values | Deprecated | Default | Description | Examples |
| -------- | ---- | -------- | --------------- | ---------- | ------- | ----------- | -------- |
| apiVersion | `const` | ✅ | `communityhub.europeanweather.cloud/v1alpha1` |  |  | Version of the catalog API this document conforms to. Must match this schema version. | ```communityhub.europeanweather.cloud/v1alpha1``` |
| kind | `const` | ✅ | `CommunityHubCatalog` |  |  | Type of the document. Always `CommunityHubCatalog`. |  |
| spec | `object` | ✅ | object |  |  | Catalog specification, holding all the items offered in the EWC Community Hub. |  |
| spec.items | `object` | ✅ | object |  |  | Map of catalog items. Each key is the item identifier and must equal the item's `name`. Each value follows the [item definition](#communityhubcatalogitem). |  |


---

# Definitions

## communityHubCatalogItem

Metadata describing a single item of the catalog: how it is presented in the Hub, who maintains and supports it, where its sources live and, optionally, how it is deployed.

#### Type: `object`

> ⚠️ Additional properties are not allowed.

| Property | Type | Required | Possible values | Deprecated | Default | Description | Examples |
| -------- | ---- | -------- | --------------- | ---------- | ------- | ----------- | -------- |
| annotations | `object` | ✅ | object |  |  | Classification metadata used by the Hub to list, filter and label the item, and to set support and licensing expectations. |  |
| annotations.licenseType | `string` | ✅ | string |  |  | SPDX full name of the license the item is distributed under. | ```Apache License 2.0```, ```MIT License``` |
| annotations.category | `string` | ✅ | [`.+`](https://regex101.com/?regex=.%2B) |  |  | Catalog category the item is listed under in the Hub, used for browsing and filtering. | ```Compute```, ```Dataset``` |
| annotations.others | `string` |  | [`.+`](https://regex101.com/?regex=.%2B) |  |  | Comma-separated free-form tags, for example whether the item is deployable or EWCCLI-compatible. | ```Deployable,EWCCLI-compatible``` |
| annotations.supportLevel | `string` | ✅ | `EWC` `Community` |  |  | Support commitment offered by the item owner. EWC means supported by the EWC team; Community means best-effort by the maintainers. | ```Community``` |
| annotations.technology | `string` | ✅ | [`.+`](https://regex101.com/?regex=.%2B) |  |  | Technology the item is implemented with, which determines how it is deployed. | ```Ansible Playbook```, ```Terraform Module``` |
| displayName | `string` | ✅ | string |  |  | Human-friendly name of the item shown in the Hub. Unlike `name`, it may contain spaces and capital letters. | ```My Item``` |
| description | `string` | ✅ | string |  |  | Full description of the item shown on its detail page. Multi-line text is allowed, and may include usage notes and a list of customizable variables. | ```My first ever Item contributed to the EWC Community Hub.``` |
| home | `string` | ✅ | [`^https://[\w\-\./:#?=&%]+$`](https://regex101.com/?regex=%5Ehttps%3A%2F%2F%5B%5Cw%5C-%5C.%2F%3A%23%3F%3D%26%25%5D%2B%24) |  |  | HTTPS URL of the item's home page, usually its location in the source repository. | ```https://my-public-git-server.com/my-repo``` |
| license | `string` | ✅ | Format: [`uri`](https://json-schema.org/understanding-json-schema/reference/string#built-in-formats) |  |  | HTTPS URL of the license file in the source repository. | ```https://my-public-git-server.com/my-repo/blob/main/LICENSE``` |
| icon | `string` | ✅ | [`^https://[\w\-\./:#?=&%]+$`](https://regex101.com/?regex=%5Ehttps%3A%2F%2F%5B%5Cw%5C-%5C.%2F%3A%23%3F%3D%26%25%5D%2B%24) |  |  | HTTPS URL of the image used as the item's icon in the Hub. | ```https://raw.my-public-git-server.com/my-repo/refs/heads/main/icon.png``` |
| maintainers | `array` | ✅ | object |  |  | People or organizations responsible for the item and its support. |  |
| maintainers[].name | `string` | ✅ | string |  |  | Name of the person or organization. | ```EWC Team``` |
| maintainers[].email | `string` or `null` |  | Format: [`email`](https://json-schema.org/understanding-json-schema/reference/string#built-in-formats) |  | `null` | Support contact email. At least one of `email` or `url` must be set. | ```support@example.org``` |
| maintainers[].url | `string` or `null` |  | [`^https://[\w\-\./:#?=&%]+$`](https://regex101.com/?regex=%5Ehttps%3A%2F%2F%5B%5Cw%5C-%5C.%2F%3A%23%3F%3D%26%25%5D%2B%24) |  | `null` | HTTPS URL where users can get support, such as the issue tracker. At least one of `email` or `url` must be set. | ```https://my-public-git-server.com/my-repo/issues``` |
| name | `string` | ✅ | string |  |  | Unique identifier of the item. Must equal the key under which the item is defined in `spec.items`. | ```my-item``` |
| published | `boolean` | ✅ | boolean |  |  | If true, the item is visible in the Hub catalog. | ```True``` |
| sources | `array` | ✅ | string |  |  | Remote location where the item is hosted. If is a source code Item, this should Git repository URLs. Mirrors can be listed as additional entries. |  |
| summary | `string` | ✅ | string |  |  | One-line summary shown on the catalog card. | ```My 1st EWC Community Hub Item``` |
| version | `string` | ✅ | [`^\d+\.\d+(\.\d+)?$`](https://regex101.com/?regex=%5E%5Cd%2B%5C.%5Cd%2B%28%5C.%5Cd%2B%29%3F%24) |  |  | Version of the item, as `MAJOR.MINOR` or `MAJOR.MINOR.PATCH`. | ```0.0.1```, ```2.0``` |
| values | `object` |  | object |  |  | Deployment configuration consumed by deployment tools like Ansible, Terraform, EWCCLI, etc., and by CI test automation. Supersedes deprecated `ewccli` sub-attributes. |  |
| values.inputSpec | `array` |  | object |  |  | Inputs a user can set when deploying the item. Each entry declares one input, its type and, optionally, a default value. |  |
| values.inputSpec[].name | `string` | ✅ | string |  |  | Name of the input. For Items compatible with the EWCCLI, users can set it at deployment time by passing the `--item-inputs name=value` argument. | ```users_file``` |
| values.inputSpec[].description | `string` | ✅ | string |  |  | Explanation of the input shown to users, including the expected format. | ```Path to a YAML file listing the users to create.``` |
| values.inputSpec[].type | `string` | ✅ | string |  |  | Data type of the input, as a short type name. | ```str``` |
| values.inputSpec[].required | `boolean` | ✅ | boolean |  | `false` | If true, the corresponding input value should always be set. |  |
| values.inputSpec[].default | `boolean` or `number` or `string` or `null` |  | boolean and/or number and/or string |  |  | Value used when the user does not provide one. |  |
| values.inputSpec[].sensitive | `boolean` |  | boolean |  | `false` | If true, the input is treated as a secret, masked during prompting or logging. |  |
| values.outputSpec | `array` |  | object |  |  | Outputs the item produces once deployed, to be reported to the user. Each entry declares one output and its type. |  |
| values.outputSpec[].name | `string` | ✅ | string |  |  | Name of the output. | ```server_url``` |
| values.outputSpec[].description | `string` | ✅ | string |  |  | Explanation of the output shown to users, such as how to use the value. | ```URL where the deployed service is reachable.``` |
| values.outputSpec[].type | `string` | ✅ | string |  |  | Data type of the output, as a short type name. | ```str``` |
| values.pathToRequirementsFile | `string` |  | string |  |  | Path, relative to the root of the item's sources, of the file listing dependencies to install before deployment, such as an Ansible Galaxy requirements file. | ```requirements.yml``` |
| values.pathToMainFile | `string` |  | string |  |  | Path, relative to the root of the item's sources, of the main file to run to deploy the item, such as the Ansible playbook. If unset, EWCCLI asks the user to provide it. | ```playbooks/my_item.yml``` |
| values.osFlavorName | `string` |  | string |  |  | Name of the OpenStack flavor (virtual machine size) used to create the server. To learn about available options, checkout the [official EWC VM plans documentation](https://confluence.ecmwf.int/x/evWHEw). | ```eo1.medium``` |
| values.osImageName | `string` |  | string |  |  | Name of the OpenStack image used to create the server. For complete information on available options, see the [official EWC Images documentation](https://confluence.ecmwf.int/x/pU2xG). | ```Ubuntu-24.04-20260519071420```, ```Ubuntu-24.04``` |
| values.osSecurityGroups | `array` |  | string |  |  | Names of the OpenStack security groups attached to the server, which control the network traffic allowed to reach it. |  |
| values.pythonVersion | `string` |  | string |  |  | Python version required to run the item's deployment tooling. | ```3.12``` |
| values.ansibleVersion | `string` |  | string |  |  | Ansible version required to run the item's playbook. | ```11.0.0``` |
| values.ansibleUser | `string` |  | string |  |  | Operating system default user which Ansible impersonates when connecting over SSH to configure the target host. Please check [EWC Virtual Images Available](https://confluence.ecmwf.int/x/pU2xG) for details. | ```ubuntu``` |
| ewccli | `object` |  | object |  |  | EWCCLI-specific settings. Only `externalIP` and `checkDNS` are current; every other attribute is deprecated in favor of `values`. |  |
| ewccli.externalIP | `boolean` |  | boolean |  |  | If true, the server is assigned an external IP address so that it is reachable from outside the tenant network. | ```False``` |
| ewccli.checkDNS | `boolean` |  | boolean |  |  | If true, EWCCLI checks the DNS record of the server before or after deployment. | ```False``` |
| ewccli.pathToMainFile | `string` |  | string | ⛔️ |  | Deprecated: use `values.pathToMainFile` instead. |  |
| ewccli.pathToRequirementsFile | `string` |  | string | ⛔️ |  | Deprecated: use `values.pathToRequirementsFile` instead. |  |
| ewccli.defaultImageName | `string` |  | string | ⛔️ |  | Deprecated: use `values.osImageName` instead. |  |
| ewccli.defaultSecurityGroups | `array` |  | string | ⛔️ |  | Deprecated: use `values.osSecurityGroups` instead. |  |
| ewccli.inputs | `array` |  | object | ⛔️ |  | Deprecated: use `values.inputSpec` instead. |  |
| ewccli.inputs[].name | `string` | ✅ | string | ⛔️ |  | Name of the input. |  |
| ewccli.inputs[].description | `string` | ✅ | string | ⛔️ |  | Explanation of the input shown to users, including the expected format. |  |
| ewccli.inputs[].type | `string` | ✅ | string | ⛔️ |  | Data type of the input, as a short type name. |  |
| ewccli.inputs[].default | `boolean` or `number` or `string` or `null` |  | boolean and/or number and/or string | ⛔️ |  | Value used when the user does not provide one. If present, the input is optional. |  |


---

Markdown generated with [jsonschema-markdown](https://github.com/elisiariocouto/jsonschema-markdown).
