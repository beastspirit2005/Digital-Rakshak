# Digital Rakshak — Security Audit & Hardening Report

**Audit Date:** October 29, 2026  
**Auditor:** Antigravity Application Security Engineering Team  
**Standard:** OWASP Top 10 API Security Risks (2023) / DPDP Act, 2023 / Bharatiya Sakshya Adhiniyam (BSA), 2023  
**Status:** In Progress — Remediation Batch 1

---

## 1. Application Security Role-Permission Matrix

The Digital Rakshak platform manages sensitive citizen FIRs, cybercrime evidence, and KYC identity documents across multiple institutional actors. The policy matrix enforced by the platform is defined below:

| Resource / Action | Citizen | Investigator (Police / Cyber Cell) | Bank Officer (`banker`, `bank_employee`) | Platform Admin |
| :--- | :--- | :--- | :--- | :--- |
| **Own Incident Report** | Full Read & Self-Update | Assignment & Jurisdiction only | View if financial scam only | Full Oversight |
| **Other Citizen's Incident** | **DENY (403)** | Assignment / Station Match only | **DENY** unless financial scam | Administrative Access |
| **Evidence Files (EVR)** | Own submitted files only | Authorized assigned case only | **Financial scam cases only** | Full Forensic Audit |
| **AI Investigation Co-Pilot** | **DENY (403)** | Authorized assigned cases only | **DENY (403)** | Full Administrative Oversight |
| **Citizen-Investigator Chat** | Assigned case participant only | Assigned investigator only | **DENY (403)** | Audited Safety Oversight |
| **KYC Identity Documents** | Own submission status | **DENY (403)** | **DENY (403)** | Authorized review workflow |
| **Audit Logs** | **DENY (403)** | Station/Jurisdiction scope only | Institutional audit only | Full Security Audit Trail |

---

## 2. Security Vulnerabilities & Findings

### Finding SEC-01: Broken Object Level Authorization (BOLA) in Evidence Vault Repository (EVR)
* **Severity**: **Critical (CVSS 8.8)**
* **Affected File**: [`backend/api/v1/evidence.py#L96-L112`](file:///c:/Users/Lenovo/Desktop/DigitalRakshak/backend/api/v1/evidence.py#L96-L112)
* **Vulnerability Description**:
  The function `_check_evidence_access` granted blanket access to evidence artifacts to any user having the role `banker` or `bank_employee`:
  ```python
  # Vulnerable Implementation:
  if user.role in ["admin", "police", "cyber_cell", "banker", "bank_employee"]:
      return
  ```
  This allowed a compromised or rogue banking partner account to retrieve sensitive evidence attachments (e.g. intimate video screenshots, identity IDs, suicide notes, non-banking police evidence) across all cases platform-wide.
* **Remediation**:
  Enforce case-level category checks. For users with role `banker` or `bank_employee`, verify that the associated case is categorized as a financial or banking scam (`BANKING_FRAUD`, `UPI_FRAUD`, `CREDIT_CARD_FRAUD`, `LOAN_APP_SCAM`, `INVESTMENT_SCAM`). For investigators, verify assignment or jurisdictional authority.
* **Verification**: Unit and API tests verifying that a `banker` user attempting to access evidence from a non-banking harassment or cyberbullying case receives `HTTP 403 Forbidden`.

---

### Finding SEC-02: Broken Function Level Authorization (BFLA) in AI Case Co-Pilot
* **Severity**: **High (CVSS 7.5)**
* **Affected File**: [`backend/api/v1/chat.py#L158-L185`](file:///c:/Users/Lenovo/Desktop/DigitalRakshak/backend/api/v1/chat.py#L158-L185)
* **Vulnerability Description**:
  The `case_copilot_chat` endpoint allowed any user with role `police` or `cyber_cell` to query the AI assistant about any arbitrary `case_id` by UUID. The endpoint leaked the case fact sheet, raw citizen narrative, and AI intelligence analysis without verifying whether the officer was assigned to the case or stationed at the relevant jurisdiction.
* **Remediation**:
  Enforce case ownership: verify `case.assigned_to == user.id` or `user.role == "admin"` before providing case context to the AI model.

---

### Finding SEC-03: Sensitive Test Artifacts & Session Tokens Tracked in Repository
* **Severity**: **High (CVSS 7.2)**
* **Affected Files**: `backend/admin_sessions.txt`, `backend/users.txt`, `backend/api_test.txt`, `temp_val.txt`.
* **Vulnerability Description**:
  Development and testing output files containing serialized user credentials, administrative session dumps, and API response logs were inadvertently committed to git tracking.
* **Remediation**:
  1. Untrack files immediately from git index using `git rm --cached`.
  2. Add patterns to `.gitignore`.
  3. Ensure zero secrets are present in tracked source code.

---

### Finding SEC-04: Chat Misconduct & Tamper-Preservation Audit
* **Status**: **Verified Compliant**
* **Evaluated File**: [`backend/api/v1/chat_safety.py`](file:///c:/Users/Lenovo/Desktop/DigitalRakshak/backend/api/v1/chat_safety.py)
* **Findings**:
  * Real-time regex and heuristic moderation effectively intercepts credentials, OTPs, UPI PINs, and extortion attempts.
  * Preserved evidence packages use SHA-256 digests complying with the Bharatiya Sakshya Adhiniyam (BSA), 2023.
  * Access to message threads is strictly limited to case participants (victim, assigned officer, administrator).

---

### Finding SEC-05: Zero-Trust KYC Onboarding & Document Streaming
* **Status**: **Verified Compliant**
* **Evaluated File**: [`backend/api/v1/users.py#L483-L580`](file:///c:/Users/Lenovo/Desktop/DigitalRakshak/backend/api/v1/users.py#L483-L580)
* **Findings**:
  * KYC documents are streamed only to authorized administrators (`get_current_admin`).
  * Immutable `AuditEvent` logs are recorded on every document view.
  * Rejection workflows securely delete KYC artifacts from cloud/local storage under the Digital Personal Data Protection (DPDP) Act, 2023.
