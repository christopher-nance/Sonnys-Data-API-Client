# Models

All response models are [Pydantic v2](https://docs.pydantic.dev/latest/) `BaseModel`
subclasses. The API returns **camelCase** field names; each model uses
`alias_generator = to_camel` so you can access fields with Pythonic
**snake_case** attributes.

```python
customer = client.customers.get("12345")
print(customer.first_name)   # snake_case attribute
print(customer.model_dump(by_alias=True))  # camelCase dict
```

---

## Customers

::: sonnys_data_client.types.CustomerListItem
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.Customer
    options:
      show_source: false
      heading_level: 3

---

## Items

::: sonnys_data_client.types.Item
    options:
      show_source: false
      heading_level: 3

---

## Employees

::: sonnys_data_client.types.EmployeeListItem
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.Employee
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.ClockEntry
    options:
      show_source: false
      heading_level: 3

---

## Sites

::: sonnys_data_client.types.Site
    options:
      show_source: false
      heading_level: 3

---

## Giftcards

::: sonnys_data_client.types.GiftcardListItem
    options:
      show_source: false
      heading_level: 3

---

## Washbooks

::: sonnys_data_client.types.WashbookListItem
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.Washbook
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.WashbookTag
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.WashbookVehicle
    options:
      show_source: false
      heading_level: 3

---

## Recurring

::: sonnys_data_client.types.RecurringListItem
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.Recurring
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.RecurringStatusChange
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.RecurringModification
    options:
      show_source: false
      heading_level: 3

---

## Transactions

::: sonnys_data_client.types.TransactionListItem
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.TransactionV2ListItem
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.Transaction
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.TransactionJobItem
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.TransactionTender
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.TransactionItem
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.TransactionDiscount
    options:
      show_source: false
      heading_level: 3

---

## Stats

::: sonnys_data_client.types.SalesResult
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.WashResult
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.ConversionResult
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.LaborCostResult
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.CostPerCarResult
    options:
      show_source: false
      heading_level: 3

::: sonnys_data_client.types.StatsReport
    options:
      show_source: false
      heading_level: 3
