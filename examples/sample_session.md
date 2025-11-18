# Sample osint85 Session

This document shows a complete example session using osint85 for authorized reconnaissance.

## Scenario

You've been authorized to perform security reconnaissance on `example.com` as part of their bug bounty program.

## Session Walkthrough

### 1. Display Legal Disclaimer

```bash
$ osint85 disclaimer
```

**Output:**
```
╭──────────────────────── osint85 Disclaimer ────────────────────────╮
│ LEGAL AND ETHICAL USAGE DISCLAIMER                                │
│                                                                     │
│ osint85 is a tool for authorized security reconnaissance only.    │
│ ...                                                                │
╰────────────────────────────────────────────────────────────────────╯
```

### 2. Initialize Project

```bash
$ osint85 init \
  --name "Example Corp Bug Bounty" \
  --domain example.com \
  --scope "Bug bounty program - authorized by example.com/security" \
  --notes "In-scope: *.example.com, example.net. Out-of-scope: internal.example.com"
```

**Output:**
```
✓ Created project: Example Corp Bug Bounty (ID: 1)
  Domain: example.com
  Scope: Bug bounty program - authorized by example.com/security
```

### 3. Generate Dork Queries

```bash
$ osint85 dorks-generate \
  --goal "Comprehensive reconnaissance covering exposed backups, configuration files, staging environments, login portals, and API endpoints"
```

**Output:**
```
Generating dork queries for: Example Corp Bug Bounty
Goal: Comprehensive reconnaissance covering exposed backups...

✓ Generated 12 queries

                      Generated Queries
┏━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ID ┃ Category            ┃ Risk  ┃ Description              ┃
┡━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1  │ exposed_backups     │ high  │ Find backup archives     │
│ 2  │ exposed_backups     │ high  │ Find SQL dumps           │
│ 3  │ config_files        │ high  │ Find .env files          │
│ 4  │ config_files        │ medium│ Find config files        │
│ 5  │ staging_environments│ medium│ Find staging subdomains  │
│ 6  │ staging_environments│ medium│ Find dev subdomains      │
│ 7  │ login_portals       │ low   │ Find admin panels        │
│ 8  │ login_portals       │ low   │ Find login pages         │
│ 9  │ api_endpoints       │ medium│ Find API documentation   │
│ 10 │ api_endpoints       │ medium│ Find API endpoints       │
│ 11 │ exposed_directories │ medium│ Find directory listings  │
│ 12 │ debug_endpoints     │ high  │ Find debug/error pages   │
└────┴─────────────────────┴───────┴──────────────────────────┘
```

### 4. Review Queries

```bash
$ osint85 dorks-list
```

**Output:**
```
                            Dork Queries
┏━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ ID ┃ Enabled ┃ Category            ┃ Risk  ┃ Query                   ┃
┡━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 1  │ ✓       │ exposed_backups     │ high  │ site:example.com ext... │
│ 2  │ ✓       │ exposed_backups     │ high  │ site:example.com ext... │
│ 3  │ ✓       │ config_files        │ high  │ site:example.com ".env" │
...
```

### 5. Disable Unnecessary Queries (Optional)

If some queries are outside your scope:

```bash
$ osint85 dorks-toggle 11,12 --disable
```

**Output:**
```
✓ Query 11 disabled
✓ Query 12 disabled
```

### 6. Run Scan

```bash
$ osint85 scan --max-results 30 --delay 2.0
```

**Output:**
```
Starting scan for: Example Corp Bug Bounty
Queries: 10
Max results per query: 30

[1/10] Running query: Find backup archives
  Query: site:example.com ext:zip OR ext:tar OR ext:gz "backup"
  Found 5 results
[2/10] Running query: Find SQL dumps
  Query: site:example.com ext:sql OR ext:dump
  Found 2 results
[3/10] Running query: Find .env files
  Query: site:example.com ".env"
  Found 0 results
...
[10/10] Running query: Find API endpoints
  Query: site:example.com inurl:api
  Found 12 results

Scan complete: 67 results from 10 queries
✓ Scan complete
```

### 7. View Results Summary

```bash
$ osint85 report --summary
```

**Output:**
```
**Target:** Example Corp Bug Bounty (example.com)
**Queries:** 12 total, 10 enabled
**Results:** 67 total

**Results by Tag:**
- backup: 7
- config: 2
- dev_staging: 8
- login: 15
- debug: 3
```

### 8. Filter Results by Category

```bash
$ osint85 results-list --category exposed_backups --limit 20
```

**Output:**
```
                   Search Results (7 total)
┏━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ ID ┃ URL                          ┃ Tags     ┃ Seen       ┃
┡━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━┩
│ 1  │ https://backup.example.com/  │ backup   │ 2025-11-18 │
│ 2  │ https://example.com/old.zip  │ backup   │ 2025-11-18 │
│ 5  │ https://dev.example.com/back │ backup,  │ 2025-11-18 │
│    │ ups/                         │ dev_stag │            │
...
```

### 9. Generate Full Report

```bash
$ osint85 report --out reports/example-corp-2025-11-18.md
```

**Output:**
```
Generating report for: Example Corp Bug Bounty
✓ Report generated: reports/example-corp-2025-11-18.md
```

### 10. Review Report

```bash
$ cat reports/example-corp-2025-11-18.md
```

**Report Content:**
```markdown
---
Generated: 2025-11-18 14:32:15
Target: Example Corp Bug Bounty
Domain: example.com
Total Results: 67
---

# OSINT Reconnaissance Report

## Executive Summary

During authorized reconnaissance of example.com, we identified 67
potentially sensitive exposures across multiple categories. Key findings
include exposed backup files, staging environments, and several admin
login panels. All findings require manual verification.

## Findings by Category

### Exposed Backups
**Risk Level:** High

**URLs Found:**
- https://backup.example.com/ - Directory listing with database backups
- https://example.com/old.zip - Archive file containing old source code
- https://dev.example.com/backups/ - Staging environment backup directory

**Security Implications:**
These backup files may contain sensitive data including database dumps,
source code, and configuration information. If accessible without
authentication, this represents a critical security risk.

**Recommendations:**
- Remove public access to all backup directories
- Implement authentication for backup storage
- Use non-web-accessible locations for backups
- Encrypt all backup files
- Regularly audit exposed backup locations

### Staging Environments
**Risk Level:** Medium

**URLs Found:**
- https://staging.example.com/ - Staging environment
- https://dev.example.com/ - Development environment
- https://test.example.com/ - Test environment

**Security Implications:**
Staging and development environments often contain the same data
structures as production but with weaker security controls. They may
expose vulnerabilities not present in production.

**Recommendations:**
- Require authentication for all non-production environments
- Use separate data sets (no production data in staging)
- Implement IP whitelisting for dev/staging access
- Regular security scans of non-production environments

...

## Overall Recommendations

1. **Immediate Actions:**
   - Secure all exposed backup files and directories
   - Implement authentication on staging/dev environments
   - Review and restrict access to admin panels

2. **Short-term Actions:**
   - Conduct comprehensive security audit of findings
   - Implement web application firewall rules
   - Review robots.txt and security headers

3. **Long-term Actions:**
   - Regular automated security scanning
   - Security awareness training for developers
   - Implement secure development lifecycle practices

---
Report generated by osint85
```

### 11. List All Projects

```bash
$ osint85 projects
```

**Output:**
```
                     OSINT Projects
┏━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━┳━━━━━━━━━━━━┓
┃ ID ┃ Name                    ┃ Domain      ┃ Created    ┃
┡━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━╇━━━━━━━━━━━━┩
│ 1  │ Example Corp Bug Bounty │ example.com │ 2025-11-18 │
└────┴─────────────────────────┴─────────────┴────────────┘
```

## Next Steps

After generating the report:

1. **Manual Verification**: Verify each finding manually
2. **Risk Assessment**: Prioritize findings by risk level
3. **Responsible Disclosure**: Report findings according to program guidelines
4. **Documentation**: Keep records of authorization and findings
5. **Follow-up**: Track remediation of identified issues

## Testing Without API Calls

For testing or development, use the `--mock` flag:

```bash
$ osint85 scan --mock --max-results 10
```

This uses a mock search client that returns fake results without making actual API calls.

## Tips

- **Start Small**: Begin with a few targeted queries
- **Rate Limiting**: Use appropriate delays to respect API limits
- **Incremental Scans**: Run multiple targeted scans rather than one large scan
- **Regular Updates**: Re-run scans periodically to catch new exposures
- **Documentation**: Always document your authorization and scope

---

**Remember**: Only use osint85 on authorized targets!
