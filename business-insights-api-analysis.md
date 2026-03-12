# Business Insights API Analysis: Conta Azul

What can we build purely from the API — and where do we hit walls?

---

## TL;DR Verdict

| Insight | API Support | Can Build? | Effort |
|---------|-------------|------------|--------|
| Cashflow Forecasting | **Strong** | Yes, fully via API | Medium |
| Outstanding Payments | **Strong** | Yes, fully via API | Low |
| Payment Reminders | **Read-only** | Detect who to remind (API), send reminder externally | Medium |
| Outlier Detection | **Strong** | Yes, fully via API | Medium-High |

The API provides excellent **read** coverage for financial data — enough to build all four insights. The main limitation is **write-back**: you can detect who needs a reminder but can't trigger Conta Azul's built-in notification system via API.

---

## 1. Cashflow Forecasting

### What the API gives us

**Future inflows (money coming in):**

| Data Source | Endpoint | Key Fields |
|-------------|----------|------------|
| Open receivables | `GET .../contas-a-receber/buscar` | `data_vencimento`, `nao_pago`, `status` (EM_ABERTO, RECEBIDO_PARCIAL) |
| Overdue receivables | Same, filter `status=ATRASADO` | `data_vencimento`, `nao_pago`, `cliente.nome` |
| Recurring contracts | `GET /v1/contratos` | `proximo_vencimento`, contract value, `tipo_frequencia` (MENSAL/ANUAL) |
| Pending sales | `GET /v1/venda/busca` | `totais.aprovado`, `totais.esperando_aprovacao` |

**Future outflows (money going out):**

| Data Source | Endpoint | Key Fields |
|-------------|----------|------------|
| Open payables | `GET .../contas-a-pagar/buscar` | `data_vencimento`, `nao_pago`, `status` (EM_ABERTO, RECEBIDO_PARCIAL) |
| Overdue payables | Same, filter `status=ATRASADO` | `data_vencimento`, `nao_pago`, `fornecedor.nome` |
| Scheduled payments | `GET .../parcelas/{id}` | `pagamento_agendado`, `data_pagamento_previsto` |

**Current position:**

| Data Source | Endpoint | Key Fields |
|-------------|----------|------------|
| Account balances | `GET /v1/conta-financeira/{id}/saldo-atual` | `saldo_atual` (real-time) |
| All financial accounts | `GET /v1/conta-financeira` | Account list with bank, type, active status |
| Inter-account transfers | `GET /v1/financeiro/transferencias` | Transfer amounts, dates, origin/destination |

### How to build it

```
Today's Cash Position
  = Σ saldo_atual across all active financial accounts

Week N Forecast
  = Current Position
  + Σ receivables due in week N (nao_pago where status ∈ [EM_ABERTO, RECEBIDO_PARCIAL])
  - Σ payables due in week N (nao_pago where status ∈ [EM_ABERTO, RECEBIDO_PARCIAL])
  + Σ recurring contract amounts due in week N
  - Historical adjustment for late payments (see below)
```

**Historical payment behavior (for accuracy adjustment):**
- Query past receivables with `data_pagamento_de/ate` filters and compare actual payment date vs `data_vencimento`
- Calculate average days-late per customer using `ids_clientes` filter
- Apply customer-specific delay factors to future forecasts

**Categorized forecasting (for departmental views):**
- Both search endpoints support `ids_categorias` and `ids_centros_de_custo` filters
- 123 financial categories available via `GET /v1/categorias`
- DRE (P&L) structure via `GET /v1/financeiro/categorias-dre` maps categories to P&L line items
- Build per-category or per-cost-center cashflow projections

### Query pattern

```python
# 12-week rolling cashflow forecast
for week in range(12):
    week_start = today + timedelta(weeks=week)
    week_end = week_start + timedelta(days=6)

    # Inflows: open receivables due this week
    receivables = api.get("/v1/financeiro/.../contas-a-receber/buscar", params={
        "data_vencimento_de": week_start.isoformat(),
        "data_vencimento_ate": week_end.isoformat(),
        "status": ["EM_ABERTO", "RECEBIDO_PARCIAL"],
        "tamanho_pagina": 1000,
    })
    inflow = sum(r["nao_pago"] for r in receivables["itens"])

    # Outflows: open payables due this week
    payables = api.get("/v1/financeiro/.../contas-a-pagar/buscar", params={
        "data_vencimento_de": week_start.isoformat(),
        "data_vencimento_ate": week_end.isoformat(),
        "status": ["EM_ABERTO", "RECEBIDO_PARCIAL"],
        "tamanho_pagina": 1000,
    })
    outflow = sum(p["nao_pago"] for p in payables["itens"])

    forecast[week] = {"inflow": inflow, "outflow": outflow, "net": inflow - outflow}
```

### What's missing

- **No cashflow report endpoint** — must be computed client-side from raw data
- **No "expected payment date" on receivables search** — only `data_pagamento_previsto` on individual parcelas, not in the search response schema
- **Recurring contracts** don't expose future installment amounts directly — must infer from contract terms + line item values
- **Tax obligations** (DAS, payroll) appear as payment origins but aren't queryable as future obligations

### Verdict: **Strong support.** All raw data for a 12-week rolling forecast is available. The API's rich filtering (date ranges, status, categories, cost centers) makes this very buildable. Missing a dedicated forecast endpoint, but the building blocks are solid.

---

## 2. Outstanding Payments

### What the API gives us

This is the strongest use case — the API was essentially designed for this.

**Receivables (money owed to you):**

```
GET /v1/financeiro/eventos-financeiros/contas-a-receber/buscar
```

Filters available:
- `status`: `EM_ABERTO`, `ATRASADO`, `RECEBIDO_PARCIAL`, `PERDIDO`, `RENEGOCIADO`, `RECEBIDO`
- `data_vencimento_de/ate`: Due date range (required)
- `data_competencia_de/ate`: Accrual date range
- `data_pagamento_de/ate`: Payment date range
- `data_alteracao_de/ate`: Last modification timestamp
- `valor_de/ate`: Amount range filter
- `ids_clientes`: Filter by specific customers
- `ids_categorias`: Filter by financial categories
- `ids_centros_de_custo`: Filter by cost centers
- `ids_contas_financeiras`: Filter by financial accounts
- `descricao`: Text search on description

**Response fields per receivable:**
- `id`, `descricao` — identifier and description
- `data_vencimento` — when it's due
- `status_traduzido` — EM_ABERTO, ATRASADO, RECEBIDO_PARCIAL, etc.
- `total` — original amount (e.g., R$ 781,201.79)
- `pago` — amount already paid
- `nao_pago` — remaining balance (e.g., R$ 213,023.79)
- `data_criacao`, `data_alteracao` — timestamps
- `data_competencia` — accrual date
- `cliente.id`, `cliente.nome` — who owes you
- `categorias[]` — financial categories
- `centros_custo[]` — cost centers
- `renegociacao` — renegotiation details if applicable

**Payables (money you owe):**

Same structure via `GET .../contas-a-pagar/buscar` with `fornecedor` (supplier) instead of `cliente`.

### Ready-made insight queries

**Aging report (how old are overdue receivables):**
```python
# Overdue 1-30 days
bucket_1 = query_receivables(
    data_vencimento_de=(today - timedelta(days=30)).isoformat(),
    data_vencimento_ate=(today - timedelta(days=1)).isoformat(),
    status=["ATRASADO"]
)
# Overdue 31-60 days
bucket_2 = query_receivables(
    data_vencimento_de=(today - timedelta(days=60)).isoformat(),
    data_vencimento_ate=(today - timedelta(days=31)).isoformat(),
    status=["ATRASADO"]
)
# Overdue 60+ days
bucket_3 = query_receivables(
    data_vencimento_de="2020-01-01",
    data_vencimento_ate=(today - timedelta(days=61)).isoformat(),
    status=["ATRASADO"]
)
```

**Top debtors:**
```python
all_overdue = query_receivables(status=["ATRASADO", "RECEBIDO_PARCIAL"])
by_customer = defaultdict(float)
for r in all_overdue:
    by_customer[r["cliente"]["nome"]] += r["nao_pago"]
top_debtors = sorted(by_customer.items(), key=lambda x: -x[1])[:10]
```

**Upcoming payment obligations (next 7 days):**
```python
upcoming = query_payables(
    data_vencimento_de=today.isoformat(),
    data_vencimento_ate=(today + timedelta(days=7)).isoformat(),
    status=["EM_ABERTO"]
)
```

### Individual installment deep dive

For any specific installment, `GET .../parcelas/{id}` returns the full detail:
- `valor_composicao`: breakdown of bruto, liquido, multa (fine), juros (interest), desconto, taxa
- `baixas[]`: payment records with dates, amounts, payment methods, reconciliation IDs
- `solicitacoes_cobrancas[]`: collection request history (boleto, PIX, payment links)
- `fatura`: linked invoice (NFe/NFS-e number)
- `renegociacao`: if the installment was renegotiated

### What's missing

- **No server-side aggregation** — the API returns raw records, not sums. You must paginate through all results and aggregate client-side.
- **Max page size is 1000** — for companies with many installments, you'll need to paginate.
- **No "days overdue" field** — must calculate from `data_vencimento` vs today.
- **No customer-level summary** — must aggregate manually per `cliente.id`.

### Verdict: **Excellent support.** This is the API's sweet spot. Status filtering, date ranges, amount ranges, customer/category/cost-center filters — everything needed for a comprehensive outstanding payments dashboard.

---

## 3. Payment Reminders

### What the API gives us

**Detection (who needs a reminder):** Fully supported — use the outstanding payments queries above to identify overdue or soon-due receivables.

**Existing reminder infrastructure (read-only):**

The `Parcela` schema includes `solicitacoes_cobrancas[]` — an array of `SolicitacaoCobranca` objects representing collection requests that Conta Azul has sent or is processing:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Collection request ID |
| `status_solicitacao_cobranca` | enum | AGUARDANDO_CONFIRMACAO, EM_CANCELAMENTO, CANCELADO, CONFIRMADO_BANCO, REJEITADO, EMITIDO, PAGO_PARCIALMENTE, FALHA_EMISSAO, FALHA_CANCELAR, REMESSA_GERADO, REMESSA_PENDENTE, PAGO, EXTORNADO |
| `tipo_solicitacao_cobranca` | enum | BOLETO, LINK_PAGAMENTO, BOLETO_REGISTRADO, PIX_COBRANCA |
| `data_vencimento` | date | Due date on the collection document |
| `data_quitacao` | date | Settlement date (if paid) |
| `id_cliente` | UUID | Customer |
| `erro` | string | Error message if failed |
| `conta_financeira` | object | Linked financial account |
| `notificacao_cobranca` | object | Notification details (see below) |
| `confirmado_em` | date | Bank confirmation date |
| `url` | string | Payment URL (for links/PIX) |
| `linha_digitavel` | string | Boleto barcode line |

**Notification details (read-only):**

Each collection request has a `NotificacaoCobranca` object:

| Field | Type | Description |
|-------|------|-------------|
| `id` | UUID | Notification ID |
| `enviado_em` | date | When the notification was sent |
| `aberto_em` | date | When the customer opened it |
| `assunto` | string | Email subject (e.g., "Fatura Vencida") |
| `corpo` | string | Email body (e.g., "Verificamos que o prazo de vencimento era [X] dias atrás...") |
| `respondido_para` | email | Reply-to address |
| `agendado` | boolean | Whether it was scheduled |
| `auto_notificacao` | boolean | Whether it was auto-sent |
| `envio_instantaneo` | boolean | Whether it was sent instantly |
| `itens_notificacao_cobranca[]` | array | Delivery items (email, SMS, WhatsApp with delivery status) |

**Delivery channels per notification:**

| Field | Description |
|-------|-------------|
| `email` | Email address |
| `sms` | Phone number for SMS |
| `whatsapp` | WhatsApp number |
| `status_entrega` | ENVIADO or INVALIDO |

### What we CAN'T do via API

- **Cannot create collection requests** (boleto, PIX, payment links) — `SolicitacaoCobranca` is read-only
- **Cannot send notifications** — `NotificacaoCobranca` is read-only
- **Cannot trigger Conta Azul's built-in reminder system** — no write endpoint

### What we CAN build

A **hybrid reminder system**:

1. **Detect** who needs a reminder (API — query overdue receivables)
2. **Check** if Conta Azul already sent a reminder (API — read `notificacao_cobranca`)
3. **Avoid duplicates** by checking `enviado_em` and `auto_notificacao`
4. **Send** the reminder externally (email via SES/SendGrid, WhatsApp via Twilio, etc.)
5. **Or** trigger Conta Azul's built-in reminder via browser automation (UI click)

```python
# Find receivables overdue >3 days with no recent notification
overdue = query_receivables(
    data_vencimento_de="2020-01-01",
    data_vencimento_ate=(today - timedelta(days=3)).isoformat(),
    status=["ATRASADO"]
)

for receivable in overdue:
    parcela = api.get(f".../parcelas/{receivable['id']}")

    # Check if Conta Azul already sent a notification
    last_notification = None
    for sc in parcela.get("solicitacoes_cobrancas", []):
        notif = sc.get("notificacao_cobranca")
        if notif and notif.get("enviado_em"):
            sent_date = parse_date(notif["enviado_em"])
            if not last_notification or sent_date > last_notification:
                last_notification = sent_date

    days_since_last = (today - last_notification).days if last_notification else 999

    if days_since_last > 7:  # No notification in 7 days
        send_external_reminder(
            customer=receivable["cliente"],
            amount=receivable["nao_pago"],
            due_date=receivable["data_vencimento"],
            # Include payment URL from collection request if available
            payment_url=get_payment_url(parcela),
        )
```

### Customer contact information

Via the Person API (`GET /v1/pessoas`), customers have:
- `email` — primary email
- `contato_cobranca_faturamento` — dedicated billing contact (AR-specific field)
- `telefone` — phone number
- `celular` — mobile number

### Verdict: **Read-only but useful.** The API gives you everything to detect who needs reminding and whether Conta Azul already reminded them. You just can't trigger reminders *through* Conta Azul's system — send them externally or use browser automation.

---

## 4. Outlier Detection

### What the API gives us

Outlier detection requires historical data to establish baselines and then flag anomalies. Here's what's available:

**Transaction-level data:**

| Data Point | Source | Fields |
|------------|--------|--------|
| All receivables in a period | `.../contas-a-receber/buscar` | amount, category, customer, dates |
| All payables in a period | `.../contas-a-pagar/buscar` | amount, category, supplier, dates |
| Individual payment details | `.../parcelas/{id}` | baixas with amounts, methods, fees, interest |
| Transfers between accounts | `/v1/financeiro/transferencias` | amount, date, source/destination accounts |
| Sales data | `/v1/venda/busca` | amount, date, customer, items, status |
| Invoice data | `/v1/notas-fiscais`, `/v1/notas-fiscais-servico` | amounts, dates, customers |

**Classification data:**

| Data Point | Source | Fields |
|------------|--------|--------|
| 123 financial categories | `/v1/categorias` | name, type (RECEITA/DESPESA), DRE mapping |
| DRE structure | `/v1/financeiro/categorias-dre` | P&L hierarchy with subcategories |
| Cost centers | `/v1/centro-de-custo` | organizational breakdown |
| Payment origins | `Referencia.origem` on parcelas | 16 origin types (sale, purchase, transfer, tax, etc.) |

### Detectable anomalies

**Amount outliers:**
- Payable significantly larger than historical average for that category/supplier
- Receivable with unusually high fees/interest (`valor_composicao.multa`, `.juros`, `.taxa`)
- Payment with suspicious discount (`valor_composicao.desconto` >> typical)

```python
# Query all payables in a category over 6 months
payables = []
for month in range(6):
    month_start = today - timedelta(days=30 * (month + 1))
    month_end = today - timedelta(days=30 * month)
    batch = query_payables(
        data_vencimento_de=month_start.isoformat(),
        data_vencimento_ate=month_end.isoformat(),
        ids_categorias=[category_id],
    )
    payables.extend(batch["itens"])

amounts = [p["total"] for p in payables]
mean, std = statistics.mean(amounts), statistics.stdev(amounts)
outliers = [p for p in payables if abs(p["total"] - mean) > 3 * std]
```

**Timing outliers:**
- Payment much earlier or later than typical for that supplier/customer
- Cluster of payables created on unusual dates (weekends, holidays)
- Receivable overdue far longer than typical for that customer segment

**Behavioral outliers:**
- New supplier with first payment much larger than typical first payments
- Customer payment method suddenly changed (was BOLETO, now PIX — not necessarily suspicious, but notable)
- Multiple partial payments on a single installment (`RECEBIDO_PARCIAL` with many `baixas[]`)
- Renegotiated installments (`status=RENEGOCIADO`) with significant value changes

**Category/cost center outliers:**
- Spending in a category suddenly spikes vs previous months
- New category appearing that wasn't used before
- Cost center allocation patterns changing

**Reconciliation outliers:**
- Installments marked `conciliado=false` for extended periods
- High count of `quantidade_nao_conciliados` in sales

### Data volume considerations

| Query | Max Page Size | Typical Volume |
|-------|---------------|----------------|
| Receivables search | 1000 | Depends on business — could be 100s to 10,000s/month |
| Payables search | 1000 | Typically fewer than receivables |
| Individual parcela | 1 | Rich detail per installment |
| Sales search | 50 | Sales are coarser-grained than installments |

For outlier detection, you'll need to pull 3-12 months of historical data. With 1000/page limits, plan for pagination. Use `data_alteracao_de/ate` for incremental sync after initial load.

### What's missing

- **No analytics/aggregation endpoint** — must pull raw data and compute statistics client-side
- **No webhook for real-time alerts** — must poll for changes using `data_alteracao_de/ate`
- **No audit log** — can't see who made changes (only that changes were made)
- **No budget/target data** — can't compare actuals against budgets via API

### Verdict: **Strong data foundation.** The filtering capabilities (by category, cost center, customer, supplier, amount range, date range) give you everything needed to build statistical anomaly detection. The main cost is pagination through historical data for the initial baseline. Incremental sync via `data_alteracao` timestamps keeps ongoing polling efficient.

---

## 5. Cross-Cutting API Capabilities

### Pagination

All search endpoints support `pagina` and `tamanho_pagina` (max 1000 for financial, max 50 for sales/contracts). Responses include `itens_totais` for total count.

### Incremental sync

Both financial search endpoints support `data_alteracao_de/ate` (ISO 8601, São Paulo/GMT-3 timezone). This enables efficient polling: "give me everything that changed since my last sync."

### Filtering power

| Filter | Receivables | Payables | Sales |
|--------|-------------|----------|-------|
| Due date range | Yes (required) | Yes (required) | N/A |
| Accrual date range | Yes | Yes | N/A |
| Payment date range | Yes | Yes | N/A |
| Last modified range | Yes | Yes | Yes |
| Amount range | Yes | Yes | N/A |
| Status | Yes (6 values) | Yes (6 values) | Yes (6 values) |
| Customer/Supplier IDs | Yes | Yes (supplier) | Yes (customer) |
| Category IDs | Yes | Yes | N/A |
| Cost center IDs | Yes | Yes | N/A |
| Financial account IDs | Yes | Yes | N/A |
| Text search | Yes (description) | Yes (description) | Yes (multiple fields) |

### Rate limits

API returns HTTP 429 (Too Many Requests) but doesn't document specific limits. Discover empirically and implement exponential backoff.

---

## 6. Recommended Implementation Priority

### Phase 1: Outstanding Payments Dashboard (1-2 weeks)
- Highest value, lowest effort
- Query receivables/payables with status filters
- Build aging buckets, top debtor/creditor lists
- Real-time balances across all accounts

### Phase 2: Cashflow Forecast (2-3 weeks)
- Extend Phase 1 with forward-looking date queries
- Add recurring contract projections
- Historical payment delay analysis for accuracy

### Phase 3: Payment Reminders (2-3 weeks)
- Layer on top of Phase 1 overdue detection
- Read existing Conta Azul notifications to avoid duplicates
- External notification sending (email/WhatsApp)
- Customer contact lookup via Person API

### Phase 4: Outlier Detection (3-4 weeks)
- Requires historical data ingestion (3-12 months baseline)
- Statistical analysis per category/supplier/customer
- Alerting system for flagged anomalies
- Incremental sync for ongoing monitoring

---

## Appendix: Key Endpoint Reference

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/v1/financeiro/.../contas-a-receber/buscar` | GET | Search receivables with rich filters |
| `/v1/financeiro/.../contas-a-pagar/buscar` | GET | Search payables with rich filters |
| `/v1/financeiro/.../parcelas/{id}` | GET | Deep detail on single installment |
| `/v1/conta-financeira` | GET | List all financial accounts |
| `/v1/conta-financeira/{id}/saldo-atual` | GET | Real-time account balance |
| `/v1/financeiro/transferencias` | GET | Inter-account transfers |
| `/v1/categorias` | GET | 123 financial categories |
| `/v1/financeiro/categorias-dre` | GET | P&L (DRE) structure |
| `/v1/centro-de-custo` | GET | Cost centers |
| `/v1/venda/busca` | GET | Search sales (totals, quantities) |
| `/v1/contratos` | GET | Recurring contracts |
| `/v1/pessoas` | GET | Customer/supplier contact info |
