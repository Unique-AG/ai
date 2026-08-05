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
An explicitly justified exception to a failing configuration check, authorized by the designated DS-Engels approver authority.

**Override authorization**:
The combination of an eligible pull request, a valid override justification, and a current approval from a DS-Engels approver; inability to verify any part means the override is not authorized.

**Authorization attestation**:
A trusted, app-owned record bound to the current pull-request revision that confirms override authorization; it is distinct from the requester’s request and from the CI result.

**Override audit record**:
A single bot-maintained record on the pull request showing the authorized override's requester, approver, current revision, and where its justification can be found.

**Override revocation**:
The loss of any authorization condition; it makes the override inactive while retaining its audit record.

**DS-Engels approver**:
A member of `Unique-AG/ds-engels` who is authorized to approve a configuration-check override.

**Override requester**:
The pull-request author who explains the configuration risk in a dedicated authorization comment and accepts responsibility for requesting an override.

**Override request**:
The requester’s explicit indication that a configuration-check failure should be reviewed for an override; the request is not authorization by itself.

**Override justification**:
A non-empty explanation from the override requester describing what changed, why the configuration failure is believed safe to accept, and any relevant risk or follow-up.

**Current approval**:
The latest non-dismissed approval from a DS-Engels approver for the pull request's current revision.

**Override approval**:
At least one current approval from a DS-Engels approver other than the override requester.

**Eligible pull request**:
A pull request from an internal repository branch targeting `main` whose configuration-check failure is being considered for an authorized override.
