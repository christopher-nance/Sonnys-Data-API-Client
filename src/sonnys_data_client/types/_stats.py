"""Stats result models for business analytics."""

from sonnys_data_client.types._base import SonnysModel


class SalesResult(SonnysModel):
    """Revenue breakdown returned by ``client.stats.total_sales()``.

    Categorizes total revenue into three buckets based on transaction
    flags: recurring plan sales, recurring redemptions, and retail.
    Each bucket includes both a revenue total and a transaction count.
    """

    total: float
    count: int
    recurring_plan_sales: float
    recurring_plan_sales_count: int
    recurring_redemptions: float
    recurring_redemptions_count: int
    retail: float
    retail_count: int


class WashResult(SonnysModel):
    """Wash volume breakdown returned by ``client.stats.total_washes()``.

    Categorizes wash transactions using v2 flags, v1 ``type=wash``,
    and v1 ``type=recurring``:

    - **member_wash_count**: Transactions where
      ``is_recurring_plan_redemption`` is ``True`` (membership washes).
    - **retail_wash_count**: Non-member car washes — ``type=wash``
      transactions (excluding plan sales and redemptions) plus
      unknown non-negative transaction types.
    - **free_wash_count**: Washes with ``total == 0``.
    - **eligible_wash_count**: Derived as
      ``total - member_wash_count - free_wash_count``.  Used as the
      denominator in conversion rate calculations.  Includes plan sale
      washes and positive-total unknown types.

    The ``total`` field is ``member + retail + plan_sale_washes``.
    Negative-total transactions (refunds) are excluded entirely.
    """

    total: int
    retail_wash_count: int
    member_wash_count: int
    eligible_wash_count: int
    free_wash_count: int


class ConversionResult(SonnysModel):
    """Membership conversion KPI returned by ``client.stats.conversion_rate()``.

    Measures how effectively a site converts eligible wash customers
    into membership sign-ups.  The ``rate`` is computed as
    ``new_memberships / eligible_washes``.

    A rate of ``0.15`` means 15 % of eligible washes resulted in a
    new membership sale.  When there are zero eligible washes the rate
    is ``0.0`` (division-by-zero safe).
    """

    rate: float
    new_memberships: int
    eligible_washes: int


class LaborCostResult(SonnysModel):
    """Labor cost breakdown returned by ``client.stats.total_labor_cost()``.

    Aggregates pay data from all clock entries in the requested period,
    splitting costs into regular and overtime buckets.  Each cost is
    computed as ``rate * hours`` for the corresponding pay type, then
    summed across all entries.

    Attributes:
        total_cost: Combined regular and overtime cost
            (``regular_cost + overtime_cost``).
        regular_cost: Sum of ``regular_rate * regular_hours`` across all
            clock entries.
        overtime_cost: Sum of ``overtime_rate * overtime_hours`` across
            all clock entries.
        regular_hours: Total regular hours worked across all entries.
        overtime_hours: Total overtime hours worked across all entries.
        total_hours: Combined hours (``regular_hours + overtime_hours``).
        entry_count: Number of clock entries aggregated.
    """

    total_cost: float
    regular_cost: float
    overtime_cost: float
    regular_hours: float
    overtime_hours: float
    total_hours: float
    entry_count: int


class CostPerCarResult(SonnysModel):
    """Cost-per-car KPI returned by ``client.stats.cost_per_car()``.

    Measures labor efficiency by dividing total labor cost by the
    number of washes in the period.  A value of ``4.25`` means the
    site spent $4.25 in labor for each car washed.

    When there are zero washes the ``cost_per_car`` is ``0.0``
    (division-by-zero safe).

    Attributes:
        cost_per_car: Total labor cost divided by total washes
            (``0.0`` when ``total_washes`` is zero).
        total_labor_cost: Aggregate labor cost from
            :class:`LaborCostResult`.
        total_washes: Wash count from :class:`WashResult`.
    """

    cost_per_car: float
    total_labor_cost: float
    total_washes: int


class StatsReport(SonnysModel):
    """Unified analytics report returned by ``client.stats.report()``.

    Bundles all KPIs into a single result object, computed from a
    single v2 transaction fetch for efficiency.

    Attributes:
        sales: Revenue breakdown (recurring plan sales, recurring
            redemptions, and retail) as a :class:`SalesResult`.
        washes: Wash volume breakdown (retail, member, and eligible
            washes) as a :class:`WashResult`.
        new_memberships: Count of recurring plan sales during the
            report period.
        conversion: Membership conversion rate KPI as a
            :class:`ConversionResult`.
        labor: Labor cost breakdown (regular/overtime costs and hours)
            as a :class:`LaborCostResult`.
        cost_per_car: Labor cost per car KPI as a
            :class:`CostPerCarResult`.
        period_start: ISO-8601 date string for the start of the report
            range (e.g. ``"2026-01-01"``).
        period_end: ISO-8601 date string for the end of the report
            range (e.g. ``"2026-01-31"``).
    """

    sales: SalesResult
    washes: WashResult
    new_memberships: int
    conversion: ConversionResult
    labor: LaborCostResult
    cost_per_car: CostPerCarResult
    period_start: str
    period_end: str
