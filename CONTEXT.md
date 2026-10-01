# CI Configuration Safety

This context defines the language for reviewing and governing configuration compatibility changes.

## Language

**Configuration check**:
A review gate that determines whether a proposed change preserves compatibility of supported configuration schemas.

**Configuration-check failure**:
An explicit result from the configuration check indicating that a proposed change may be incompatible with an existing configuration schema.

**Gatekeeper decision**:
The trusted merge decision that all required checks are acceptable, with a configuration-check failure accepted only when override authorization is present.

**Configuration-check override**:
An exception to a failing configuration check, authorized when an eligible pull request has the `config-check-override` label and a current approval from a DS-Engels approver. Justification lives in normal PR review; no dedicated justification comment is required.

**Override authorization**:
The combination of an eligible pull request, the `config-check-override` label, and a current approval from a DS-Engels approver who is not the PR author; inability to verify any part means the override is not authorized (fail closed).

**Override audit record**:
A single bot-maintained record on the pull request showing the authorized override's PR author, approving DS-Engels reviewer, and current head SHA.

**Override revocation**:
The loss of any authorization condition; it makes the override inactive while retaining its audit record.

**DS-Engels approver**:
A member of `Unique-AG/ds-engels` who is authorized to approve a configuration-check override.

**Current approval**:
The latest non-dismissed review from a reviewer for the pull request's current head SHA is `APPROVED`.

**Override approval**:
At least one current approval from a DS-Engels approver other than the pull-request author.

**Eligible pull request**:
A pull request from an internal repository branch (not a fork) targeting `main` whose configuration-check failure is being considered for an authorized override.

## Operational notes

- Only a `config` job result of `failure` can be overridden; `cancelled` or unavailable results stay blocking.
- Any other failing or cancelled required check keeps Gatekeeper failing.
- After adding the label or approval, re-run Gatekeeper (or re-run failed jobs). There is no automatic re-dispatch on label/review events.
- CI reads the `config-check-override` label; it never creates or mutates labels. Create the label once in the repo if missing:
  `gh label create config-check-override --description "Authorize Gatekeeper to pass despite a config-check failure (requires DS-Engels approval)" --color B60205`
