import csv

#This is a simple tld and compound tld parser, should only be used on apex domains, will not work on fqdn. Used to parse tld's from NOD. 

def dissect_domains(filename):
    with open(filename, 'r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip the header
        domains = [row[0] for row in reader]  # Assumes domain is the first column

    dissected_domains = []
    for domain in domains:
        period_count = domain.count('.')
        if period_count == 2:
            dissected_domains.append(domain.split('.', 1)[1])
        elif period_count >= 3:
            dissected_domains.append(domain.split('.', 2)[2])

    with open('dissected_domains.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Dissected Domain"])
        for domain in dissected_domains:
            writer.writerow([domain])

dissect_domains('domains.csv')  # replace with the path to your CSV file
