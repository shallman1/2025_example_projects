from datetime import datetime
import random

class LogTemplate:
    LOG_TEMPLATES = []

    def _generate_microtimestamp(self):
        now = datetime.now()
        return "{}.{:05}.{:05}".format(now.strftime('%Y%m%d%H%M%S'), now.microsecond // 10, (now.microsecond % 10) * 10**4)

    def generate_logs(self, domain_details):
        logs = []
        microtimestamp = self._generate_microtimestamp()
        for result in domain_details['response']['results']:
            timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.000Z')
            ip_address = '0.0.0.0'
            
            if 'ip' in result and isinstance(result['ip'], list) and len(result['ip']) > 0:
                ip_address = result['ip'][0].get('address', {}).get('value', '0.0.0.0')
                
            domain_name = result['domain']
            template = random.choice(self.LOG_TEMPLATES)
            log = template.format(timestamp=timestamp, domain_name=domain_name, ip_address=ip_address, microtimestamp=microtimestamp)
            logs.append(log)
        return logs
    
class PaloAltoFirewallLogTemplate(LogTemplate):
    LOG_TEMPLATES = [
        "{timestamp} src_zone=Trust dst_zone=Untrust src_ip=192.168.1.10 dst_ip={ip_address} url={domain_name}",
        "{timestamp} src_zone=Untrust dst_zone=Trust src_ip={ip_address} dst_ip=192.168.1.20 url={domain_name}",
        "{timestamp} src_zone=DMZ dst_zone=Untrust src_ip={ip_address} dst_ip=192.168.1.30 url={domain_name}",
        "{timestamp} src_zone=Untrust dst_zone=DMZ src_ip={ip_address} dst_ip=192.168.2.20 url={domain_name}",
        "{timestamp} src_zone=Trust dst_zone=Untrust src_ip=192.168.2.30 dst_ip={ip_address} url={domain_name}",
        "{timestamp} src_zone=DMZ dst_zone=Trust src_ip=192.168.1.40 dst_ip={ip_address} url={domain_name}",
        "{timestamp} src_zone=Untrust dst_zone=Untrust src_ip={ip_address} dst_ip=192.168.1.50 url={domain_name}",
        "{timestamp} src_zone=Trust dst_zone=Trust src_ip=192.168.1.60 dst_ip={ip_address} url={domain_name}",
        "{timestamp} src_zone=DMZ dst_zone=DMZ src_ip={ip_address} dst_ip=192.168.1.70 url={domain_name}",
    ]

class MicrosoftExchangeLogTemplate(LogTemplate):
    LOG_TEMPLATES = [
        "{timestamp},08D8FAB376ADEFCE,SMTP,RECEIVE,8834HBD0-9D43-6C17-A4DA-9287F8G7H5I5,1,,{ip_address},,aperkins@{domain_name},,203,1,,<{microtimestamp}@{domain_name}>,mscott@dundermifflin.com,08D8FAB376ADEFCE;{timestamp};0,receiving message",
        "{timestamp},04D8DPB376ADIUKL,SMTP,SEND,6612F98B-7D21-4A15-82B8-8065D6E5F3E3,1,,{ip_address},,rswanson@{domain_name},,103,1,,<{microtimestamp}@{domain_name}>,dschrute@dundermifflin.com,04D8DPB376ADIUKL;{timestamp};0,sending message",
        "{timestamp},07DJ9KLD62DJ9VN2,SMTP,RECEIVE,7723GAC9-8C32-5B16-93C9-9176E7F6G4F4,1,,{ip_address},,aludgate@{domain_name},,301,2,,<{microtimestamp}@{domain_name}>,abernard@dundermifflin.com,07DJ9KLD62DJ9VN2;{timestamp};0,delivery failed",
        "{timestamp},09HBGY4347NYDUE3,SMTP,RECEIVE,BB23ZA9A-7J21-5F16-82J1-8H63D7E2G7I8,1,,{ip_address},,bBrendanawicz@{domain_name},,202,1,,<{microtimestamp}@{domain_name}>,jhalpert@dundermifflin.com,09HBGY4347NYDUE3;{timestamp};0,receiving message",
        "{timestamp},O3J89FG876JDIUTY,SMTP,SEND,LSK22F98B-7T21-1L15-87K8-87P5J4O5Y8Z3,1,,{ip_address},,lknope@{domain_name},,101,1,,<{microtimestamp}@{domain_name}>,pbeesley@dundermifflin.com,O3J89FG876JDIUTY;{timestamp};0,sending message",
        "{timestamp},07DJ9HJS54AT9BR2,SMTP,RECEIVE,6A97GAJ8-8D88-6B15-96J7-9B72E7F6W4Z4,1,,{ip_address},,jgergich@{domain_name},,305,2,,<{microtimestamp}@{domain_name}>,shudson@dundermifflin.com,07DJ9HJS54AT9BR2;{timestamp};0,delivery failed",
        "{timestamp},05RSKDI302KDJVCP,SMTP,RECEIVE,ABC12XYZ-7M21-9N16-82N1-8M63E7X2Z9J8,1,,{ip_address},,thaverford@{domain_name},,204,1,,<{microtimestamp}@{domain_name}>,rhoward@dundermifflin.com,05RSKDI302KDJVCP;{timestamp};0,receiving message",
        "{timestamp},X9J89HG876KDIJKY,SMTP,SEND,QSK32Z98C-7Z21-1Z25-89Z8-98Q5S4O6Y1C3,1,,{ip_address},,bwyatt@{domain_name},,102,1,,<{microtimestamp}@{domain_name}>,mpalmer@dundermifflin.com,X9J89HG876KDIJKY;{timestamp};0,sending message",
        "{timestamp},07DJ9EJS36XT9SFR2,SMTP,FAIL,6C97GAJ8-8D36-6V15-98J7-9R72E7M6Y6Z6,1,,{ip_address},,adwyer@{domain_name},,306,2,,<{microtimestamp}@{domain_name}>,ehannon@dundermifflin.com,07DJ9EJS36XT9SFR2;{timestamp};0,delivery failed",
    ]
class WindowsDnsLogTemplate(LogTemplate):
    LOG_TEMPLATES = [
        "{timestamp},192.168.1.11,{ip_address},A,{domain_name}",
        "{timestamp},192.168.1.37,{ip_address},A,{domain_name}",
        "{timestamp},192.168.1.12,{ip_address},CNAME,{domain_name}",
        "{timestamp},192.168.1.40,{ip_address},A,{domain_name}",
        "{timestamp},192.168.1.81,{ip_address},A,{domain_name}",
        "{timestamp},192.168.1.22,{ip_address},SOA,{domain_name}",
        "{timestamp},192.168.1.77,{ip_address},NS,{domain_name}",
        "{timestamp},192.168.1.20,{ip_address},A,{domain_name}",
        "{timestamp},192.168.1.87,{ip_address},TXT,{domain_name}",
        "{timestamp},192.168.1.101,{ip_address},SPF,{domain_name}",
    ]

class PaloAltoCortexXDR(LogTemplate):
    LOG_TEMPLATES = [
        "{timestamp} src_zone=Trust dst_zone=Untrust src_ip=103.7.199.196 dst_ip={ip_address} url={domain_name}",
        "{timestamp} src_zone=DMZ dst_zone=Trust src_ip=103.7.199.196 dst_ip={ip_address} url={domain_name}",
        "{timestamp} src_zone=Untrust dst_zone=DMZ src_ip=103.7.199.196 dst_ip={ip_address} url={domain_name}",
    ]

class ProofPoint_email_log(LogTemplate):
    LOG_TEMPLATES = [
        "{timestamp} MessageID=82N18M63 From=mscott@dundermifflin.com To=aperkins@{domain_name} Subject='Encoded Subject' Size=12345 Verdict=Spam Action=quarantine Policy=Default",
        "{timestamp} MessageID=6C97GAJ8 From=dschrute@dundermifflin.com To=rswanson@{domain_name} Subject='Delete after read' Size=12345 Verdict=pass Action=allow Policy=Default",
        "{timestamp} MessageID=GY4347ND From=jhalpert@dundermifflin.com To=aludgate@{domain_name} Subject='MEMES' Size=12345 Verdict=pass Action=allow Policy=Default",
        "{timestamp} MessageID=4K21PQ56 From=pbeesly@dundermifflin.com To=tflenderson@{domain_name} Subject='Art Show Invitation' Size=67890 Verdict=pass Action=allow Policy=VIP",
        "{timestamp} MessageID=4J56ZT22 From=kkapoor@dundermifflin.com To=kleonard@{domain_name} Subject='New Saree Collection!' Size=23456 Verdict=pass Action=allow Policy=Marketing",
        "{timestamp} MessageID=9F34GGH7 From=creed@dundermifflin.com To=lknope@{domain_name} Subject='Mung Beans Harvest' Size=56789 Verdict=pass Action=allow Policy=Agriculture",
        "{timestamp} MessageID=2L65BBC9 From=rhoward@dundermifflin.com To=bbrendanawicz@{domain_name} Subject='Cat for Adoption' Size=12345 Verdict=pass Action=allow Policy=AnimalWelfare",
        "{timestamp} MessageID=5Q67YU88 From=mpalmer@dundermifflin.com To=jgergich@{domain_name} Subject='Accounting Best Practices' Size=98765 Verdict=pass Action=allow Policy=Finance",
    ]
# As you add more log templates, simply define them in this file.
