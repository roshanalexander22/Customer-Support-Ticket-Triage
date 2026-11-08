# Technical Support and SLA Policy (POL-TECH-004)

## 1. Incident Severity Definitions & Response SLAs
NovaTech Technical Support categorizes all software, API, and platform incidents into four severity levels:
- **P1 - Critical Severity:** Complete production outage, system downtime, data corruption, or payment gateway failure affecting multiple users.
  - Initial Response SLA: **1 Hour**
  - Resolution Target: **4 Hours**
  - Mandatory Escalation: Tier-2 On-Call Engineering & Site Reliability Engineering (SRE).
- **P2 - Major Severity:** Significant core feature degradation (e.g. mobile checkout crashes, export reports failing), no direct workaround.
  - Initial Response SLA: **4 Hours**
  - Resolution Target: **1 business day**
  - Routing: Senior Technical Support Specialist.
- **P3 - Normal Severity:** Non-critical defects, isolated UI rendering issues, third-party integration warnings with functional workaround.
  - Initial Response SLA: **24 Hours**
  - Resolution Target: **3 business days**
  - Routing: Automated triage and tier-1 response.
- **P4 - Minor / Inquiry:** Feature enhancements, cosmetic bugs, documentation clarifications.
  - Initial Response SLA: **48 Hours**

## 2. Standard Troubleshooting Hierarchy
1. Clear local application cache and browser cookies.
2. Verify network connectivity and inspect WebSockets / CORS errors in developer console.
3. Test on updated supported browser (Chrome 120+, Safari 17+, Firefox 122+).
4. For mobile application crashes, capture device model, OS build number, and reproduction steps.

## 3. Autonomous Diagnostics vs Engineering Escalation
- Automated agents may provide verified knowledge-base troubleshooting steps, query system uptime status, and verify account feature flags autonomously.
- Automated creation of Jira / GitHub Engineering bugs for P1/P2 incidents requires Human Lead confirmation if external incident declaration or customer status page modification is involved.
