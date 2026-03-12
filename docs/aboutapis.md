# Introduction to Conta Azul APIs

The **Conta Azul APIs** allow you to integrate external systems with the Conta Azul ERP in a secure, standardized, and scalable way.
They provide resources to automate **financial processes, sales, customer and supplier records, products, and invoices**, making data synchronization easier.

## What You Can Do with Our APIs

With the Conta Azul APIs, you can:

- Integrate partner systems (BI, CRM, e-commerce, etc.);
- Automate accounts payable and receivable entries;
- Query financial and accounting information in real time;
- Create and maintain up-to-date records of customers, products, and services;
- Query electronic invoices (products NFe only) - Services (NFS-e) coming soon


## General API Structure

The Conta Azul API documentation is organized by **functional areas**.
Below, you'll find an overview with the purpose of each area and direct links to the respective technical guides.

| Area | Description | Example Use Case | Link |
|  --- | --- | --- | --- |
| **Authentication** | APIs for OAuth2 authentication, credential generation, and metadata access. | Create an application and obtain API access tokens. | [View documentation](https://developers.contaazul.com/auth) |
| **Financial / Billing / Write-offs** | Full control of accounts payable and receivable, write-offs, reconciliations, billing, and expenses. | Automate invoice write-offs and payment reconciliation. | [View documentation](https://developers.contaazul.com/docs/financial-apis-openapi) |
| **Sales** | Creation, updating, and querying of sales. | Create a sale and automatically replicate it in Conta Azul. | [View documentation](https://developers.contaazul.com/docs/sales-apis-openapi) |
| **People / Suppliers** | Registration and querying of customers and suppliers. | Automatically sync customers between systems. | [View documentation](https://developers.contaazul.com/open-api-docs/open-api-person) |
| **Products and Services** | Management of products and services: creation, updating, inventory, and pricing. | Integrate the e-commerce product catalog with the ERP. | [View documentation](https://developers.contaazul.com/open-api-docs/open-api-inventory) |
| **Invoices** | Querying of product and service invoices. | Query issued NFe invoices | [View documentation](https://developers.contaazul.com/open-api-docs/open-api-invoice) |
| **Contracts** | Management of recurring contracts. | Manage monthly contracts and allocate expenses by cost center. | [View documentation](https://developers.contaazul.com/docs/contracts-apis-openapi) |
|  |  |  |  |


## Technical Standards

- **Style:** REST
- **Format:** JSON
- **Authentication:** OAuth 2.0
- **Return codes:** Standard HTTP (`200`, `400`, `401`, `404`, `429`, `500`)
- **Pagination:** `page` and `size` parameters
- **Date/time:** ISO 8601 format (`YYYY-MM-DDTHH:mm:ssZ`)


## API Future

At this time, some important features are not yet available. We are constantly working to improve and expand our capabilities, but it's important that you are aware of the following current characteristics:

* **Staging Environment (Sandbox):** we do not offer a dedicated sandbox environment. For testing, you will have access to a **30-day developer account**, which can be extended if needed. This account allows you to validate your integrations in a realistic environment
* **Webhooks:** currently, the API **does not support webhooks**, so your application will not receive automatic notifications about events or data changes. To keep your data up to date, you will need to implement a *polling* mechanism (periodic API queries)
* **Official SDKs:** we do not provide **official Software Development Kits (SDKs)** for programming languages. Your integration must be built directly with HTTP calls and JSON handling, without the aid of Conta Azul-specific pre-built libraries


### Contact Us

For any questions, the **documentation is your best resource**. We recommend reading the **"OAuth 2.0"**, **"Usage Guides"**, and **"Common Errors"** guides. If you encounter bugs or service outages, please contact support at api@contaazul.com.
Additionally, you can also access the Chat through the Developer Portal to ask questions and get guidance on using the APIs.
