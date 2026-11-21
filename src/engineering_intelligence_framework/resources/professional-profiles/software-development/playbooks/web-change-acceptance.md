# Accept a web interface change

Use this optional playbook when a task changes what someone sees or does in
a web interface. A copy-only fix can use the light route and a focused view
check. A server-only change with unchanged visible behavior uses the core
workflow and its service checks.

## Reuse the project's design sources

Record the existing token source, component entry point, and current source
revision in the task or launch file. Link the code, component catalog or
approved mockup that is authoritative for the changed surface. Reuse the
closest component. If a new component is needed, record the gap it fills and
update the existing catalog as part of the change.

## Connect criteria to the affected states

Record the route or user action, the visible states it can reach, the component
used in each state, and the native check that proves the criterion. Include
loading, empty, error, validation or success states when the requirement can
reach them. Use the project's existing evidence format.

| Criterion | User path and visible behavior | Sources and evidence |
|---|---|---|
| AC-04 | A request fails. The status explains the failure. The user reaches Retry with Tab and activates it with Enter. The view transitions through loading to success. | Reuse the action button and focus token. The browser check records focus and the success view after the failing request. |
| Service response | A scheduled task retries an internal service request without changing a user-facing route or state. | Verify the retry and response through the service entry point. The web playbook adds no artifact for this change. |

Record the exact revision and command in the result. An API check can
establish the response and network contract. A criterion about keyboard
interaction or visible behavior needs evidence from the interface. In an
orchestrated packet, return the unmet criterion to the executor and attach the
interface result to the subsequent review.
