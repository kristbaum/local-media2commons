import requests
import csv


def get_all_image_sha1s():
    url = "https://www.fuerthwiki.de/wiki/api.php"
    params = {
        "action": "query",
        "list": "allimages",
        "ailimit": "500",
        "aiprop": "sha1",
        "format": "json",
    }

    sha1_list = []
    continue_param = None

    while True:
        if continue_param:
            params["aicontinue"] = continue_param

        response = requests.get(url, params=params)
        data = response.json()

        # Collect SHA-1 values from the response
        for image in data["query"]["allimages"]:
            title = image["title"]
            sha1 = image["sha1"]
            # Create the full URL for the image
            image_url = f"https://www.fuerthwiki.de/wiki/File:{title.replace(' ', '_')}"
            sha1_list.append({"title": title, "sha1": sha1, "url": image_url})

        # Check if there's more data to continue
        if "continue" in data:
            continue_param = data["continue"]["aicontinue"]
        else:
            break  # No more pages

    return sha1_list


def save_to_csv(sha1_data, filename="image_sha1_data.csv"):
    # Specify the field names (columns) for the CSV
    fieldnames = ["title", "sha1", "url"]

    # Write the data to a CSV file
    with open(filename, mode="w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        # Write the header row
        writer.writeheader()

        # Write each row of image data
        for image in sha1_data:
            writer.writerow(image)


# Run the function and save the data to a CSV file
sha1_data = get_all_image_sha1s()
save_to_csv(sha1_data)

print(f"Data has been saved to 'image_sha1_data.csv'")
