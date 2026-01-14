# Effective policies with boundaries resolution 
When policy binding contains boundaries, then the effective policy is calculated according to the following rules:

- Only conditions added to [service configuration](https://bitbucket.lab.dynatrace.org/projects/COPS/repos/heimdall-dt-saas-managed/browse/service-definitions) will be applied to relative permissions. This rule doesn't apply to `global` conditions. Global conditions will be applied to all permissions
- When a boundary contains repeated condition names, then each policy statement is multiplied by such conditions. Each of the repeated conditions appears separately in each applicable statement.
- When more than one boundary applies to a policy, then effective statements are calculated for each boundary separately
- When a policy statement contains multiple permissions, then such a statement will be split into single permission statements
- Boundaries are applied to policy statements without evaluating the statement's condition. i.e. Boundary will be applied no matter if the statement already contains the same condition
- Boundaries don't apply to DENY statements


## Examples
### Boundary with conditions not found in service configuration

Boundary
```
settings:schemaId = "builtin:maintenance-windows";
settings:not-found-in-service-configuration = "1";
```
Policy
```
ALLOW settings:objects:read;
```
Effective policy
```
ALLOW settings:objects:read WHERE settings:schemaId = "builtin:maintenance-windows";
```

### Boundary with global condition

Boundary
```
settings:schemaId = "builtin:maintenance-windows";
global:week-day = "Monday";
```
Policy
```
ALLOW settings:objects:read;
ALLOW app-engine:apps:run;
```
Effective policy
```
ALLOW settings:objects:read WHERE settings:schemaId = "builtin:maintenance-windows" AND global:week-day = "Monday";
ALLOW app-engine:apps:run WHERE global:week-day = "Monday";
```

### Boundary contains repeated condition names

Boundary
```
settings:schemaId = "builtin:maintenance-windows";
settings:schemaId startsWith "custom";
settings:objectId = "1";
```
Policy
```
ALLOW settings:objects:read WHERE global:week-day = "Monday";
```
Effective policy
```
ALLOW settings:objects:read WHERE global:week-day = "Monday" AND settings:schemaId = "builtin:maintenance-windows" AND settings:objectId = 1;
ALLOW settings:objects:read WHERE global:week-day = "Monday" AND settings:schemaId startsWith "custom" AND settings:objectId = 1;
```

### Many boundaries apply to a policy

Boundary 1
```
settings:schemaId = "builtin:maintenance-windows";
settings:schemaId startsWith "custom";
settings:objectId = "1";
```
Boundary 2
```
settings:schemaId startsWith "dynatrace";
settings:objectId = "4";
```
Policy
```
ALLOW settings:objects:read WHERE global:week-day = "Monday";
ALLOW app-engine:apps:run;
ALLOW settings:objects:read;
```
Effective policy
```
//statements calculated for Boundary 1
ALLOW settings:objects:read WHERE global:week-day = "Monday" AND settings:schemaId = "builtin:maintenance-windows" AND settings:objectId = "1";
ALLOW settings:objects:read WHERE global:week-day = "Monday" AND settings:schemaId startsWith "custom" AND settings:objectId = "1";
ALLOW settings:objects:read WHERE settings:schemaId = "builtin:maintenance-windows" AND settings:objectId = "1";
ALLOW settings:objects:read WHERE settings:schemaId startsWith "custom" AND settings:objectId = "1";
//statements calculated for Boundary 2
ALLOW settings:obects:read WHERE global:week-day = "Monday" AND settings:schemaId startsWith "dynatrace" AND settings:objectId = "4";
ALLOW settings:obects:read WHERE settings:schemaId startsWith "dynatrace" AND settings:objectId = "4";
ALLOW app-engine:apps:run;
```

### Policy statement with many permissions

Boundary
```
settings:schemaId = "builtin:maintenance-windows";
settings:objectId = "4";
app-engine:appId = "application-id";
```
Policy
```
ALLOW settings:objects:read, settings:objects:write, app-engine:apps:run;
```
Effective policy
```
ALLOW settings:objects:read WHERE settings:schemaId = "builtin:maintenance-windows" AND settings:objectId = "4";
ALLOW settings:objects:write WHERE settings:schemaId = "builtin:maintenance-windows" AND settings:objectId = "4";
ALLOW app-engine:apps:run WHERE app-engine:appId = "application-id"
```

### Boundary has the same condition as in the policy

Boundary
```
settings:schemaId = "builtin:maintenance-windows";
```
Policy
```
ALLOW settings:objects:read settings:schemaId startsWith "test";
```
Effective policy
```
ALLOW settings:objects:read WHERE settings:schemaId startsWith "test" AND settings:schemaId = "builtin:maintenance-windows";
```

### Policy with DENY statement

Boundary
```
settings:schemaId = "builtin:maintenance-windows";
```
Policy
```
DENY settings:objects:read;
```
Effective policy
```
DENY settings:objects:read;
```


