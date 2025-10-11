# type safety

do not use any, unknown, or other escape hatches that disable type checking. If you need to use one of these, first try to improve the types so that you don't need to. If you really must use one of these, add a comment explaining why it's necessary and what the expected type is.

# fixing tests

When tests fail, treat the deployed/public API contract (and active frontend usage) as the source of truth. If tests diverge from that contract, update the tests. Only change backend behavior when a failure reveals a real bug, regression, or agreed product change. For intentional API changes, update the backend, frontend, and tests together in a single, coherent change. Document deviations and keep tests asserting the contract, not internal implementation details.
