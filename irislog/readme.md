# IrisLog

## Overview

The IrisLog application is designed to seamlessly integrate with the Iris Investigate API, enabling the creation of realistic synthetic logs across various SIEM platforms. Key features include:

- **Integration with Iris Investigate API**: IrisLog works hand-in-hand with the Iris Investigate API, pulling in rich domain data and weaving it into the generated logs, providing a realistic and context-rich simulation.
- **Wide Range of Platform Support**: The application includes log templates for a variety of potential log generating platforms such as Palo Alto Firewall, Microsoft Exchange, Windows DNS, Palo Alto Cortex XDR, and ProofPoint.
- **Customizable Log Generation**: Users can tailor the log output to match the specific scenarios and requirements of their SIEM environment.

## Getting Started

To integrate IrisLog with the Iris Investigate API and start generating synthetic logs, follow these steps:

1. Ensure you have access to the Iris Investigate API and your DomainTools credentials.
2. Clone the repository or download the files to your machine.
3. Configure the `irislog.py` script with your DomainTools API credentials and set up the desired log output.
4. Edit the `SIEM_CONFIGS` in the configuration file to target the specific SIEM platform you want to generate logs for. Currently, Elastic and Splunk are supported, but more can be added upon request to the author.
5. Run the script to start generating logs, and use them in your SIEM platform to enrich your demo environment.

## Customization and Expansion

IrisLog is built with customization and scalability in mind. To add new log templates or modify existing ones:

1. Extend the `log_templates.py` file with new classes for additional log types, ensuring they inherit from the `LogTemplate` base class.
2. Populate the `LOG_TEMPLATES` class variable with your custom log formats.
3. If needed, implement specific log generation logic within your class to cater to complex requirements or to integrate additional data points from the Iris Investigate API.
4. You also have the option of editing `SEARCH_HASH` that is used to retrieve the domain information. The default hash looks for domains first_seen in the last hour and with a risk score of 99.

Feel free to contribute to the project by submitting pull requests or opening issues for any bugs or feature requests.



