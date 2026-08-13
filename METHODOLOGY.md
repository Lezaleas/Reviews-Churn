# Technical Methodology

[Olist Brazilian E-Commerce Dataset](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

# 1. Exploratory Pre-Analysis and Goal Setting

During the initial exploration, it became apparent that the Portuguese review text contained potentially valuable information that was not captured by the structured review score alone. A review of existing analyses of the dataset also showed relatively limited use of the textual review content, particularly through systematic classification of the messages. This gap motivated the decision to classify the reviews into meaningful categories, with the goal of exploring information that would otherwise remain largely unused.

To support this objective, the relevant data required for the analysis was identified. This included review messages and scores, the relationships necessary to associate reviews with individual customers through Reviews -> Order ID -> Customer ID -> Customer Unique ID. Order dates were also required to establish the chronological sequence of purchases and determine whether customers made subsequent purchases after a reviewed order.

---

# 3. Review Categorization by LLM

About 30,000 reviews contained messages written in Brazilian Portuguese. A locally hosted LLM, accessed through Ollama, was used to classify these messages into 12 distinct categories, such as delivery not received and easy service, allowing qualitative review text to be transformed into structured data for quantitative analysis.

The category taxonomy was developed manually through iterative trial runs. Initial classifications were manually inspected and the categories were progressively refined until they provided a useful balance between specificity and consistency.

The initial model selected for classification produced accurate results, but its computational requirements would have resulted in an estimated processing time of approximately 20 days. A compromise was found with **Qwen2.5:3B**, which provided sufficiently high classification precision while being substantially faster and clearing the task in 2 days. Classification quality was manually checked on trial outputs before processing the full dataset.

Because positive and negative reviews required different classification taxonomies, two filtered copies of the reviews table were created in PostgreSQL, containing only reviews within the respective score ranges. These tables were then exported to CSV and processed in Python. The script handled prompting the LLM with each review message, extracting the resulting category, and periodically saving checkpoints so that processing could be resumed without losing completed classifications.

The Python script initially also validated the model's output against the predefined category list, since the model occasionally generated categories outside the intended taxonomy. This validation step was ultimately ignored after it became apparent that the model's occasional category variations could be more effectively consolidated into the final taxonomy in SQL.

[View the complete Python script](./scripts/classify_reviews.py)

```python
SYSTEM_PROMPT = """
You classify Brazilian Portuguese customer reviews into the CATEGORY described in the review. Choose exactly ONE category from this list:
OTHER, QUICK_DELIVERY, GOOD_PRODUCT_QUALITY, GOOD_PRICE, GOOD_SERVICE, EASY_PURCHASE
"""
response = ollama.chat(model=MODEL, messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}, ], options={"temperature": 0},)

#-------------------------------------------------------------------------------------

for i, row in enumerate(rows):
    value = row.get(OUTPUT_COLUMN, "").strip()
    if not value:
        start_index = i    # we start on the first empty column found
        break

#-------------------------------------------------------------------------------------

temp_file = INPUT_CSV + ".tmp"    # it's important to save in a temporary file to prevent waste of time by data corruption
with open(temp_file, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=fieldnames,
        extrasaction="ignore",
    )
    writer.writeheader()
    writer.writerows(rows)
os.replace(temp_file, INPUT_CSV)
```



# 2. Data Structure

A new table was created with the appropriate joins as can be seen in the diagram

```sql
Relevant
```

# 3. Data Cleaning & Validation

- Starting from 100k reviews, 800 of them had null review score. It was decided to discard them to not introduce ambiguity later in the analysis, after checking that they are distributed similarly to the rest of the data set.

- There was a column for review message titles. The majority of them were variations on *Recomendo, Otimo, Nao Recomendo*, which hint towards general sentiment rather than specific issues. Since It's less ambiguous to get this information from review scores, this column was ignored

- About 700 reviews were had duplicated order ids. This is because a customer can leave multiple reviews in the same transaction. To make things simple, it was decided to keep the last, since it's the most likely one to represent final customer sentiment.

```sql
Relevant
```

Examples:

* Missing values
* Duplicate records
* Invalid dates
* Invalid identifiers
* Impossible values
* Inconsistent categories
* Out-of-range values
* Encoding issues

## 4.2 Missing Values

Explain separately how different types of missingness were handled.

### Missing because information was unavailable

### Missing because the concept was not applicable

### Missing because of data-generation limitations

Explain why these were **not automatically treated as equivalent**.

## 4.3 Duplicate Records

Explain:

* How duplicates were detected
* What constituted a true duplicate
* Whether duplicates were removed
* Which record was retained and why

```python
# Duplicate detection
```

## 4.4 Outliers / Invalid Observations

Document observations that were excluded or transformed.

For each exclusion:

| Condition | Records affected | Treatment | Reason |
| --------- | ---------------: | --------- | ------ |
|           |                  |           |        |

Important distinction:

> An observation was excluded because it was invalid for the analytical question, not merely because it was statistically unusual.

---

# 5. Defining the Analytical Population

This section is particularly important because downstream statistics depend on **which observations are allowed into the analysis**.

## 5.1 Inclusion Criteria

Define exactly which observations qualify.

```text
Include observations where:
- ...
- ...
- ...
```

## 5.2 Exclusion Criteria

Document every exclusion.

```text
Exclude observations where:
- ...
- ...
- ...
```

## 5.3 Consequences of Filtering

Explain what each major filter changes about the population.

Avoid discussing the resulting business insight; focus on methodological consequences.

---

# 6. Customer & Purchase Identification

## 6.1 Customer Identifier Choice

Explain the distinction between:

* `customer_id`
* `customer_unique_id`

and why one was selected for customer-level analysis.

## 6.2 Order-Level vs. Customer-Level Analysis

Explain when the analysis operates at:

* Order level
* Customer level
* Review level
* Product level

and why mixing these levels could introduce bias.

## 6.3 First-Purchase Identification

Explain how the first purchase was determined.

```python
# Relevant code
```

Discuss:

* Sorting logic
* Ties
* Multiple orders on the same date
* Whether order timestamps were available
* How ambiguous cases were handled

## 6.4 Subsequent Purchase Definition

Define precisely what qualifies as a repeat purchase.

For example:

```text
repeat_customer =
    customer has >= 2 qualifying orders
```

Explain why this definition was chosen.

---

# 7. Review Classification

## 7.1 Motivation

Explain why review text was classified rather than relying exclusively on the existing review score.

## 7.2 Classification Taxonomy

Document the categories and their definitions.

| Category                | Definition | Examples / boundary |
| ----------------------- | ---------- | ------------------- |
| `NO_ISSUE`              |            |                     |
| `DELIVERY_DELAY`        |            |                     |
| `DELIVERY_NOT_RECEIVED` |            |                     |
| `DAMAGED_PRODUCT`       |            |                     |
| `PRODUCT_QUALITY`       |            |                     |
| `PRODUCT_DIFFERENT`     |            |                     |
| `MISSING_ITEM`          |            |                     |
| `PAYMENT`               |            |                     |
| `SERVICE`               |            |                     |
| `OTHER`                 |            |                     |
| `UNSPECIFIED`           |            |                     |

## 7.3 LLM Classification

Document:

* Model used
* Model version
* Prompt design
* Output format
* Temperature/settings
* Batch processing
* Error handling
* Retry logic
* Persistence/checkpointing

```python
# Classification code
```

## 7.4 Classification Rules

Explain how ambiguous reviews were handled.

Examples:

* Multiple complaints in one review
* Praise + complaint
* Reviews with no meaningful text
* Extremely short reviews
* Sarcasm
* Unclear responsibility
* Reviews mentioning delivery and product simultaneously

## 7.5 Classification Validation

Explain how classification quality was checked.

Possible methods:

* Manual sample inspection
* Confusion matrix
* Inter-rater agreement
* Repeated classification
* Rule-based sanity checks
* Category frequency checks

If no formal validation was performed, explicitly state that.

---

# 8. Feature Engineering

Document every derived variable.

For each feature:

### `feature_name`

**Definition:**

**Purpose:**

**Calculation:**

```python
# code
```

**Potential edge cases:**

**Why this definition was chosen:**

Relevant examples:

* `is_first_purchase`
* `purchases_so_far`
* `days_since_previous_purchase`
* `had_subsequent_order`
* `review_category`
* `is_repeat_customer`

---

# 9. Statistical Methodology

## 9.1 Descriptive Statistics

Explain which statistics were used and why.

Potential measures:

* Mean
* Median
* Standard deviation
* Percentiles
* Count
* Proportion
* Rate

Discuss when each measure is appropriate for the distribution being analyzed.

## 9.2 Rates and Proportions

Define the denominator explicitly.

For example:

[
\text{Repeat Rate} =
\frac{\text{customers with a subsequent purchase}}
{\text{eligible customers}}
]

Explain:

* Numerator
* Denominator
* Eligibility criteria
* Why this denominator was chosen

## 9.3 Sample Size Considerations

Explain whether categories with very small sample sizes were:

* Excluded
* Grouped
* Displayed with warnings
* Retained but interpreted cautiously

Explain the rationale.

## 9.4 Uncertainty

If confidence intervals or hypothesis tests are used, document:

* Statistical test
* Null hypothesis
* Alternative hypothesis
* Significance level
* Confidence interval method
* Assumptions
* Why the test was appropriate

```python
# Statistical test
```

## 9.5 Correlation vs. Causation

Explicitly describe the analytical limitations.

The analysis measures associations between variables. It does not establish that a review category **causes** a subsequent purchase or loss unless an appropriate causal design is present.

---

# 10. Handling Potential Bias

Discuss methodological sources of bias.

## 10.1 Selection Bias

Could the analyzed customers differ systematically from excluded customers?

## 10.2 Survivorship Bias

Could customers who remain observable for longer have a greater opportunity to make another purchase?

## 10.3 Observation Window

Explain how the available time period affects the opportunity to observe repeat purchases.

## 10.4 Review Bias

Consider:

* Who leaves reviews
* Whether unhappy customers are more likely to leave reviews
* Whether review text is missing
* Whether review scores affect review behavior

## 10.5 Class Imbalance

Discuss whether some review categories are much more common than others and how that affects analysis.

---

# 11. Edge Cases & Exceptions

Document unusual situations explicitly.

### 11.1 Multiple Orders on the Same Date

### 11.2 Missing Review Text

### 11.3 Customers with Multiple Identifiers

### 11.4 Orders Without Reviews

### 11.5 Reviews Without Valid Orders

### 11.6 Extremely Small Categories

### 11.7 Ambiguous Classifications

### 11.8 Invalid / Impossible Values

For each:

**Problem → Decision → Reason → Implementation**

---

# 12. SQL Analysis

Explain why SQL was used for each stage rather than treating the SQL merely as implementation.

## 12.1 Data Transformation

```sql
-- Relevant SQL
```

Explain:

* Joins
* CTEs
* Aggregations
* Window functions
* Filtering
* Deduplication

## 12.2 Window Functions

Explain any use of:

```sql
ROW_NUMBER()
LAG()
LEAD()
SUM() OVER (...)
COUNT() OVER (...)
```

and why a window function was preferable to a conventional aggregation.

## 12.3 Reproducibility

Explain how the SQL analysis can be reproduced from the cleaned database.

---

# 13. Python Analysis

## 13.1 Libraries

| Library  | Purpose              |
| -------- | -------------------- |
| `pandas` | Data manipulation    |
| `numpy`  | Numerical operations |
| `scipy`  | Statistical analysis |
| `...`    |                      |

## 13.2 Analytical Code Structure

Explain how Python was used for:

* Data transformation
* Statistical analysis
* Classification
* Validation
* Exporting results

```python
# Representative analytical code
```

---

# 14. Power BI Data Preparation

## 14.1 Data Model

Explain:

* Tables imported
* Relationships
* Granularity
* Measures vs. calculated columns

## 14.2 DAX Measures

Document important measures and the reasoning behind them.

```DAX
-- Measure
```

Explain:

* What it calculates
* Filter context
* Why it was implemented as a measure
* Any edge cases

## 14.3 Filtering Logic

Explain important dashboard filters and why they were implemented.

Examples:

* Minimum sample size
* Review category
* Customer population
* Date range

---

# 15. Quality Assurance

## 15.1 Data Validation

Checks performed after cleaning:

* Row counts
* Unique customer counts
* Unique order counts
* Null checks
* Referential integrity
* Date consistency
* Category validity

## 15.2 Analytical Validation

Cross-check important calculations using independent methods where possible.

Example:

```python
# Python calculation
```

versus

```sql
-- SQL calculation
```

## 15.3 Dashboard Validation

Verify that:

* Totals reconcile with source data
* Filters behave correctly
* Percentages use the correct denominator
* Small samples are handled correctly
* Measures do not double-count customers

---

# 16. Reproducibility

Document the complete analytical pipeline:

```text
Raw Dataset
     ↓
Data Cleaning
     ↓
PostgreSQL
     ↓
Python / LLM Classification
     ↓
Feature Engineering
     ↓
SQL Analysis
     ↓
Power BI Dataset
     ↓
Dashboard
```

Include:

* Required software
* Python version
* Database requirements
* Dependencies
* Environment setup
* Execution order
* Required files
* Configuration variables

---

# 17. Methodological Limitations

This section should discuss **limitations of the methodology**, not the results.

Potential topics:

* Observational dataset
* Limited observation window
* Missing information
* LLM classification uncertainty
* Small categories
* Customer identification limitations
* Review-selection bias
* Lack of experimental controls
* Potential confounding variables
* Measurement-definition choices

---

# 18. Design Decisions & Alternatives Considered

Document decisions where multiple reasonable approaches existed.

| Decision                   | Chosen approach | Alternative | Reason |
| -------------------------- | --------------- | ----------- | ------ |
| Customer identifier        |                 |             |        |
| Repeat purchase definition |                 |             |        |
| Missing values             |                 |             |        |
| Review classification      |                 |             |        |
| Small samples              |                 |             |        |
| Statistical test           |                 |             |        |

This section is particularly useful for demonstrating **analytical judgment rather than merely technical implementation**.

---

# 19. Reproducibility Checklist

* [ ] Raw data can be identified
* [ ] Cleaning steps are documented
* [ ] Exclusions are documented
* [ ] Derived variables are defined
* [ ] Classification methodology is documented
* [ ] SQL transformations are available
* [ ] Python dependencies are documented
* [ ] Statistical methods are documented
* [ ] DAX measures are documented
* [ ] Edge cases are documented
* [ ] Validation checks are documented
* [ ] Known limitations are documented

---

# Appendix A — Complete SQL

Include the full SQL used for the analysis, rather than only representative snippets.

# Appendix B — Complete Python

Include scripts that are necessary to reproduce the analytical pipeline.

# Appendix C — Classification Prompt

Include the final LLM prompt and output specification.

# Appendix D — Data Dictionary

| Field | Type | Source | Definition | Transformation |
| ----- | ---- | ------ | ---------- | -------------- |
|       |      |        |            |                |

# Appendix E — Additional Validation

Document supplementary checks that are useful for a technical reviewer but not important enough for the main methodology.
