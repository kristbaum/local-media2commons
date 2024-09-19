import requests
import csv
import time


def check_file_exists_on_commons(sha1):
    url = "https://commons.wikimedia.org/w/api.php"
    params = {
        "action": "query",
        "list": "allimages",
        "aisha1": sha1,
        "format": "json",
    }

    response = requests.get(url, params=params)
    data = response.json()

    # If the list of allimages is not empty, the file exists on Commons
    if data["query"]["allimages"]:
        return True
    else:
        return False


def check_files_from_csv(
    input_filename, output_filename, log_interval=10, skip_lines=33688
):
    start_time = time.time()
    processed_count = 0
    skipped_count = 0

    with open(input_filename, mode="r", newline="", encoding="utf-8") as infile:
        reader = csv.DictReader(infile)

        # Skip the first `skip_lines` rows
        for _ in range(skip_lines):
            next(
                reader, None
            )  # Advance the reader by one line, skip `None` when end is reached
            skipped_count += 1
            if skipped_count % log_interval == 0:
                print(f"Skipped {skipped_count} rows.")

        # Prepare the output CSV file
        with open(output_filename, mode="a", newline="", encoding="utf-8") as outfile:
            fieldnames = ["title", "sha1", "url", "exists_on_commons"]
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)

            # Check if the output file is empty and write the header if it is
            if outfile.tell() == 0:
                writer.writeheader()

            # Process each remaining row from the input CSV
            for row in reader:
                sha1 = row["sha1"]
                title = row["title"]
                url = row["url"]

                try:
                    # Check if the file exists on Wikimedia Commons using its SHA-1 hash
                    exists = check_file_exists_on_commons(sha1)

                    # Write the result to the output CSV
                    writer.writerow(
                        {
                            "title": title,
                            "sha1": sha1,
                            "url": url,
                            "exists_on_commons": exists,
                        }
                    )

                    processed_count += 1

                    # Log progress every `log_interval` rows
                    if processed_count % log_interval == 0:
                        elapsed_time = time.time() - start_time
                        print(
                            f"Processed {processed_count} rows in {elapsed_time:.2f} seconds."
                        )

                except Exception as e:
                    print(f"Error processing file '{title}': {e}")
                    continue

                time.sleep(0.1)  # Add a small delay to avoid hitting API limits

    print(
        f"Completed processing {processed_count} files after skipping {skipped_count} rows. Results have been saved to '{output_filename}'."
    )


# Example usage
input_filename = "image_sha1_data.csv"  # Replace this with your actual CSV file name
output_filename = (
    "commons_check_results.csv"  # Output file where the results will be saved
)

# Run the function to check SHA-1 hashes from the CSV, skipping the first 33,688 lines
check_files_from_csv(input_filename, output_filename, log_interval=10, skip_lines=36688)
