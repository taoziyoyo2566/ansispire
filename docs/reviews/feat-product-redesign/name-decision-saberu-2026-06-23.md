# Name Decision - Saberu

**Status**: Confirmed by user on 2026-06-23

## Decision

The product name is **Saberu**.

Use:

- `Saberu` for product/brand display.
- `saberu` for CLI commands, package names, service IDs, URLs, config prefixes,
  and machine-readable identifiers.
- `saberu.com` as the primary domain direction.

Do not use:

- `SABERU` as normal branding text.
- `SabeRu`, `SabeRU`, or other stylized capitalization.
- Translated brand names as primary names.

## Readability Strategy

The brand should stay readable across languages by keeping the word stable and
adding local help around it.

### Global rule

Always keep the Latin brand name:

```text
Saberu
```

Do not translate it into each locale. Instead, add a short pronunciation or
descriptor on first mention when helpful.

### Pronunciation helper

Use a simple syllable guide:

```text
Saberu (sa-be-ru)
```

For Chinese docs or UI onboarding:

```text
Saberu（读作：sa-be-ru）
```

If a Chinese sound hint is useful in a casual document, prefer:

```text
Saberu（读作：萨贝鲁）
```

Keep that as a helper only, not the product name.

### Descriptor pattern

Use a local-language descriptor after the name:

```text
Saberu - Multi-VPS automation cockpit
Saberu - 多 VPS 自动化管理控制台
```

The descriptor can be translated. The name should not be.

## Naming In Surfaces

| Surface | Form | Example |
|---|---|---|
| Product name | `Saberu` | `Welcome to Saberu` |
| Domain | `saberu.com` | `https://saberu.com` |
| CLI | `saberu` | `saberu vps add` |
| Config prefix | `saberu_` | `saberu_project_id` |
| Env prefix | `SABERU_` | `SABERU_API_TOKEN` |
| Service/container | `saberu-*` | `saberu-controller` |
| Docs title | `Saberu` | `Saberu Architecture` |

## Product Vocabulary

Use feature names that are descriptive, but keep them secondary to the brand:

- Saberu Core - platform/control core
- Saberu Flow - plans, runs, and execution flows
- Saberu Vault - credentials and secrets surface
- Saberu Lens - audit, logs, and explanations
- Saberu Forge - templates and service setup
- Saberu Guard - baseline, security checks, and remediation

These are optional product vocabulary labels, not required module names for the
first implementation.

## Rationale

`Saberu` is short, brandable, and not tied to Ansible, VPS, Semaphore, or any
specific implementation detail. It can start with personal multi-VPS
standardized management and still fit later provider, security, audit, and
planning capabilities.

The main readability risk is unfamiliar pronunciation. The mitigation is to
show `Saberu` consistently and add a lightweight pronunciation or translated
descriptor where needed.
