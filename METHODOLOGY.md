# Technical Methodology

[Olist Brazilian E-Commerce Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

# 1. Exploratory Pre-Analysis and Goal Setting

During the initial exploration, it became apparent that the Portuguese review text contained potentially valuable information that was not captured by the structured review score alone. A review of existing analyses of the dataset also showed relatively limited use of the textual review content, particularly through systematic classification of the messages. This gap motivated the decision to classify the reviews into meaningful categories, with the goal of exploring information that would otherwise remain largely unused.

To support this objective, the relevant data required for the analysis was identified. This included review messages and scores, the relationships necessary to associate reviews with individual customers through Reviews -> Order ID -> Customer ID -> Customer Unique ID. Order dates were also required to establish the chronological sequence of purchases and determine whether customers made subsequent purchases after a reviewed order.

---

# 2. Data Structure

The study was conducted using a copy of the *orders* table as the primary analytical dataset. The *order_reviews* and *customers* tables were joined to it using the relationships shown in the diagram. The *order_id* field in *order_reviews* had been deduplicated in a previous step to ensure that each order could be matched to a single review record.

![Data Structure](pictures/data_structure.webp)

# 3. Data Cleaning & Preparation

- Starting with approximately 100,000 reviews, around 800 had a NULL review score. These records were removed to avoid ambiguity in subsequent analysis, after verifying that their distribution across relevant categories was broadly consistent with the rest of the dataset.

- Some reviews contained duplicated *order_id* values, likely because customers could submit feedback more than once per order. When duplicates were found, entries containing a non-empty review message were prioritized, with the most recent qualifying entry retained. The associated orders were subsequently removed in a later step:

```sql
SELECT review_answer_timestamp, order_id, review_comment_message
FROM public.order_reviews
WHERE order_id IN (
    SELECT order_id
    FROM public.order_reviews
    GROUP BY order_id
    HAVING COUNT(*) > 1
)
ORDER BY order_id, review_answer_timestamp desc;
```
```sql
WITH ranked_reviews AS (
    SELECT
        ctid,
        ROW_NUMBER() OVER (
            PARTITION BY order_id
            ORDER BY
                CASE
                    WHEN review_comment_message IS NOT NULL
                         AND TRIM(review_comment_message) <> ''
                    THEN 0
                    ELSE 1
                END,
                review_answer_timestamp DESC
        ) AS rn
    FROM public.order_reviews)

DELETE FROM public.order_reviews r
USING ranked_reviews x
WHERE r.ctid = x.ctid
  AND x.rn > 1;
```

- A column containing review message titles was also available. The majority of entries consisted of variations of "Recomendo", "Ótimo", and "Não Recomendo", which primarily indicate general sentiment rather than specific issues. Since this information could be captured less ambiguously through the review score, the column was excluded from the analysis.

- Approximately 600 orders out of 100,000 occurred at the same timestamp for the same customer, indicating bundled transactions. These orders were treated as a single purchase event. The distribution of these bundled orders was compared with the rest of the dataset and found to be broadly consistent. Therefore, only one order in each bundle was retained for the purchase sequence, simplifying the construction of customer purchase histograms without materially altering the overall distribution. The last order by chronological delivery date was retained, since it's associated review should reflect customer sentiment more accurately:
```sql
WITH ranked_orders AS (
    SELECT
        order_id,
        ROW_NUMBER() OVER (
            PARTITION BY customer_unique_id, order_purchase_timestamp
            ORDER BY order_delivered_customer_date DESC NULLS LAST, order_id DESC
        ) AS bundle_rank
    FROM orders
)

DELETE FROM orders AS o
USING ranked_orders AS r
WHERE o.order_id = r.order_id
  AND r.bundle_rank > 1;
```

---

# 4. Repurchase Rate and Customer Purchase Histograms

An order was considered to have a subsequent repurchase when the same customer placed a chronologically later order. Subsequent orders were included regardless of their order status, including cancelled or still-in-progress orders, as the act of placing another order was considered an indication of continued purchasing intent.

Each order was then assigned a sequential number based on its chronological position within the same customer. This value was stored in a new *purchases_so_far* column.

```sql
ALTER TABLE public.orders
ADD COLUMN purchases_so_far INTEGER;

WITH numbered_orders AS (
    SELECT
        order_id,
        ROW_NUMBER() OVER (
            PARTITION BY customer_unique_id
            ORDER BY order_purchase_timestamp, order_id
        ) AS purchase_number
    FROM orders
)
UPDATE orders AS o
SET purchases_so_far = n.purchase_number
FROM numbered_orders AS n
WHERE o.order_id = n.order_id;
```

With orders ranked chronologically for each customer, the number of days until the customer's next order was calculated and stored in a new *days_to_next_order column*. The value was left as NULL when no subsequent order was observed.

```sql
ALTER TABLE public.orders
ADD COLUMN days_to_next_order INTEGER;

WITH next_orders AS (
    SELECT
        order_id,
        order_purchase_timestamp,
        LEAD(order_purchase_timestamp) OVER (
            PARTITION BY customer_unique_id
            ORDER BY purchases_so_far
        ) AS next_order_timestamp
    FROM orders )

UPDATE orders AS o
SET days_to_next_order =
    n.next_order_timestamp::DATE - n.order_purchase_timestamp::DATE
FROM next_orders AS n
WHERE o.order_id = n.order_id;
```

A boolean variable, *had_subsequent_order*, was added to simplify subsequent repurchase-rate calculations. It was derived from *days_to_next_order*, with a value of TRUE when a subsequent order was observed and FALSE when the value was null.

Additional checks were performed to better understand customer repurchase behavior, including the time elapsed between purchases. The median time to a subsequent purchase was found to be 66 days.
```sql
WITH ranked AS (
    SELECT
        days_to_next_order,
        NTILE(10) OVER (
            ORDER BY days_to_next_order
        ) AS decile
    FROM analysis.all
    WHERE days_to_next_order IS NOT NULL
)

SELECT
    decile,
    ROUND(AVG(days_to_next_order), 0) AS avg_days,
    ROUND(
        PERCENTILE_CONT(0.5)
        WITHIN GROUP (ORDER BY days_to_next_order)
    ) AS median_days,
    COUNT(*) AS customers
FROM ranked
GROUP BY decile
ORDER BY decile;
```

```sql
SELECT
    ROUND(
        PERCENTILE_CONT(0.5)
        WITHIN GROUP (ORDER BY days_to_next_order)
    ) AS median_days
FROM analysis.all
WHERE days_to_next_order IS NOT NULL;
```

At this stage, it was possible to assess customer repurchase rates and perform additional checks to validate the analysis. In particular, the relationship between review scores and average repurchase rates was examined:

| Review Score | Repurchase Rate % | Count |
|---:|---:|---:|
| 1 | 2.37 | 9650 |
| 2 | 2.46 | 2598 |
| 3 | 2.61 | 6749 |
| 4 | 2.63 | 15409 |
| 5 | 3.33 | 44675 |
```sql
SELECT
    review_score,
    ROUND(AVG(had_subsequent_order::INTEGER) * 100, 2) AS repurchase_rate,
    COUNT(*) AS orders
FROM analysis.all
GROUP BY review_score
ORDER BY review_score;
```

It was initially assumed that repurchase rates would decline gradually as review scores decreased. However, the analysis showed that a binary distinction between 5-star reviews and reviews below 4 stars provided a better representation of the observed customer behavior. Positive reviews were therefore defined as 5-star reviews, while negative reviews were defined as reviews below 4 stars. Throughout the analysis, repurchase rate is calculated at the order level rather than the customer level.

The observed overall repurchase rate of approximately 3% was also substantially lower than initially expected. This became the first major insight of the study and influenced several subsequent modeling decisions. Additional checks were performed to determine whether this result could instead be attributed to issues within the dataset, including verifying that customers with more than 365 days of purchasing activity were present.

The dataset showed an unusual decline in order frequency during approximately the final two months of the observation period, with a small but persistent tail of orders. This pattern suggested that the dataset may be subject to administrative censoring near its endpoint, meaning that the apparent decline may reflect incomplete observation rather than genuine changes in purchasing behavior.

Since the exact point at which the data became incomplete could not be reliably determined, a cutoff date was manually selected to approximate 66 days (median repurchase estimation) before the start of the censored period.

Orders after this cutoff were treated differently depending on whether a subsequent purchase had already been observed. Confirmed repurchases were retained, as they represent directly observed customer behavior and provide valuable observations for subsequent statistical analysis. Orders without a subsequent purchase were excluded, since they did not have sufficient observation time to reliably classify the customer as a non-repurchaser. this did not meaningfully inflate general repurchase rates or introduce biases, and helped reduce the potential biases caused by right-censoring:

```sql
DELETE FROM analysis.all
WHERE order_purchase_timestamp::DATE > '2018-06-01'
  AND had_subsequent_order = FALSE;
```

After these steps, the table had the new column **had_subsequent_order** as a way to quickly determine repurchase per order. Columns for **positive_message** & **negative_message** were added to later include review categories. It was decided to keep 2 columns instead of 1 for easier manipulation in Power BI. These 3 columns were the core columns later utilized in dashboard creation

---

# 5. Review Categorization Using an LLM in Python

**Ollama:** About 30,000 reviews contained messages written in Brazilian Portuguese. A locally hosted LLM, accessed through Ollama, was used to classify these messages into 12 distinct categories, such as delivery not received and easy service, allowing qualitative review text to be transformed into structured data for quantitative analysis.

The category taxonomy was developed manually through iterative trial runs. Initial classifications were manually inspected and the categories were progressively refined until they provided a useful balance between specificity and consistency.

The initial model selected for classification produced accurate results, but its computational requirements would have resulted in an estimated processing time of approximately 20 days. A compromise was found with **Qwen2.5:3B**, which provided sufficiently high classification precision while being substantially faster and clearing the task in 2 days. Classification quality was manually checked on trial outputs before processing the full dataset.

**Python:** Because positive and negative reviews required different classification taxonomies, two filtered copies of the reviews table were created in PostgreSQL, containing only reviews within the respective score ranges. These tables were then exported to CSV and processed in Python. The script handled prompting the LLM with each review message, extracting the resulting category, and periodically saving checkpoints so that processing could be resumed without losing completed classifications.

The Python script initially also validated the model's output against the predefined category list, since the model occasionally generated categories outside the intended taxonomy. This validation step was ultimately removed after it became apparent that these occasional category variations could be more effectively consolidated into the final taxonomy in SQL.

The resulting classified datasets were saved as two CSV files, containing the review messages alongside their assigned categories. These files were then imported back into PostgreSQL using pgAdmin.

**[View the complete Python script](./pictures/review_categorization.py)**

---

# 6. Final Data Preparations

For brevity, the following chapters focus on the processing and analysis of positive messages. The negative messages underwent the same general processing pipeline.

The positive messages were joined to the main orders table using order_id as the linking key. Integrity checks were performed after the joins to verify that the relationships behaved as expected and that no orders were left without an assigned message category:
```sql
UPDATE public.orders o
SET pos_message = p.issue_category
FROM public.pos_messages p
WHERE p.order_id = o.order_id;
```

The original message categories were consolidated into broader analytical categories to reduce fragmentation and improve interpretability. The mapping was performed in SQL as follows:
```sql
UPDATE public.orders
SET pos_message = CASE
    WHEN issue_category LIKE 'RECOMMEN%' THEN 'Unspecified'
    WHEN issue_category LIKE 'SKIPPED' THEN 'Unspecified'
    WHEN issue_category LIKE 'OTHER' THEN 'Unspecified'
    WHEN issue_category LIKE '%PRICE%' THEN 'Value/Price'
    WHEN issue_category LIKE '%VALUE%' THEN 'Value/Price'
    WHEN issue_category LIKE '%SERVICE%' THEN 'Easy/Good Service'
    WHEN issue_category LIKE '%PURCHASE%' THEN 'Easy/Good Service'
    WHEN issue_category LIKE '%PRODUCT%' THEN 'Product Quality'
    WHEN issue_category LIKE '%PACKAGE%' THEN 'Product Quality'
    WHEN issue_category LIKE '%DELIVERY%' THEN 'Good Delivery'
    ELSE pos_message
END;

```

# 7. Statistics and Possible Biases

A minimum sample-size threshold was established to determine when a category's repurchase rate can be considered statistically precise enough for interpretation. The target was a 95% confidence range of approximately ±1 percentage point around the expected 3% repurchase rate.

At a 3% repurchase rate, the standard error for 100 observations is approximately 1.7 percentage points. At 95% confidence, this produces an expected range of approximately ±3.3 percentage points. Since the margin of error decreases with the square root of the sample size, approximately 1,100 observations are required to reduce the 95% margin of error to ±1 percentage point.

**A practical threshold of 1,100 observations** was therefore adopted. Categories below this threshold were not excluded, but their results should be interpreted with greater caution due to their lower statistical precision.

The following table is the result of calculating the p-value of each resulting category against the hypothesis of 2.99% repurchase rate displayed by the general population:

```sql
WITH category_stats AS (
    SELECT
        pos_message,
        COUNT(*) AS sample_size,
        COUNT(*) FILTER (
            WHERE had_subsequent_order = TRUE
        ) AS repurchases
    FROM analysis.all
    WHERE pos_message IS NOT NULL
    GROUP BY pos_message
),

calculations AS (
    SELECT
        pos_message,
        sample_size,
        repurchases,
        repurchases::numeric / sample_size AS repurchase_rate,

        SQRT(
            (repurchases::numeric / sample_size)
            * (1 - repurchases::numeric / sample_size)
            / sample_size
        ) AS standard_error,

        (
            (repurchases::numeric / sample_size) - 0.0299
        )
        / SQRT(
            0.0299 * (1 - 0.0299) / sample_size
        ) AS z_score

    FROM category_stats
)

SELECT
    pos_message,

    ROUND(repurchase_rate * 100, 2) AS repurchase_rate_pct,

    sample_size AS count,

    ROUND(
        (repurchase_rate - 1.96 * standard_error) * 100,
        2
    ) AS error_lower_pct,

    ROUND(
        (repurchase_rate + 1.96 * standard_error) * 100,
        2
    ) AS error_upper_pct,

ROUND(
    (
        2 * (
            1 - (
                0.5 * (
                    1 + erf(ABS(z_score) / SQRT(2))
                )
            )
        )
    )::numeric,
    2
) AS p_value_vs_baseline

FROM calculations
ORDER BY p_value_vs_baseline DESC;
```

| Category          | Repurchase Rate |  Count | Low 95% Range | High 95% Range | P-value vs 2.99% Baseline |
| ----------------- | --------------: | -----: | ------------: | -------------: | ---------------------: |
| Good Delivery     |           2.98% |  4,695 |         2.50% |          3.47% |                   0.94 |
| Value/Price       |           4.24% |    283 |         1.89% |          6.59% |                   0.22 |
| Easy/Good Service |           3.82% |  1,127 |         2.70% |          4.93% |                   0.11 |
| Unspecified       |           3.23% | 32,438 |         3.04% |          3.42% |                   0.02 |
| Product Quality   |           3.98% |  6,132 |         3.49% |          4.47% |                  <0.01 |
| Unsatisfied       |           2.54% | 34,406 |         2.38% |          2.71% |                  <0.01 |

Most categories display statistically significant differences in repurchase rate compared to the 2.99% baseline. The main exception is the "Good Delivery" category, which has a large sample size of 4,695 but a high p-value of 0.94. This indicates that its 2.98% repurchase rate is effectively indistinguishable from the 2.99% general rate, likely because the true repurchase rate for this category is genuinely very close to the baseline. A similar analysis with similar results was made for the negative message categories.

 Potential Biases
- **Review reporting bias:** Customers are more likely to report issues that are easy to identify or describe, or that have a strong emotional impact. This may cause some issues to be over/underrepresented relative to their actual frequency or impact.
- **Review-selection bias:** The customers who choose to leave reviews may differ systematically from those who do not. As a result, the analyzed reviews may not fully represent the experiences or behavior of the entire customer population.
- **Correlation vs. causation:** The review itself is not necessarily causing the lower repurchase rate. Rather, the review category serves as an observable indicator of an underlying customer experience. Therefore, the analysis demonstrates correlation between reported issues and repurchase behavior, rather than causality.
- **LLM classification bias:** The review categorization process introduced potential classification errors. In particular, due to computational resource limitations, each review was assigned only one category, even when a review could reasonably describe multiple issues. This may cause some categories to be overrepresented at the expense of others.
- **Dataset timing:** The Olist database represents a relatively early period in the company's lifetime, when brand recognition was likely lower and customers had had less time to establish purchasing habits. Repurchase rates may therefore be lower than what would be expected from a more established marketplace, limiting the generalizability of the findings to later stages of the company's growth.

# 8. Dashboard Creation

The following DAX measure was created to provide a reusable repurchase rate metric throughout the dashboard:

```text
Repurchase = 
DIVIDE(
    CALCULATE(
        COUNT('analysis all'[customer_unique_id]),
        'analysis all'[had_subsequent_order] = TRUE()),
    COUNT('analysis all'[customer_unique_id]))
```

It was also important to estimate the number of customers potentially lost within each category, including customers who did not leave a review. Under the assumption that customers who left reviews and those who did not are drawn from the same underlying distribution, the following measure was used to extrapolate the observed repurchase behavior of reviewers to the broader customer population:

```text
Good Review Coverage = 
DIVIDE(
    CALCULATE(
        COUNTROWS('analysis all'),
        REMOVEFILTERS('analysis all'),
        'analysis all'[review_score] = 5),
    CALCULATE(
        COUNTROWS('analysis all'),
        REMOVEFILTERS('analysis all'),
        'analysis all'[review_score] = 5,
        'analysis all'[pos_message] <> "Unspecified"))
```

```text
Estimated Repurchases Gained = 
VAR BaselineRate =
    CALCULATE(
        [Repurchase],
        'analysis all'[review_score] = 5,
        REMOVEFILTERS('analysis all'[pos_message]))

VAR HighlightRate =
    [Repurchase]

VAR AffectedCustomers =
    DISTINCTCOUNT(
        'analysis all'[customer_unique_id])

RETURN
    MAX(
        0,
        (HighlightRate - BaselineRate)
            * AffectedCustomers
            * [Good Review Coverage])
```

Since certain categories can be grouped into opposing positive and negative customer experiences (e.g., good delivery vs. delivery delay), the following measure was of many implemented to quantify the difference in repurchase rates between positive and negative feedback within the same category:

```text
Delta Product = 
VAR GoodProduct =
    CALCULATE(
        [Repurchase],
        'analysis all'[pos_message] = "Product Quality")

VAR NegativeProduct =
    CALCULATE(
        [Repurchase],
        'analysis all'[neg_message] IN {
            "Product Damage",
            "Product Quality",
            "Product Mismatch",
            "Product Missing"})

RETURN
    GoodProduct - NegativeProduct
```

Sliders were added to allow users to filter out categories below the recommended sampling threshold, accompanied by an explanatory message indicating the threshold used.

A repurchase-rate-by-time table was considered but ultimately omitted. Because repurchases are attributed to the customer's initial purchase for the purposes of this analysis, subsequent repurchases are associated with the date of the original order. As a result, a temporal visualization would produce an apparent decline in repurchase rates that is largely an artifact of the methodology rather than a genuine trend.

Analysis of additional relationships, such as repurchase rate by state or product, was outside the scope of this project. However, these dimensions could be incorporated in future analyses if they provide meaningful additional insight into the factors associated with customer retention.

[← View Results](README.md)
