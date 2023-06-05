import openai_utils
import csv
import time
# Function that takes a value and returns a dictionary
def process_value(value):
    # Your logic to process the value and return a dictionary
    # For demonstration, let's assume the value is a string and return a dictionary with fixed values
    return openai_utils.get_openai_dict_scores(value)

# Path to the input CSV file
input_file = "harassment.csv"

# Path to the output CSV file
output_file = "harassment-output.csv"

# Open input and output files
with open(input_file, "r") as csv_input, open(output_file, "w", newline="") as csv_output:
    reader = csv.reader(csv_input)
    writer = csv.writer(csv_output)

    # Read the header row
    header = next(reader)

    # Process the header value and get the dictionary keys
    header_value = header[0]
    # header_dict = process_value(header_value)
    # print(header_dict)
    # assert len(header_dict.keys()) == 9
    # keys = list(header_dict.keys())

    # Extend the header row with the dictionary keys
    # header.extend(keys)
    writer.writerow(header)

    # Process each row and append the dictionary values to the row
    count = 0
    for row in reader:
        value = row[0]
        try:
            row_dict = process_value(value)
        except:
            print("Error")
            time.sleep(5)
            continue
        if (len(row_dict.keys()) != 9):
            row_dict = process_value(value)
            if (len(row_dict.keys()) != 9):
                print("Skipping...")
                continue
        # Create a new row by appending the dictionary values
        new_row = row + [row_dict[key] for key in row_dict.keys()]
        writer.writerow(new_row)
        count += 1
        time.sleep(1)
        print("processing.." + str(count))
print("CSV processing completed!")