import csv
import os
import time
import ollama

# -----------------------------
# Configuration
# -----------------------------
INPUT_CSV = "pos_reviews.csv"
MODEL = "qwen2.5:3b"
OUTPUT_COLUMN = "issue_category"
RETRY_SECONDS = 10

# -----------------------------
# Prompt
# -----------------------------
SYSTEM_PROMPT = """
You classify Brazilian Portuguese customer reviews into the CATEGORY described
in the review. We are looking for positive feedback, if the review is negative or neutral, choose OTHER

Choose exactly ONE category from this list, and make sure the answer is on this list:

OTHER
QUICK_DELIVERY
GOOD_PRODUCT_QUALITY
GOOD_PRICE
GOOD_SERVICE
EASY_PURCHASE
"""

VALID_CATEGORIES = {
    "OTHER",
    "QUICK_DELIVERY",
    "GOOD_PRODUCT_QUALITY",
    "GOOD_PRICE",
    "GOOD_SERVICE",
    "EASY_PURCHASE"
}


def classify_review(review_title, review_message, review_score):
    title = review_title.strip() if review_title else ""
    message = review_message.strip() if review_message else ""

    # No message = skip before reaching Ollama.
    if not message:
        return None

    prompt = f"""Review score: {review_score}

Review title:
{title}

Review message:
{message}
"""

    response = ollama.chat(
        model=MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        options={
            "temperature": 0,
        },
    )

    result = response["message"]["content"].strip().upper()

    # Clean up occasional formatting from the model.
    result = result.replace("`", "").replace('"', "").strip()

    # If Qwen adds extra text, try to find a valid category in it.
    if result not in VALID_CATEGORIES:
        for category in VALID_CATEGORIES:
            if category in result:
                return category

        print(f"WARNING: Unexpected model output: {result!r}")
        return result

    return result


def load_csv():
    with open(INPUT_CSV, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def save_csv(rows, fieldnames):
    temp_file = INPUT_CSV + ".tmp"

    with open(temp_file, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)

    while True:
        try:
            os.replace(temp_file, INPUT_CSV)
            break
        except PermissionError:
            print(f"\nFile is temporarily locked. Retrying in {RETRY_SECONDS} seconds...")
            try:
                time.sleep(RETRY_SECONDS)
            except KeyboardInterrupt:
                print("\nInterrupted while waiting for the file lock to clear.")
                raise


def main():
    rows = load_csv()

    if not rows:
        print("CSV is empty.")
        return

    fieldnames = list(rows[0].keys())

    # Add the result column if it doesn't exist.
    if OUTPUT_COLUMN not in fieldnames:
        fieldnames.append(OUTPUT_COLUMN)

        for row in rows:
            row[OUTPUT_COLUMN] = ""

    # Find the first row that hasn't been classified.
    start_index = None

    for i, row in enumerate(rows):
        value = row.get(OUTPUT_COLUMN, "").strip()

        if not value:
            start_index = i
            break

    if start_index is None:
        print("All reviews have already been classified.")
        return

    print(f"Found {len(rows):,} reviews.")
    print(f"Starting at row {start_index + 1:,}.")
    print(f"Using model: {MODEL}")
    print(f"Retry delay: {RETRY_SECONDS} seconds")
    print()

    for i in range(start_index, len(rows)):
        row = rows[i]

        review_id = row.get("review_id", "")
        title = row.get("review_comment_title", "")
        message = row.get("review_comment_message", "")
        score = row.get("review_score", "")

        # Completely skip reviews without a message.
        if not message or not message.strip():

            row[OUTPUT_COLUMN] = "SKIPPED"

            # Save the skip so the program doesn't process it again
            # if restarted.
            save_csv(rows, fieldnames)
            continue


        # Retry indefinitely until the classification succeeds.
        while True:
            try:
                category = classify_review(
                    title,
                    message,
                    score,
                )

                row[OUTPUT_COLUMN] = category

                # Save immediately after every successful classification.
                save_csv(rows, fieldnames)

                break

            except KeyboardInterrupt:
                print("\nInterrupted. Progress has already been saved.")
                return

            except Exception as e:
                print(f"\nERROR: {e}")
                print(
                    f"Retrying in {RETRY_SECONDS} seconds..."
                )

                try:
                    time.sleep(RETRY_SECONDS)
                except KeyboardInterrupt:
                    print("\nInterrupted. Progress has already been saved.")
                    return


if __name__ == "__main__":
    main()