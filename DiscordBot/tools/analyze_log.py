# Example tool that shows how the logs can be analayzed to draw conclusions. 
# In this example, the 

with open("../logging/log.txt") as file:
    # A report is valid if the reviewer agrees it violated content
    num_valid_reports = 0

    # A report is invalid if the reviewer disagrees it violated content
    num_invalid_reports = 0

    # Total number of reports that have been reviewed
    report_count = 0

    for line in file:
        parts = line.strip().split("|")
        report_valid = parts[3]

        if report_valid == "True":
            num_valid_reports += 1
        else:
            num_invalid_reports += 1

        report_count += 1


    print(f"The total number of reports {report_count}")
    print(f"The number of valid reports {num_valid_reports}")
    print(f"The number of invalid reports {num_invalid_reports}")