# Analyzing Customer Review Messages with LLMs to Identify Key Drivers of Churn and Retention

Customer churn and repurchase behavior are critical metrics for business sustainability, yet unstructured qualitative data—such as customer review messages—often remains underutilized due to manual classification bottlenecks.

This project leverages Large Language Models (LLMs) to perform zero-shot categorization of unstructured customer reviews written in Brazilian Portuguese for Olist. By transforming free-form feedback into structured categories, the analysis identifies customer friction points and quantifies their relationship with churn and repurchase behavior. The resulting insights highlight which types of customer issues are most strongly associated with lost customers, providing actionable opportunities to improve retention.

---

**Executive Summary**
<br>• Delivery issues were the negative feedback category most strongly associated with churn, cutting customer repurchase rates in half compared to the baseline. <br>• Positive feedback around product quality was strongly associated with higher repurchase rates. <br>• The overall customer repurchase rate was 3%, highlighting a significant retention challenge and raising questions about long-term customer value.


---
| Category | Insight | Recommendation |
| :--- | :--- | :--- |
| **Delivery Issues** | • **Primary Churn Driver:** Accounted for **2/3 of customer losses** observed in the study.<br>• **Highest Negative Volume:** Represented the most common negative feedback theme and correlated with the lowest repurchase rate (**1.6% vs. 3.3% baseline**).<br>• **Asymmetric Impact:** Positive delivery praise showed little to no effect on boosting repurchase rates. | • **Address Baseline Expectations:** On-time delivery is expected as standard service; preventing delays matters far more than over-performing.<br>• **Investigate Root Causes:** A follow-up analysis on delivery timestamps and freight costs will help identify specific bottlenecks.<br>• **Brand Messaging:** Focus marketing copy around reliability and shipment consistency. |
| **Product Quality Praise** | • **Highest Retention Engine:** Appeared in **50% of all positive reviews** containing a message and drove the **2nd highest repurchase rate (~4%)**.<br>• **Delight Factor:** Unlike delivery (where speed is merely expected), customers are highly receptive and gladly surprised by exceptional product quality.<br>• **Low Churn Risk:** Negative reviews regarding product quality did not correlate strongly with churn, highlighting a total opposite dynamic to delivery friction. | • **Seller Quality Incentives:** Implement a seller encouragement program (e.g., fee discounts, badge priority) for merchants with high quality scores.<br>• **Surprise-and-Delight Marketing:** Center campaigns around exceeding product expectations and spotlighting individual customer unboxing anecdotes.<br>• **Leverage Quality Assets:** Feature real customer praise stories in retention emails to drive repeat purchases. |
