## 🚀 Summary
Refs: _link to or id of ticket_

Briefly describe the changes introduced in this PR.

## ✅ Changes

- [ ] Added feature / fixed bug / updated docs
- [ ] Refactored code / cleaned up
- [ ] Other (describe below)

## 📸 Screenshots / Demos (if applicable)

_Add screenshots, GIFs, or demo links to illustrate your changes._

## 🧪 Testing

Explain what has been tested and how.

- [ ] Unit tests AI Repo
- [ ] Unit tests Monorepo `assistants core`
- [ ] Smoke test Monorepo `assistants core`

## ⛙ Merging workflow process
Once you have finished developing your feature and done **all** the testing listed above you can perform the process below

1. Open PR against `Unique-AG/ai`
2. Get review and fix any requested changes
3. Merge PR
4. Wait for publish to PyPI action to complete
5. Create PR for `Unique-AG/monorepo` bumping the version
6. Follow procedure for release in `monorepo`

**The work is not completed til version is increased in monorepo and synced to prod**

## ❔ Q & A
### How to test against Monorepo

1. Go to `monorepo/python/assistants/bundles/core/src/pyproject.toml`
2. Update sdk and/or toolkit to point to your branch
    * `unique-sdk= {git = "https://github.com/Unique-AG/ai/", rev = "<your-branch>", subdirectory="unique_sdk"}`
    * `unique-toolkit = {git = "https://github.com/Unique-AG/ai/", rev = "<hash>", subdirectory="unique_toolkit"}`
3. Run `poetry lock` then `poetry install`

Now `assistanst core` environment is pointing to your new version and you can do smoke test and unittests 

### Poetry in monorepo dosen't find the lastest version

There can be delays in synchronization due to Poetry's caching mechanism. Please allow up to 20 minutes before raising a concern.