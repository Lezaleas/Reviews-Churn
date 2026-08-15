WITH category_stats AS (
    SELECT
        neg_message,
        COUNT(*) AS sample_size,
        COUNT(*) FILTER (
            WHERE had_subsequent_order = TRUE
        ) AS repurchases
    FROM analysis.all
    WHERE neg_message IS NOT NULL
    GROUP BY neg_message
),

calculations AS (
    SELECT
        neg_message,
        sample_size,
        repurchases,
        repurchases::numeric / sample_size AS repurchase_rate,

        SQRT(
            (repurchases::numeric / sample_size)
            * (1 - repurchases::numeric / sample_size)
            / sample_size
        ) AS standard_error,

        (
            (repurchases::numeric / sample_size) - 0.03
        )
        / SQRT(
            0.03 * (1 - 0.03) / sample_size
        ) AS z_score

    FROM category_stats
)

SELECT
    neg_message,

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
    4
) AS p_value

FROM calculations
ORDER BY p_value DESC;