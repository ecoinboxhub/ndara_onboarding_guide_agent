# Security Policy

## Deployment Security (Pip / Python)

### Upgrade pip (required before installing dependencies)

**Minimum recommended: pip ≥ 23.3** (covers the issues below).

```bash
pip install --upgrade pip
```

**Required:** (1) Upgrade pip as above. (2) For the tar/symlink fix, use a Python version that implements **PEP 706**:
   - Python **≥ 3.9.17**
   - Python **≥ 3.10.12**
   - Python **≥ 3.11.4**
   - Python **≥ 3.12**

**Optional:** Inspect source distributions (sdists) and wheel files (`.whl`) before installation if upgrading is not possible.

---

## Supported Versions

Use this section to tell people about which versions of your project are
currently being supported with security updates.

| Version | Supported          |
| ------- | ------------------ |
| 5.1.x   | :white_check_mark: |
| 5.0.x   | :x:                |
| 4.0.x   | :white_check_mark: |
| < 4.0   | :x:                |

## Reporting a Vulnerability

Use this section to tell people how to report a vulnerability.

Tell them where to go, how often they can expect to get an update on a
reported vulnerability, what to expect if the vulnerability is accepted or
declined, etc.
