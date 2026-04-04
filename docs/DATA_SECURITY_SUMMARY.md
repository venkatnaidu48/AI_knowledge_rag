# Data Security & Access Control Summary

## Overview

The RAG system implements **multi-layer security** to protect documents from unauthorized access. Only authorized users with appropriate roles can see specific documents.

---

## CORE SECURITY ARCHITECTURE

### Layer 1: Document-Level Classification

**Every document has security metadata:**
```
Document:
├─ ID: doc-456
├─ Title: "Confidential Contract"
├─ Department: Legal
├─ Sensitivity Level:
│   ├─ PUBLIC (anyone can see)
│   ├─ INTERNAL (employees only)
│   ├─ CONFIDENTIAL (restricted roles)
│   └─ SECRET (CEO/Director only)
├─ Owner: john.smith@company.com
├─ Created: 2024-01-15
└─ Access Control List (ACL):
    ├─ Allowed users: [john, sarah, mike]
    ├─ Allowed roles: [Legal Team, Directors]
    └─ Allowed departments: [Legal, Compliance]
```

---

### Layer 2: Role-Based Access Control (RBAC)

**Employee roles determine what they see:**

**Role 1: Employee**
- Can access: PUBLIC documents only
- Cannot access: INTERNAL, CONFIDENTIAL, SECRET
- Examples: Company handbook, public announcements

**Role 2: Department Manager**
- Can access: PUBLIC + INTERNAL documents
- Cannot access: CONFIDENTIAL, SECRET
- Examples: Department strategies, internal communications

**Role 3: Director/Senior Leader**
- Can access: PUBLIC + INTERNAL + CONFIDENTIAL
- Cannot access: SECRET
- Examples: Strategic plans, employee reviews

**Role 4: CEO/Executive**
- Can access: ALL documents (PUBLIC + INTERNAL + CONFIDENTIAL + SECRET)
- Examples: Board minutes, financial records, M&A plans

**Example:**
```
User: John (Sales Employee)
Role: Employee
Access level: PUBLIC only

User queries: "What is strategic plan?"
System checks:
├─ Document sensitivity: CONFIDENTIAL
├─ User role: Employee
├─ Can access? NO
└─ Response: "Access Denied. Document is confidential."

---

User: Sarah (Sales Director)
Role: Director
Access level: PUBLIC + INTERNAL + CONFIDENTIAL

User queries: "What is strategic plan?"
System checks:
├─ Document sensitivity: CONFIDENTIAL
├─ User role: Director
├─ Can access? YES
└─ Response: [Shows document]
```

---

### Layer 3: Department-Level Filtering

**Users only see documents from their department (unless shared):**

```
Legal Department documents:
├─ Contracts (CONFIDENTIAL)
├─ Compliance reports (CONFIDENTIAL)
└─ Employee agreements (CONFIDENTIAL)

Finance Department documents:
├─ Budget plans (CONFIDENTIAL)
├─ Revenue reports (CONFIDENTIAL)
└─ Payroll data (SECRET)

User: John from Sales Department
Can see: 
├─ PUBLIC documents (all departments)
├─ INTERNAL documents (all departments)
└─ Cannot see: Legal/Finance confidential docs

Exception: If explicitly shared
If Sarah (Legal, Director) shares a contract with John:
├─ John's role: Employee
├─ BUT: Document explicitly shared
├─ Result: John CAN see this one contract
```

---

### Layer 4: User Authentication

**Before accessing system at all:**

```
Login flow:
┌─────────────────────────────┐
│ User enters: email + password│
└──────────┬──────────────────┘
           ↓
┌─────────────────────────────┐
│ System checks database       │
├─ Email exists?              │
├─ Password matches (hashed)?  │
└──────────┬──────────────────┘
           ↓
       YES? Continue
       NO? Access Denied
           ↓
┌─────────────────────────────┐
│ Generate JWT token (24 hrs)  │
│ Token contains:             │
├─ User ID                    │
├─ User role(s)               │
├─ Department                 │
└─ Expiration time            │
```

**Password security:**
```
Passwords stored as:
├─ NOT plain text (never!)
├─ Hashed: bcrypt (industry standard)
├─ Salted: Random salt per password
├─ Examples impossible to reverse
```

---

### Layer 5: Document Encryption

**Data at rest (stored in database):**
```
Sensitivity Level → Storage Method

PUBLIC:
├─ Stored: Plain text in database
├─ Encryption: None (public anyway)

INTERNAL:
├─ Stored: Encrypted with AES-256
├─ Encryption key: Rotated annually

CONFIDENTIAL:
├─ Stored: Encrypted with AES-256
├─ Encryption key: Rotated quarterly
├─ Additional: Field-level encryption for PII

SECRET:
├─ Stored: Double-encrypted (AES-256 + RSA)
├─ Key 1: AES-256 (multi-party control)
├─ Key 2: RSA (separate management)
├─ Access: Only on CEO approval
```

**Data in transit (over network):**
```
All connections: HTTPS/TLS 1.3
├─ Encryption: Military-grade (256-bit)
├─ Certificate: Signed by trusted CA
├─ Prevents: Interception, man-in-middle attacks
```

---

### Layer 6: Audit Logging

**Every document access is logged:**

```
Example audit log:
┌────────────────────────────────────────┐
│ Timestamp: 2024-03-15 14:32:15         │
│ User: john.smith (ID: emp-123)         │
│ Action: VIEW                           │
│ Document: "Q2 Financial Report"        │
│ Document ID: doc-456                   │
│ Sensitivity: CONFIDENTIAL              │
│ Result: SUCCESS (access granted)       │
│ IP Address: 192.168.1.100              │
│ Duration: 12 minutes                   │
└────────────────────────────────────────┘

Log entries MUST have:
├─ WHO accessed (user ID + name)
├─ WHEN accessed (timestamp)
├─ WHAT document (document ID + title)
├─ WHY/HOW accessed (download, view, search)
├─ WHETHER allowed (success/denied)
└─ FROM WHERE (IP address)
```

**Audit log uses:**
```
Security investigations:
├─ "Who downloaded contract XYZ?"
├─ "Did unauthorized user access?"
├─ "When did data breach occur?" (trace timeline)

Compliance:
├─ SOX compliance (financial)
├─ HIPAA (healthcare data)
├─ GDPR (personal data)

Example query:
"Show document access for confidential files in Feb"
→ Lists all access to SECRET/CONFIDENTIAL docs
→ Easy to spot suspicious activity
```

---

### Layer 7: Search Filtering

**Documents don't appear in search results if user can't access them:**

```
User: John (Sales Employee, PUBLIC access)

Searches for: "strategy"

Database has:
├─ "Marketing Strategy" (PUBLIC) ✓ Will appear
├─ "Financial Strategy" (CONFIDENTIAL) ✗ Will NOT appear
├─ "Sales Strategy" (INTERNAL) ✓ Will appear

Search results for John:
─────────────────────────
1. Marketing Strategy (PUBLIC)
2. Sales Strategy (INTERNAL)

Hidden from John:
─────────────────────────
- Financial Strategy (CONFIDENTIAL)
- Legal Strategy (CONFIDENTIAL)

Result: John has NO IDEA these documents exist
(can't find what you can't search for)
```

---

### Layer 8: Granular Permission Levels

**Beyond role, specific permissions can be granted:**

```
User: Mike (Employee in Finance)

Default access: INTERNAL documents in Finance dept only

But Sarah (CEO) grants Mike:
├─ View permission on: "Board Minutes" (SECRET)
├─ Edit permission on: "Budget Review" (CONFIDENTIAL)
├─ Download permission on: "Payroll Report" (CONFIDENTIAL)

Result:
├─ Mike can VIEW Board Minutes (but not edit/download)
├─ Mike can EDIT Budget Review (can modify + download)
├─ Mike can DOWNLOAD Payroll Report (but not edit it)
├─ Mike still can't see other SECRET documents

Formula: Base Access + Explicit Grants = Final Access
```

---

### Layer 9: Session Management

**Users automatically logged out after inactivity:**

```
Session timeout: 30 minutes of inactivity
(No keyboard/mouse activity)

User: John logs in
├─ Gets JWT token (24-hour expiration)
├─ Token valid for: Yes
└─ Can query: Yes

30 minutes pass (no activity)
├─ Inactivity timeout triggered
├─ Token invalidated
├─ JWT token: Deleted from browser
└─ Can query: NO (session expired)

Next action required:
├─ User tries to access: "View document"
└─ System says: "Session expired, please login again"

Security benefit:
├─ Left computer unattended? Can't harm you
├─ Shared computer? Next user can't access your account
```

---

## IMPLEMENTATION EXAMPLES

### How It Works in Practice

**Scenario 1: Employee browsing public documents**
```
Flow:
1. Sarah logs in with credentials
2. System validates (bcrypt password check)
3. Assigns JWT token: {user_id, role: "Employee", dept: "Sales"}
4. Sarah queries: "Show all documents"
5. System returns: Only PUBLIC documents
6. Sarah tries to access: "Confidential Contract" (CONFIDENTIAL)
7. System checks: Role "Employee" + Sensitivity "CONFIDENTIAL"
8. Result: DENIED ✗
9. Audit log: "2024-03-15 14:32:15 - Sarah attempt to view contract - DENIED"
10. User sees: "Access Denied. You don't have permission."
```

---

**Scenario 2: Manager accessing department documents**
```
Flow:
1. Mike logs in (Manager role)
2. System assigns: {user_id, role: "Manager", dept: "Legal"}
3. Mike searches: "contracts"
4. System returns:
   ├─ PUBLIC contracts (all) ✓
   ├─ INTERNAL contracts (all) ✓
   ├─ CONFIDENTIAL contracts (Legal dept only) ✓
   ├─ SECRET contracts ✗ (DENIED)
5. Mike views: "Client Contract A"
   ├─ Sensitivity: CONFIDENTIAL
   ├─ Department: Legal (Mike's dept)
   ├─ Access check: Manager role + Legal dept = YES
   ├─ Audit log: "Successful access - Legal Manager"
   └─ Document shown with full content
```

---

**Scenario 3: CEO accessing restricted document**
```
Flow:
1. CEO logs in
2. System assigns: {user_id, role: "CEO", dept: "Executive"}
3. CEO accesses: "Board Minutes" (SECRET)
4. Access check:
   ├─ Sensitivity: SECRET
   ├─ User role: CEO
   ├─ Can CEO access SECRET? YES
   ├─ Decrypt document (RSA key + AES-256)
5. Document displayed with maximum detail
6. Audit log: "CEO accessed Board Minutes - Approved"
```

---

## SUMMARY TABLE

| Layer | Mechanism | Protection | Example |
|-------|-----------|-----------|---------|
| 1 | Document classification | Metadata tags | Doc marked "CONFIDENTIAL" |
| 2 | Role-based access (RBAC) | User roles | Manager ≠ Employee access |
| 3 | Department filtering | Org hierarchy | Sales can't see Legal docs |
| 4 | Authentication | Username/password | Login required (bcrypt) |
| 5 | Encryption | Data protection | AES-256 at rest, TLS in transit |
| 6 | Audit logging | Activity tracking | Every access logged + timestamped |
| 7 | Search filtering | Result control | Hidden docs don't appear in search |
| 8 | Granular permissions | Exception handling | CEO can grant special access |
| 9 | Session management | Timeout protection | Auto-logout after 30 min |

---

## DATA PROTECTION CHECKLIST

**✅ Implemented in this system:**
- Document classification (PUBLIC, INTERNAL, CONFIDENTIAL, SECRET)
- Role-based access control (Employee, Manager, Director, CEO)
- Department-level filtering
- Password hashing (bcrypt)
- Encryption at rest (AES-256)
- Encryption in transit (HTTPS/TLS 1.3)
- Complete audit logging
- Search result filtering
- Granular permission system
- Session timeout (30 minutes)
- JWT token-based authentication

**Answer to your question:**

"How do you protect your documents?"

→ **Multi-layer approach**: 
1. Mark document sensitivity level (metadata)
2. Assign user roles (Employee/Manager/CEO)
3. Check: Does user's role have permission to view this sensitivity level?
4. If NO → Block access, log attempt
5. If YES → Decrypt document, show to user, log access
6. All access attempts visible in audit log for compliance

**Result:** Only authorized employees see authorized documents. Everything else is invisible and blocked.

---

