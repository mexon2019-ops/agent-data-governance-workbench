# FineReport 11.0 inventory import contract

The workbench supports importing a read-only inventory export via API. This is an adapter
contract, not an assertion that a specific FineReport 11.0 endpoint is available in every edition.

## API
- `POST /api/v1/finereport/reports/import` (requires governance:write)
- `GET /api/v1/finereport/reports`

## Payload example
```json
{
  "reports": [
    {
      "report_id": "sales-summary",
      "name": "Sales Summary",
      "folder": "/Management/Sales",
      "owner": "Sales",
      "datasource": "erp",
      "datasets": [
        {"name": "sales_ds", "sql": "SELECT * FROM sales_order"}
      ]
    }
  ]
}
```

Import is upsert-by-report identifier. Inventory is stored as JSON in governance records;
no dataset SQL is executed. This endpoint is intended for sanitized inventory metadata.
Limit: 5000 report records per request. Only allowlisted keys are stored. Verify and use a
vendor-supported export/API to populate this contract for your deployment.
