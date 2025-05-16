## upload-private-artifact-action

This is a GitHub Action that can be used by workflows in the qualcomm-linux
organization to publish CI artifacts that aren't approved for public distribution.

## Quick Start

See the [unit test](.github/workflows/unit-test.yml) for examples.

## How It Works

The backend API is a simple serverless application that can handle PUT requests
from this service by:

 * Validating the `ACTIONS_RUNTIME_TOKEN` JWT. By specifying the permission `id-token: write`, the JWT will include an `oidc_extra` attribute that includes information for the active workflow such as run ID, attempt, and repository name. The backend can ensure the incoming request is valid.

 * Creating a [Signed URL](https://cloud.google.com/storage/docs/access-control/signed-urls) to an object store.


The flow looks something like:
```
    Action           FileServer           Google storage

    PUT foo.txt  ->  Validate JWT
                 <-  Generate Signed URL
    PUT ${URL} -----------------------------> foo.txt
```

## License

*upload-private-artifact-action* is licensed under the [BSD-3-clause License](https://spdx.org/licenses/BSD-3-Clause.html). See [LICENSE.txt](LICENSE.txt) for the full license text.
