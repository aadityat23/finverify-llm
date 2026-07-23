# Security Policy

FinVerify's mission is to make financial AI output more trustworthy through deterministic verification and reproducible evaluation. That mission only holds up if the infrastructure around it — the API, the ingestion pipelines, the SDK, and the hosted demo — is itself trustworthy. We take the security of the FinVerify backend, frontend, and SDK seriously, and we appreciate the work of researchers and community members who help us find and fix issues before they affect users.

This applies across every surface in the repository: the FastAPI backend (`finverify-terminal/backend`), the Next.js frontend (`finverify-terminal/frontend`), the standalone `finverify` Python SDK (`finverify-terminal/sdk`), and the data-ingestion pipelines that pull from SEC EDGAR and other external sources.

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.** Public issues are indexed and visible immediately, which gives bad actors a head start before a fix is available.

Instead, report vulnerabilities privately by emailing:

**aaditya.thokal24@gmail.com**

Please use a clear subject line such as `[SECURITY] <short description>` so it can be triaged quickly. If you believe the issue is severe (for example, active exploitation, credential exposure, or data leakage on the hosted demo at finverify-llm.vercel.app or the HuggingFace Space API), please say so explicitly in your email so it can be prioritized accordingly.

## What to Include

To help us understand, reproduce, and fix the issue as quickly as possible, please include as much of the following as you can:

- **Description** — a clear explanation of the vulnerability and which component it affects (backend endpoint, frontend page, SDK function, ingestion pipeline, etc.).
- **Steps to reproduce** — the exact request, payload, or sequence of actions needed to trigger the issue. For API-level findings, include the endpoint, method, headers, and body used.
- **Potential impact** — what an attacker could actually achieve: for example, unauthorized data access, denial of service against ingestion or market-data endpoints, credential or secret exposure, or the ability to bypass verification and present unverified financial figures as trusted output.
- **Proof of concept** — a minimal script, `curl` command, or request/response trace demonstrating the issue, if you have one. This is optional but significantly speeds up triage.
- **Suggested mitigation** — if you have a recommendation (a config change, an input validation fix, a dependency update), we welcome it, though it's not required.

## Response Process

Once a report is received, you can expect the following process:

1. **Acknowledgement** — We will acknowledge receipt of your report as soon as possible after it is submitted, so you know it has reached a maintainer and hasn't been lost to a spam filter.
2. **Investigation** — We will investigate the report, confirm whether it reproduces, and assess its severity and affected components (backend API, frontend, SDK, or a specific ingestion source). We may follow up with clarifying questions during this stage.
3. **Fix** — Once confirmed, we will work on a fix. For issues affecting the hosted demo or API, we will prioritize deploying the fix to the live environment; for issues affecting the SDK, we will prioritize a patched release.
4. **Public disclosure** — After a fix is available and deployed (or released, for the SDK), we will publish details of the vulnerability, generally as a GitHub Security Advisory, and credit the reporter unless they prefer to remain anonymous.

We will keep you informed of progress throughout this process. Response and fix timelines depend on severity and complexity — a credential-exposure or authentication-bypass finding will be treated with more urgency than a lower-impact configuration issue.

## Supported Versions

FinVerify does not currently maintain multiple released version branches. Security updates are applied to the **`main` branch**, which reflects the current state of the backend, frontend, and SDK. If you are running a fork, an older clone, or a pinned version of the `finverify` SDK from PyPI, we recommend updating to the latest `main`/release before assuming a reported fix applies to your deployment.

## Responsible Disclosure

We ask that you give us a reasonable opportunity to investigate and address a reported vulnerability before publishing any details publicly (including on social media, blog posts, or public GitHub discussions) or disclosing it to third parties. We are committed to working with researchers in good faith, and we will coordinate on disclosure timing so that a fix is available before public details are shared.

We do not currently operate a paid bug bounty program, but we are glad to credit researchers publicly (with permission) in release notes and security advisories for responsibly disclosed findings.

Thank you for helping keep FinVerify — and the people who rely on it to sanity-check financial AI output — secure.
