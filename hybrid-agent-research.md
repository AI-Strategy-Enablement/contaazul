# Hybrid AP/AR Automation Agent: Research Document

## 1. Executive Summary

Conta Azul's REST API covers **~85% of the Accounts Receivable (AR)** flow but only **~40% of Accounts Payable (AP)**. Four critical AP steps — purchase order creation, supplier invoice receipt, 3-way matching, and approval workflows — have **zero API coverage**. Bank reconciliation, shared by both flows, is read-only (no statement import, no write-back of reconciled status).

**The solution:** a hybrid automation agent that calls APIs wherever possible and falls back to browser automation for the gaps. The agent follows a strict **API-first, browser-fallback** principle — every step attempts API execution first and only invokes browser automation when no API path exists.

### Key Numbers

| Metric | Value |
|--------|-------|
| AP steps with full API | 3 / 10 (30%) |
| AP steps with partial API | 3 / 10 (30%) |
| AP steps with NO API | 4 / 10 (40%) |
| AR steps with full API | 7 / 10 (70%) |
| AR steps with partial API | 3 / 10 (30%) |
| AR steps with NO API | 0 / 10 (0%) |
| Steps requiring browser automation | 6 (4 AP gaps + 2 reconciliation operations) |
| Estimated cost per full AP flow (hybrid) | $0.80–2.50 |
| Estimated cost per full AR flow (API-only) | ~$0.00 (API calls only) |

---

## 2. Coverage Gap Analysis

### Accounts Payable (AP) — 10 Steps

| # | Step | Coverage | Approach | Key Endpoints / Notes |
|---|------|----------|----------|----------------------|
| 1 | Supplier Onboarding | **Full** | API | `POST /v1/pessoas` (perfil=Fornecedor), CNPJ/CPF, state/municipal registration |
| 2 | Purchase Order Creation | **None** | Browser | No PO API. ERP tracks COMPRA internally but exposes nothing. Must use UI. |
| 3 | Supplier Invoice Receipt | **None** | Browser | Invoice API is read-only (issued invoices only). IMPORTACAO_DOCUMENTO and NOTA_COMPRA visible as origins but no ingest endpoint. |
| 4 | 3-Way Matching (PO ↔ Invoice ↔ Receipt) | **None** | Browser + Logic | No matching API. Inventory API available for product reference only. Build matching logic externally, execute confirmation in UI. |
| 5 | AP Recording (Contas a Pagar) | **Full** | API | `POST /v1/financeiro/.../contas-a-pagar` (async, HTTP 202). Full installment CRUD. |
| 6 | Approval Workflow | **None** | Browser | No approval/authorization API. Internal workflow exists but isn't exposed. |
| 7 | Payment Scheduling | **Partial** | API + Browser | `PATCH .../parcelas/{id}` can set vencimento and pagamento_agendado flag. No scheduling management UI automation needed for complex scheduling. |
| 8 | Payment Execution | **Partial** | API + Browser | Record payments as "baixas" via PATCH parcelas. 22+ payment methods supported. No dedicated execution endpoint — may need browser for boleto generation. |
| 9 | Bank Reconciliation | **Partial** | API + Browser | Read-only: conciliado flag, id_reconciliacao, NSU (writable). No statement import, no reconcile-write endpoint. Browser needed for import + matching confirmation. |
| 10 | Financial Reporting | **Full** | API | 123 categories, cost centers, DRE mapping. Full query capabilities. |

### Accounts Receivable (AR) — 10 Steps

| # | Step | Coverage | Approach | Key Endpoints / Notes |
|---|------|----------|----------|----------------------|
| 1 | Customer Onboarding | **Full** | API | `POST /v1/pessoas` (perfil=Cliente). contato_cobranca_faturamento for billing contact. |
| 2 | Quote / Sales Order | **Full** | API | `POST /v1/venda`, full lifecycle (EM_ANDAMENTO → APROVADO → FATURADO), line items, installment schedules, PDF generation. |
| 3 | Invoice Issuance (NFe/NFS-e) | **Partial** | API (indirect) | Set sale to FATURADO triggers NFe/NFS-e. No direct invoice creation. 14 NFS-e statuses for polling. |
| 4 | Invoice Delivery (PDF/XML) | **Full** | API | `GET /v1/venda/{id}/imprimir` (PDF), `GET /v1/notas-fiscais/{chave}` (XML). |
| 5 | AR Recording (Contas a Receber) | **Full** | API | `POST .../contas-a-receber` (async, HTTP 202). Rich filtering: date, customer, status, amount range. |
| 6 | Billing & Collection | **Partial** | API + Browser | SolicitacaoCobranca schema is rich (boleto, PIX, payment links) but read-only — no creation endpoint. Browser needed to generate collection documents. |
| 7 | Cash Receipt | **Full** | API | Record baixas via `PATCH .../parcelas/{id}`. 22+ payment methods, partial payments supported. |
| 8 | Bank Reconciliation | **Partial** | API + Browser | Same as AP Step 9. NSU writable, conciliado read-only. |
| 9 | Recurring Billing | **Full** | API | `POST /v1/contratos` — MENSAL/ANUAL frequency, configurable due day, auto-generates sales. |
| 10 | Financial Reporting | **Full** | API | Same category/cost center/DRE infrastructure as AP. AR search supports aging reports. |

### Summary Heat Map

```
AP Flow:  [API][---][---][---][API][---][~~ ][~~ ][~~ ][API]
AR Flow:  [API][API][~~ ][API][API][~~ ][API][~~ ][API][API]

Legend: [API] = Full API  [~~ ] = Partial  [---] = No API (browser required)
```

---

## 3. Technology Options for Browser Automation

### Option A: Claude Computer Use (Cloud VM)

Claude's computer use capability runs in a cloud VM, takes screenshots, reasons about what it sees, and issues mouse/keyboard commands.

**How it works:**
1. Spin up a cloud VM (e.g., AWS EC2) with a browser
2. Authenticate to Conta Azul in the browser
3. Send screenshots to Claude API with tool_use for computer actions
4. Claude reasons about the UI and returns click/type/scroll commands
5. Execute commands, take new screenshot, repeat

**Strengths:**
- Handles arbitrary UI states, popups, errors, and layout changes
- No selector maintenance — purely visual
- Can reason about unexpected states ("this modal shouldn't be here")
- Works even if Conta Azul redesigns their UI (within reason)

**Weaknesses:**
- Latency: 2-5 seconds per action (screenshot + API call + response)
- Cost: ~$0.01-0.05 per action, $0.50-2.00 per complete flow
- Requires cloud VM infrastructure
- Screenshot-based — can misread small text or ambiguous elements
- Rate limited by Claude API throughput

**Best for:** Unpredictable UI states, error recovery, one-off admin tasks.

### Option B: Playwright Headless (Selector-Based)

Standard browser automation using CSS/XPath selectors to interact with DOM elements.

**How it works:**
1. Run Playwright in headless mode (no visible browser)
2. Navigate to Conta Azul pages
3. Use CSS selectors to find and interact with elements
4. Assert expected states, handle known modals/popups

**Strengths:**
- Fast: 50-200ms per action
- Free: no API costs
- Deterministic: same input → same output
- Easy to test and debug
- Can run multiple concurrent sessions

**Weaknesses:**
- Fragile: any UI change (class name, DOM structure) breaks selectors
- Requires maintenance when Conta Azul updates their frontend
- Cannot handle unknown states — fails on unexpected modals/layouts
- Must be explicitly programmed for every scenario

**Best for:** Stable, repetitive flows with predictable UI states.

### Option C: Hybrid (Recommended)

Playwright as the primary driver, Claude Computer Use as fallback for error recovery and unpredictable states.

**How it works:**
1. Playwright executes the happy path (fast, free, deterministic)
2. After each action, verify expected state via DOM assertions
3. If verification fails → capture screenshot → send to Claude Computer Use
4. Claude diagnoses the issue and provides recovery instructions
5. Resume Playwright execution or let Claude drive until stable state

**Strengths:**
- Fast for happy path (Playwright speed)
- Resilient to unexpected states (Claude reasoning)
- Cost-efficient: only pays for Claude on failures (~5-10% of actions)
- Self-documenting: screenshots captured on every anomaly

**Weaknesses:**
- More complex to implement
- Two systems to maintain
- Fallback path is slower

### Comparison Matrix

| Criterion | Claude Computer Use | Playwright | Hybrid |
|-----------|-------------------|------------|--------|
| Latency per action | 2-5s | 50-200ms | 50ms–5s |
| Cost per flow | $0.50-2.00 | $0.00 | $0.02-0.50 |
| Selector dependency | None | High | Medium |
| Handles unknown states | Excellent | Poor | Good |
| Concurrent sessions | Limited (API rate) | Unlimited | High |
| Maintenance burden | Low | High | Medium |
| Setup complexity | Medium | Low | High |
| Audit trail | Screenshots auto | Must add logging | Screenshots on anomaly |
| Best for | Complex/variable flows | Stable/repetitive flows | Production use |

---

## 4. Recommended Architecture

### 4.1 API-First, Browser-Fallback Principle

Every flow step follows this decision tree:

```
Step N requested
  ├─ Full API coverage? → Execute via API → Verify via API read-back → Done
  ├─ Partial API coverage? → Execute what API allows → Browser for remainder → Verify
  └─ No API coverage? → Execute via browser → Verify via screenshot + DOM check → Done
```

This minimizes browser automation usage (which is slower, costlier, and more fragile) while ensuring full coverage.

### 4.2 State Machine Orchestrator

Each AP/AR flow is modeled as a finite state machine. Each step is a state; transitions are API or browser commands.

```
┌──────────────┐    API     ┌──────────────┐   Browser   ┌──────────────┐
│  supplier_    │──────────→│  po_creation  │───────────→│  invoice_    │
│  onboarding   │           │  (browser)    │            │  receipt     │
│  (API)        │           │               │            │  (browser)   │
└──────────────┘            └──────────────┘            └──────────────┘
                                                              │
                                                         Browser + Logic
                                                              │
                                                              ▼
┌──────────────┐    API     ┌──────────────┐   Browser   ┌──────────────┐
│  payment_    │←──────────│  approval     │←───────────│  3way_match  │
│  scheduling   │           │  (browser)    │            │  (browser)   │
│  (API+browser)│           │               │            │              │
└──────────────┘            └──────────────┘            └──────────────┘
       │
       ▼
┌──────────────┐   API+Brw  ┌──────────────┐    API     ┌──────────────┐
│  payment_    │──────────→│  bank_recon   │───────────→│  reporting   │
│  execution    │           │  (API+browser) │            │  (API)       │
│  (API+browser)│           │               │            │              │
└──────────────┘            └──────────────┘            └──────────────┘
```

**State machine properties:**
- **Persistent state**: each flow instance writes its current state to a database (SQLite or Postgres)
- **Resumable**: if the agent crashes mid-flow, it reads last state and resumes
- **Idempotent transitions**: each transition can be safely retried (see Section 5)
- **Observable**: state transitions emit events for monitoring/alerting

### 4.3 Command Pattern for Actions

Each action (API call or browser interaction) is wrapped in a Command object:

```python
class Command(ABC):
    @abstractmethod
    def execute(self, context: FlowContext) -> CommandResult:
        """Perform the action."""

    @abstractmethod
    def verify(self, context: FlowContext) -> bool:
        """Confirm the action succeeded (API read-back or DOM check)."""

    @abstractmethod
    def compensate(self, context: FlowContext) -> None:
        """Undo the action if downstream steps fail (where possible)."""
```

**Examples:**

```python
class CreateSupplierCommand(Command):
    """API command — creates supplier via Person API."""

    def execute(self, context):
        response = context.api.post("/v1/pessoas", json={
            "nome": context.supplier_name,
            "documento": context.cnpj,
            "perfis": ["Fornecedor"],
        })
        context.supplier_id = response["id"]
        return CommandResult(success=True, data=response)

    def verify(self, context):
        supplier = context.api.get(f"/v1/pessoas/{context.supplier_id}")
        return supplier["nome"] == context.supplier_name

    def compensate(self, context):
        context.api.post("/v1/pessoas/ativar", json={
            "ids": [context.supplier_id],
            "ativo": False
        })


class CreatePurchaseOrderCommand(Command):
    """Browser command — creates PO via Conta Azul UI."""

    def execute(self, context):
        page = context.browser.page
        page.goto("https://app.contaazul.com/compras/novo")
        page.fill("#supplier-search", context.supplier_name)
        page.click(f"text={context.supplier_name}")
        # ... fill PO details
        page.click("button:has-text('Salvar')")

        # Verify save succeeded
        if not page.wait_for_selector(".success-toast", timeout=5000):
            return CommandResult(success=False, error="Save confirmation not shown")

        context.po_number = page.text_content(".po-number")
        return CommandResult(success=True)

    def verify(self, context):
        # Navigate to PO list and confirm it exists
        page = context.browser.page
        page.goto("https://app.contaazul.com/compras")
        return page.is_visible(f"text={context.po_number}")

    def compensate(self, context):
        # POs can be cancelled via UI
        pass
```

### 4.4 Page Object Model for Browser Automation

Encapsulate UI interaction details in Page Objects to isolate selector changes:

```python
class PurchaseOrderPage:
    URL = "https://app.contaazul.com/compras/novo"

    SELECTORS = {
        "supplier_search": "#supplier-search",
        "supplier_option": ".supplier-dropdown-item",
        "product_search": "#product-search",
        "quantity_input": "input[name='quantity']",
        "save_button": "button:has-text('Salvar')",
        "success_toast": ".toast-success, .notification-success",
        "po_number": ".purchase-order-number, .document-number",
    }

    def __init__(self, page: Page):
        self.page = page

    async def navigate(self):
        await self.page.goto(self.URL)
        await self.page.wait_for_load_state("networkidle")

    async def set_supplier(self, name: str):
        await self.page.fill(self.SELECTORS["supplier_search"], name)
        await self.page.click(f"{self.SELECTORS['supplier_option']}:has-text('{name}')")

    async def add_line_item(self, product: str, quantity: int, unit_price: float):
        await self.page.fill(self.SELECTORS["product_search"], product)
        # ... etc

    async def save(self) -> str:
        await self.page.click(self.SELECTORS["save_button"])
        await self.page.wait_for_selector(self.SELECTORS["success_toast"])
        return await self.page.text_content(self.SELECTORS["po_number"])
```

**Note:** Actual selectors must be discovered by inspecting Conta Azul's UI. The examples above are illustrative — a browser exploration session is needed to map real selectors (see Open Questions, Section 9).

### 4.5 Proposed Directory Structure

```
contaazul/
├── agent/
│   ├── __init__.py
│   ├── config.py                 # Environment, credentials, feature flags
│   ├── orchestrator.py           # State machine engine
│   ├── context.py                # FlowContext — shared state for a flow run
│   │
│   ├── api/
│   │   ├── client.py             # Extended ContaAzulClient (from contaazul_client.py)
│   │   ├── models.py             # Pydantic models for API request/response
│   │   └── retry.py              # API-specific retry logic
│   │
│   ├── browser/
│   │   ├── driver.py             # Playwright lifecycle management
│   │   ├── auth.py               # Login / session management
│   │   ├── fallback.py           # Claude Computer Use fallback handler
│   │   ├── screenshots.py        # Screenshot capture and storage
│   │   └── pages/                # Page Object Models
│   │       ├── purchase_order.py
│   │       ├── supplier_invoice.py
│   │       ├── approval.py
│   │       ├── reconciliation.py
│   │       └── collection.py
│   │
│   ├── flows/
│   │   ├── ap_flow.py            # AP state machine definition
│   │   ├── ar_flow.py            # AR state machine definition
│   │   └── reconciliation.py     # Shared reconciliation flow
│   │
│   ├── commands/
│   │   ├── base.py               # Command ABC
│   │   ├── ap/                   # AP step commands
│   │   │   ├── supplier_onboard.py
│   │   │   ├── purchase_order.py
│   │   │   ├── invoice_receipt.py
│   │   │   ├── three_way_match.py
│   │   │   ├── ap_recording.py
│   │   │   ├── approval.py
│   │   │   ├── payment_scheduling.py
│   │   │   └── payment_execution.py
│   │   └── ar/                   # AR step commands
│   │       ├── customer_onboard.py
│   │       ├── sales_order.py
│   │       ├── invoice_issuance.py
│   │       ├── invoice_delivery.py
│   │       ├── ar_recording.py
│   │       ├── billing_collection.py
│   │       ├── cash_receipt.py
│   │       └── recurring_billing.py
│   │
│   ├── matching/
│   │   ├── fuzzy_matcher.py      # LLM-powered transaction matching
│   │   ├── rules_engine.py       # Deterministic matching rules
│   │   └── ofx_parser.py         # OFX bank statement parser
│   │
│   ├── reliability/
│   │   ├── idempotency.py        # Dedup and idempotency keys
│   │   ├── verification.py       # Double-entry verification
│   │   ├── circuit_breaker.py    # Circuit breaker pattern
│   │   └── dead_letter.py        # Failed action queue
│   │
│   └── monitoring/
│       ├── events.py             # Event emission
│       ├── metrics.py            # Prometheus metrics
│       └── audit.py              # Screenshot audit trail
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
│
├── scripts/
│   ├── explore_ui.py             # Script to map Conta Azul UI selectors
│   └── run_flow.py               # CLI to execute a flow
│
└── data/
    ├── flows.db                  # SQLite state persistence
    └── screenshots/              # Audit trail screenshots
```

### 4.6 Why Custom Python Over LangChain / Temporal

**LangChain:** Designed for LLM-orchestrated chains where the LLM decides next steps. Our AP/AR flows are **deterministic** — the steps and their order are known in advance. LangChain adds overhead (token cost, latency, non-determinism) for zero benefit. The only place an LLM belongs is fuzzy matching (Section 7).

**Temporal:** Excellent for durable workflows, but adds significant infrastructure complexity (Temporal server, workers, SDK). Our flows are relatively short (10 steps, minutes not hours) and don't need multi-day sagas. A SQLite-backed state machine gives us resumability and idempotency without deploying a workflow engine.

**Our approach:** Plain Python + asyncio + Playwright + SQLite. The state machine is ~200 lines. Commands are simple classes. No framework lock-in. If flows grow more complex in the future, migrating to Temporal is straightforward because the Command pattern maps cleanly to Temporal activities.

---

## 5. Reliability Engineering

Financial automation demands higher reliability than typical web automation. A missed payment or duplicate invoice has real monetary consequences.

### 5.1 Idempotency

**Problem:** If the agent crashes after executing a payment but before recording success, restarting the flow could create a duplicate payment.

**Solution:** Idempotency keys and dedup checks before every financial write.

```python
class IdempotencyGuard:
    def __init__(self, db: Database):
        self.db = db

    def check_and_mark(self, flow_id: str, step: str, action_hash: str) -> bool:
        """Returns True if this action has already been executed."""
        existing = self.db.query(
            "SELECT result FROM idempotency_log WHERE flow_id=? AND step=? AND action_hash=?",
            (flow_id, step, action_hash)
        )
        if existing:
            return True  # Already executed — skip
        self.db.execute(
            "INSERT INTO idempotency_log (flow_id, step, action_hash, timestamp) VALUES (?, ?, ?, ?)",
            (flow_id, step, action_hash, datetime.utcnow())
        )
        return False  # First execution — proceed
```

**Action hash composition:** `SHA256(flow_id + step + supplier_id + amount + due_date)` — captures the business identity of the action.

### 5.2 Double-Entry Verification

**Principle:** After every write action, read it back via API and confirm the data matches.

```python
async def verified_create_payable(self, context):
    # Write
    response = await context.api.post("/v1/financeiro/.../contas-a-pagar", json=payload)
    event_id = response["id"]

    # Read back (with retry — async creation returns 202)
    for attempt in range(5):
        await asyncio.sleep(1 * (attempt + 1))  # Backoff: 1s, 2s, 3s, 4s, 5s
        payable = await context.api.get(f".../contas-a-pagar/{event_id}")
        if payable and payable["valor_total"] == payload["valor_total"]:
            return payable

    raise VerificationError(f"Payable {event_id} readback mismatch after 5 attempts")
```

**Critical for async endpoints:** Conta Azul's financial APIs return HTTP 202 (accepted, not created). The read-back retry is mandatory.

### 5.3 Screenshot Audit Trail

Every browser action captures a before/after screenshot pair:

```python
async def capture_action(self, page, action_name: str, action_fn):
    before = await page.screenshot(full_page=True)
    self.store_screenshot(f"{action_name}_before", before)

    result = await action_fn()

    after = await page.screenshot(full_page=True)
    self.store_screenshot(f"{action_name}_after", after)

    return result
```

**Storage:** Screenshots stored locally (data/screenshots/) with flow_id/step/timestamp naming. Retained for 90 days minimum (audit compliance).

### 5.4 Retry Strategies

API and browser actions require different retry approaches:

| Aspect | API Retry | Browser Retry |
|--------|-----------|---------------|
| Max retries | 3 | 2 |
| Backoff | Exponential (1s, 2s, 4s) | Fixed (2s) |
| Retryable errors | 429, 500, 502, 503, 504, timeout | Selector not found, navigation timeout |
| Non-retryable | 400, 401, 403, 404, 409 | Unexpected page state |
| On exhaust | Dead letter queue | Screenshot + Claude Computer Use fallback |

**Browser retry escalation:**
1. Retry with same Playwright selector
2. If fails → try alternative selectors from Page Object
3. If fails → capture screenshot → send to Claude Computer Use for diagnosis
4. If Claude Computer Use cannot resolve → dead letter queue + alert

### 5.5 Human-in-the-Loop Checkpoints

Some actions are too consequential for full automation. The agent pauses and requests human approval:

**Mandatory checkpoints:**
- Payment execution above a configurable threshold (e.g., R$ 10,000)
- First-time supplier payments (new vendor fraud risk)
- Reconciliation discrepancies above threshold
- Any compensating action (undo/cancel)

**Implementation:**
```python
class HumanCheckpoint:
    async def request_approval(self, flow_id: str, step: str, details: dict) -> bool:
        """Send approval request via configured channel (Slack, email, webhook)."""
        await self.notify(channel="slack", message={
            "flow_id": flow_id,
            "step": step,
            "action": details["description"],
            "amount": details.get("amount"),
            "supplier": details.get("supplier_name"),
        })
        # Wait for approval (with timeout)
        return await self.wait_for_response(flow_id, step, timeout_hours=24)
```

### 5.6 Circuit Breakers and Dead Letter Queues

**Circuit breaker:** If a specific step fails N times in a row (across different flow instances), the circuit opens and all flows skip that step, falling into a manual queue.

```
State: CLOSED (normal) → N failures → HALF_OPEN (test one) → success → CLOSED
                                     → failure  → OPEN (all requests fail-fast)
```

**Thresholds:**
- API endpoints: 5 consecutive failures → open circuit
- Browser steps: 3 consecutive failures → open circuit (UI may have changed)
- Half-open test: every 5 minutes

**Dead letter queue:** Failed actions that exhaust retries go to a dead letter table with full context (flow_id, step, payload, error, screenshots). A human reviews and either:
1. Retries after fixing the issue
2. Manually completes the step
3. Cancels the flow

---

## 6. Brazilian-Specific Challenges

### 6.1 NFe / NFS-e Legal Compliance

Brazilian electronic invoices are **legal fiscal documents** — they cannot be casually created, modified, or cancelled.

**NFe (Nota Fiscal Eletrônica) — Product Invoices:**
- Issued by setting a sale to FATURADO status in Conta Azul
- Once issued (status: EMITIDA), cannot be cancelled without filing a cancellation request with SEFAZ (state tax authority) within 24 hours
- After 24h, only a Carta de Correção (correction letter) is possible for minor fixes
- Access key (chave) is a 44-character unique identifier
- XML is the legally binding document, not the PDF (DANFE)

**NFS-e (Nota Fiscal de Serviço Eletrônica) — Service Invoices:**
- 14 lifecycle statuses in Conta Azul: PENDENTE → PRONTA_ENVIO → AGUARDANDO_RETORNO → EM_ESPERA → EMITINDO → EMITIDA
- Cancellation rules vary by municipality (each city has its own NFS-e system)
- RPS (Recibo Provisório de Serviço) serves as temporary receipt until NFS-e is confirmed

**Agent implications:**
- **Never cancel an invoice without explicit human approval** (mandatory checkpoint)
- Invoice issuance is a one-way door — verify all data BEFORE setting sale to FATURADO
- Poll NFS-e status after issuance (can take minutes for municipal systems to respond)
- Store XML copies locally as backup (legal retention: 5 years)

### 6.2 CPF/CNPJ Input Masks

Brazilian tax IDs have specific formatting that UI input fields enforce:

| Document | Format | Length | Validation |
|----------|--------|--------|------------|
| CPF (individual) | 000.000.000-00 | 11 digits | Modulo 11 check digits |
| CNPJ (company) | 00.000.000/0000-00 | 14 digits | Modulo 11 check digits |

**Browser automation concern:** Conta Azul's input fields likely have input masks that format as you type. Playwright must either:
- Type digits slowly so the mask can format them, or
- Use `page.fill()` which bypasses the mask (may cause validation errors), or
- Use `page.type()` with a delay between keystrokes

**Recommendation:** Use `page.type(selector, digits_only, delay=50)` to simulate human typing speed and let the mask format naturally.

### 6.3 BRL Currency Formatting

Brazilian Real (BRL) uses inverted separators compared to US:

| Format | US (USD) | Brazil (BRL) |
|--------|----------|--------------|
| Thousands | 1,000.00 | 1.000,00 |
| Decimal | . (period) | , (comma) |

**Agent implications:**
- API accepts numeric values (float/int) — no formatting issues
- Browser inputs may expect comma decimal separators: `page.type(selector, "1.500,00")`
- When reading values from the UI, parse BRL format: `"R$ 1.500,00"` → `1500.00`

### 6.4 Timezone: UTC-3 (Permanent)

Brazil abolished daylight saving time in 2019. São Paulo timezone (America/Sao_Paulo) is permanently UTC-3.

**Agent implications:**
- All date comparisons between API (which may return UTC) and browser (which shows BRT) must account for the -3h offset
- Due dates (vencimento) are date-only fields (no time component) — timezone doesn't affect them
- Transaction timestamps need conversion: `datetime.now(ZoneInfo("America/Sao_Paulo"))`

### 6.5 OFX File Format for Bank Statement Import

Conta Azul supports OFX (Open Financial Exchange) file import for bank statements, but only through the UI (no API endpoint).

**OFX structure relevant to reconciliation:**
```xml
<OFX>
  <BANKMSGSRSV1>
    <STMTTRNRS>
      <STMTRS>
        <BANKTRANLIST>
          <STMTTRN>
            <TRNTYPE>DEBIT</TRNTYPE>
            <DTPOSTED>20260312120000[-3:BRT]</DTPOSTED>
            <TRNAMT>-1500.00</TRNAMT>
            <FITID>2026031200001</FITID>
            <MEMO>PIX FULANO DE TAL</MEMO>
          </STMTTRN>
        </BANKTRANLIST>
      </STMTRS>
    </STMTTRNRS>
  </BANKMSGSRSV1>
</OFX>
```

**Browser automation for OFX import:**
1. Navigate to bank reconciliation page
2. Select the financial account
3. Upload OFX file via file input
4. Wait for parsing confirmation
5. Proceed to matching (see Section 7)

---

## 7. Key Insight: LLM for Fuzzy Matching

### The Problem

Bank statement descriptions are messy. They don't match the structured data in Conta Azul:

| Bank Statement (MEMO field) | Conta Azul Receivable |
|------------------------------|----------------------|
| `PIX FULANO DE TAL` | Fulano de Tal Comércio Ltda, R$ 1.500,00 |
| `TED 12345 MARIA S` | Maria Silva ME, R$ 3.200,00 |
| `PAG BOLETO 123456789` | Boleto #789 for Empresa ABC, R$ 5.000,00 |
| `DEB AUTO ENERGY CO` | Conta de Luz - CPFL Energia, R$ 450,00 |

Rules-based matching (exact amount + date window) catches ~60-70% of transactions. The remaining 30-40% require fuzzy name matching, partial amount matching (fees deducted), or context reasoning.

### The Solution: Claude API for Batch Matching

Use Claude's text API (NOT Computer Use) to match unresolved transactions:

```python
async def llm_match_transactions(
    unmatched_bank_txns: list[BankTransaction],
    open_receivables: list[Receivable],
    open_payables: list[Payable],
) -> list[MatchSuggestion]:

    prompt = f"""You are a Brazilian bank reconciliation assistant.

Match each bank transaction to the most likely open receivable or payable.
Consider: partial name matches, amount proximity (bank may deduct fees),
date proximity, and payment method clues in the memo.

Bank transactions (unmatched):
{format_transactions(unmatched_bank_txns)}

Open receivables:
{format_receivables(open_receivables)}

Open payables:
{format_payables(open_payables)}

For each bank transaction, return:
- matched_to: receivable/payable ID (or null if no match)
- confidence: high/medium/low
- reasoning: brief explanation

Return JSON array."""

    response = await claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    return parse_match_suggestions(response.content[0].text)
```

### Cost Analysis

| Metric | Value |
|--------|-------|
| Input tokens per batch (50 txns + 100 open items) | ~3,000 |
| Output tokens per batch | ~1,500 |
| Cost per batch (Claude Sonnet) | ~$0.02 |
| Latency | ~200-500ms |
| Accuracy vs rules-only | +25-35% match rate |

**This is the one place where an LLM genuinely outperforms deterministic code.** Bank memo parsing is inherently fuzzy — abbreviations, truncations, Portuguese variations, different bank formatting conventions.

### Matching Pipeline

```
Bank Transactions
       │
       ▼
┌─────────────────┐
│ Stage 1: Exact  │  Amount match + same date + exact name
│ Rules Engine    │  → ~40% matched
└────────┬────────┘
         │ unmatched
         ▼
┌─────────────────┐
│ Stage 2: Fuzzy  │  Amount within 2% + date within 3 days + similar name
│ Rules Engine    │  → ~25% more matched
└────────┬────────┘
         │ unmatched
         ▼
┌─────────────────┐
│ Stage 3: LLM    │  Claude API batch matching
│ Matching        │  → ~20% more matched
└────────┬────────┘
         │ unmatched (~15%)
         ▼
┌─────────────────┐
│ Stage 4: Human  │  Dashboard for manual review
│ Review Queue    │  → remaining matched by human
└─────────────────┘
```

---

## 8. Implementation Roadmap

### Phase 1: Foundation (Weeks 1-2)

**Goal:** API client, state machine, and basic AR flow working end-to-end.

| Task | Details |
|------|---------|
| Extend `contaazul_client.py` | Add all Person, Sales, Financial, Contracts API endpoints with Pydantic models |
| State machine engine | SQLite-backed, resumable, with event emission |
| Command base classes | API command + browser command + verification |
| AR flow (API-only steps) | Steps 1, 2, 4, 5, 7, 9, 10 — all have full API coverage |
| Integration tests | Against Conta Azul sandbox/test environment |

**Deliverable:** AR flow runs end-to-end for API-covered steps. State persists across restarts.

### Phase 2: Browser Automation Core (Weeks 3-5)

**Goal:** Playwright infrastructure, Page Objects, and first browser-automated steps.

| Task | Details |
|------|---------|
| Playwright setup | Headless Chrome, session management, screenshot capture |
| Login/auth flow | Handle Conta Azul login, session refresh, 2FA if applicable |
| UI selector mapping | Explore Conta Azul UI and document selectors for all browser-required pages |
| Page Object Models | PurchaseOrder, SupplierInvoice, Approval, Reconciliation, Collection pages |
| AP Steps 2, 3, 6 | Purchase order creation, invoice receipt, approval workflow via browser |
| AR Step 3, 6 | Invoice issuance (trigger FATURADO + verify), collection document generation |

**Deliverable:** All 20 AP+AR steps executable. Browser steps have Page Objects with real selectors.

### Phase 3: Reliability & Reconciliation (Weeks 6-8)

**Goal:** Production-grade reliability, bank reconciliation, and LLM matching.

| Task | Details |
|------|---------|
| Idempotency guard | Dedup keys for all financial writes |
| Double-entry verification | Read-back after every write (API and browser) |
| Retry + circuit breakers | Differentiated strategies for API vs browser |
| OFX parser | Parse bank statements locally |
| Reconciliation flow | Upload OFX via browser, match via rules + LLM, confirm via browser |
| LLM matching pipeline | 4-stage matching (exact → fuzzy → LLM → human queue) |
| Dead letter queue | Failed action storage and retry UI |

**Deliverable:** Reconciliation flow works. Financial writes are idempotent. Circuit breakers protect against cascading failures.

### Phase 4: Claude Computer Use Fallback (Weeks 9-10)

**Goal:** Resilient fallback for unexpected UI states.

| Task | Details |
|------|---------|
| Computer Use integration | Cloud VM setup, screenshot capture, Claude API integration |
| Fallback trigger logic | Detect Playwright failures → escalate to Computer Use |
| Error classification | Categorize UI errors (modal, layout change, auth expired, etc.) |
| Recovery strategies | Per-error-type recovery playbooks for Claude to follow |
| Human-in-the-loop | Approval checkpoints for high-value actions |

**Deliverable:** Agent self-recovers from unexpected UI states. Screenshots captured for all anomalies.

### Phase 5: Hardening & Monitoring (Weeks 11-12)

**Goal:** Production readiness.

| Task | Details |
|------|---------|
| Monitoring dashboard | Flow status, success rates, latency, cost tracking |
| Alerting | Slack/email alerts for failures, circuit breaker trips, human checkpoints |
| Audit trail | Searchable log of all actions with screenshots |
| Load testing | Concurrent flow execution, rate limit discovery |
| Documentation | Runbook, troubleshooting guide, selector update guide |
| Dry-run mode | Execute flow without writing — verify all reads succeed |

**Deliverable:** Production-ready agent with observability, alerting, and documentation.

---

## 9. Open Questions

### Must-answer before Phase 2

| # | Question | Impact | How to Answer |
|---|----------|--------|---------------|
| 1 | What frontend framework does Conta Azul use? (React? Angular? Vue?) | Determines selector strategy and stability expectations | Inspect app.contaazul.com with browser DevTools |
| 2 | Does Conta Azul use data-testid or similar stable attributes? | If yes, selectors are much more resilient to UI changes | Inspect DOM elements on key pages |
| 3 | Does Conta Azul have a staging/sandbox environment? | Needed for testing without affecting real data | Check account settings or contact support |
| 4 | What are the API rate limits? | Determines concurrency limits and retry backoff | Test empirically; check for 429 responses and X-RateLimit headers |
| 5 | Does Conta Azul enforce 2FA on login? | Affects browser automation auth flow | Check account security settings |
| 6 | Can multiple browser sessions run concurrently on one account? | Limits parallelism | Test with 2 sessions |

### Should-answer before Phase 3

| # | Question | Impact | How to Answer |
|---|----------|--------|---------------|
| 7 | What bank file formats does Conta Azul accept? (OFX only? CSV? MT940?) | Determines OFX parser scope | Check reconciliation import UI |
| 8 | Does Conta Azul expose webhooks for financial events? | Could replace polling for async operations | Check API docs / account settings |
| 9 | Is there a Conta Azul API roadmap? (Will PO API come?) | Might make some browser automation temporary | Contact Conta Azul partnership/developer team |
| 10 | What payment gateways are integrated? (Boleto registration, PIX QR) | Affects collection automation approach | Check account integrations page |

---

## 10. Risk Matrix

### Technical Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Conta Azul UI redesign breaks selectors | **High** (quarterly releases likely) | Medium | Page Object pattern isolates changes. Claude Computer Use fallback recovers gracefully. Maintain selector update runbook. |
| API rate limiting blocks automation | Medium | High | Respect rate limits, implement backoff, queue requests. Discover limits in Phase 1. |
| Async API (202) returns inconsistent data | Medium | Medium | Read-back verification with exponential backoff. Treat 202 as "pending" not "done". |
| Browser session expires mid-flow | **High** | Low | Session health check before each step. Re-authenticate automatically. State machine resumes from last step. |
| Claude Computer Use misreads UI element | Medium | Medium | Confidence threshold — if Claude isn't sure, screenshot goes to human queue instead of acting. |
| Concurrent sessions cause data conflicts | Low | **High** | Single-writer pattern per financial account. Flow-level locking. |

### Operational Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Credential management (OAuth tokens, browser cookies) | Medium | **High** | Use secret manager (AWS Secrets Manager / 1Password). Rotate tokens proactively. Never log tokens. |
| Agent creates duplicate payments | Low | **Critical** | Idempotency guard + double-entry verification + human checkpoint for high-value payments. |
| Agent runs in wrong timezone | Low | Medium | All dates in America/Sao_Paulo. Explicit timezone in every datetime operation. |
| Screenshot storage grows unbounded | Medium | Low | Retention policy (90 days), S3 lifecycle rules, periodic cleanup. |
| Conta Azul API deprecation | Low | High | Pin API version (v1). Monitor deprecation headers. Maintain API test suite. |

### Compliance Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Incorrect NFe/NFS-e issuance | Low | **Critical** | Pre-issuance verification checklist. Mandatory human approval for first-time customers. Never auto-cancel invoices. |
| Tax document retention failure | Low | **High** | Local XML backup for all invoices. 5-year retention minimum. Automated backup verification. |
| Unauthorized payment execution | Low | **Critical** | Human-in-the-loop for all payments above threshold. Approval audit log. Role-based access to agent controls. |
| Bank reconciliation mismatch goes unnoticed | Medium | High | Daily reconciliation report. Alert on unmatched transactions older than 3 business days. Monthly manual audit. |
| Personal data (CPF/CNPJ) exposed in logs | Medium | High | Mask PII in all logs. Screenshots stored encrypted. Access-controlled audit trail. |

---

## Appendix A: API Endpoint Reference

### Person API (Supplier/Customer Management)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/pessoas` | Create person (supplier or customer) |
| GET | `/v1/pessoas` | List persons with filters |
| PATCH | `/v1/pessoas/{id}` | Update person |
| POST | `/v1/pessoas/ativar` | Batch activate/deactivate |

### Sales API
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/venda` | Create sale |
| PUT | `/v1/venda/{id}` | Update sale (including status → FATURADO) |
| GET | `/v1/venda/busca` | Search sales |
| GET | `/v1/venda/{id}/itens` | Get line items |
| GET | `/v1/venda/{id}/imprimir` | Generate PDF |
| GET | `/v1/venda/proximo-numero` | Next sale number |

### Invoice API (Read-Only)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/v1/notas-fiscais` | Query NFe (product invoices) |
| GET | `/v1/notas-fiscais/{chave}` | Get NFe XML by access key |
| GET | `/v1/notas-fiscais-servico` | Query NFS-e (service invoices) |

### Financial API
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `.../contas-a-pagar` | Create payable event (async, 202) |
| GET | `.../contas-a-pagar/buscar` | Query payables |
| POST | `.../contas-a-receber` | Create receivable event (async, 202) |
| GET | `.../contas-a-receber/buscar` | Query receivables |
| GET | `.../parcelas/{id}` | Get installment details |
| PATCH | `.../parcelas/{id}` | Update installment (payment, dates, NSU) |
| GET | `/v1/conta-financeira` | List financial accounts |
| GET | `/v1/conta-financeira/{id}/saldo-atual` | Account balance |
| GET | `/v1/financeiro/transferencias` | Query transfers |
| GET | `/v1/categorias` | List 123 financial categories |
| GET | `/v1/centro-de-custo` | List cost centers |
| GET | `/v1/financeiro/categorias-dre` | DRE (P&L) mapping |

### Contracts API
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/v1/contratos` | Create recurring contract |
| GET | `/v1/contratos` | List contracts |
| GET | `/v1/contratos/proximo-numero` | Next contract number |

## Appendix B: Conta Azul Client Extension Plan

The existing `contaazul_client.py` implements 6 methods. The following methods need to be added:

| Priority | Method | Endpoint | Flow Step |
|----------|--------|----------|-----------|
| P0 | `create_person()` | POST /v1/pessoas | AP-1, AR-1 |
| P0 | `list_persons()` | GET /v1/pessoas | AP-1, AR-1 |
| P0 | `create_sale()` | POST /v1/venda | AR-2 |
| P0 | `update_sale()` | PUT /v1/venda/{id} | AR-2, AR-3 |
| P0 | `create_payable()` | POST .../contas-a-pagar | AP-5 |
| P0 | `create_receivable()` | POST .../contas-a-receber | AR-5 |
| P0 | `get_installment()` | GET .../parcelas/{id} | AP-5, AR-5 |
| P0 | `update_installment()` | PATCH .../parcelas/{id} | AP-7,8, AR-7 |
| P1 | `search_payables()` | GET .../contas-a-pagar/buscar | AP-9 |
| P1 | `search_receivables()` | GET .../contas-a-receber/buscar | AR-8 |
| P1 | `list_financial_accounts()` | GET /v1/conta-financeira | AP-9, AR-8 |
| P1 | `get_account_balance()` | GET .../saldo-atual | AP-7, AR-8 |
| P1 | `create_contract()` | POST /v1/contratos | AR-9 |
| P2 | `search_sales()` | GET /v1/venda/busca | AR-2 |
| P2 | `get_sale_items()` | GET /v1/venda/{id}/itens | AR-2 |
| P2 | `get_sale_pdf()` | GET /v1/venda/{id}/imprimir | AR-4 |
| P2 | `list_transfers()` | GET .../transferencias | AP-9, AR-8 |
| P2 | `update_person()` | PATCH /v1/pessoas/{id} | AP-1, AR-1 |
| P2 | `batch_activate_persons()` | POST /v1/pessoas/ativar | AP-1, AR-1 |
