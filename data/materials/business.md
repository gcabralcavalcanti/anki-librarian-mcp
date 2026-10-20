# Case notes: unit economics of a subscription box (fictitious company)

**The company.** Northwind Coffee Club sells a monthly coffee subscription at $30. Cost of goods and shipping per
box is $18, so the contribution margin is $12 per subscriber per month (40%). Customers are acquired mostly
through paid social ads.

**The numbers the team tracks.**
- Customer acquisition cost (CAC): marketing spend divided by new subscribers in the same period. Last quarter:
  $90,000 spent, 1,500 new subscribers → CAC of $60.
- Monthly churn: share of subscribers who cancel each month. Currently 8%.
- Expected lifetime in months ≈ 1 / churn → about 12.5 months at 8%.
- Lifetime value (LTV), on margin, not revenue: $12 × 12.5 ≈ $150.
- LTV / CAC ≈ 2.5. A common rule of thumb asks for at least 3 before scaling paid acquisition.
- CAC payback: months of margin needed to recover CAC = $60 / $12 = 5 months.

**The decision on the table.** Marketing wants to double ad spend. Two problems: (1) CAC usually rises as spend
grows, because the cheapest audiences are reached first; (2) at 8% churn, LTV/CAC is already below the target.

**Levers discussed.**
- Reduce churn: an annual plan paid upfront with a discount; a "skip a month" button instead of cancel. Cutting
  churn from 8% to 6% raises expected lifetime to about 16.7 months and LTV to about $200.
- Raise margin: a price increase to $33 for new subscribers, tested on a share of traffic first.
- Measure CAC by channel and cohort, not blended: a blended CAC hides an expensive channel behind a cheap one.

**Pitfalls the mentor pointed out.**
- LTV computed on revenue instead of margin overstates value by 2.5× here.
- Churn in the first month is usually much higher than later; one average churn rate hides it, so look at cohort
  retention curves.
- Payback matters for cash: a 5-month payback means each new subscriber is a cash outflow for 5 months, so fast
  growth burns cash even when LTV/CAC looks fine.

**Open question.** Is the annual plan's discount worth the lower margin, given that it also brings the cash
forward?
