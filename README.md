# Mintlify Starter Kit


### Docuemntacion autogenerada
```json
"tabs": [
  {
    "name": "API Reference",
    "url": "api-reference",
    "openapi": "https://api.wesog.com/openapi.json"
  }
]
```

### Docuemntacion manual
```json
"tabs": [
  {
    "name": "API Reference",
    "url": "api-reference",
    "openapi": "/openapi.yaml"
  }
]
```



Click on `Use this template` to copy the Mintlify starter kit. The starter kit contains examples including

- Guide pages
- Navigation
- Customizations
- API Reference pages
- Use of popular components

### Development

Install the [Mintlify CLI](https://www.npmjs.com/package/mintlify) to preview the documentation changes locally. To install, use the following command

```
npm i -g mintlify
```

Run the following command at the root of your documentation (where mint.json is)

```
mintlify dev
```

### Publishing Changes

Install our Github App to auto propagate changes from your repo to your deployment. Changes will be deployed to production automatically after pushing to the default branch. Find the link to install on your dashboard. 

#### Troubleshooting

- Mintlify dev isn't running - Run `mintlify install` it'll re-install dependencies.
- Page loads as a 404 - Make sure you are running in a folder with `mint.json`

## Customer API guides (new platform, `new/` and `es/new/`)

The "Nueva plataforma" version holds the documentation for customers who integrate with an API key:

- `new/` is English, `es/new/` is Spanish (same pages, same code). `new/quickstart`, `new/concepts/*` (authentication, errors, limits, pagination, async, idempotency) and `new/guides/*` (tag photos, search, Library, workflows, alerts, agents) are written by hand; `new/platform-api/*` are the generated tool pages.
- `new/openapi.json` is the **API reference**, generated from the code (only the operations we promise to keep stable, each with summary, description, examples, errors and cURL/Python/JavaScript samples). Regenerate it from core-api after any change to an endpoint:

  ```bash
  cd backend/services/core-api
  PYTHONPATH=src:. python scripts/export_customer_openapi.py ../../../documentation/new/openapi.json
  ```

  The same document is served live at `https://api.wesog.com/api/openapi-customer.json?server=public`.
- Validate before publishing (`npm i -g mint`): `mint validate` and `mint broken-links` (the "Actual" version's reference imports `https://api.wesog.com/openapi.json`, so run them with network access to that host), and `python3 scripts/check_examples.py` (every Python, JavaScript, shell and JSON block parses).
- Examples against a live API: export `WESOG_API_KEY` (a test key of a test organization) and run the quickstart commands in order; delete the key afterwards.
