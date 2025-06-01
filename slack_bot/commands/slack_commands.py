# slack_commands.py

from slack_bolt.async_app import AsyncApp

def register_commands(app: AsyncApp):
    # Import command registration functions from individual modules
    from .dns_history import register_dns_history_command
    from .fingerprint import register_fingerprint_command
    from .subdomains import register_subdomains_command
    from .supplychain import register_supplychain_command
    from .track import register_track_command
    from .mx_security import register_mx_security_command
    from .dga import register_dga_command  
    from .dnscount import register_dnscount_command
    from .timeline import register_timeline_command
    from .screenshot import register_screenshot_command

    # Register each command
    register_dns_history_command(app)
    register_fingerprint_command(app)
    register_subdomains_command(app)
    register_supplychain_command(app)
    register_track_command(app)
    register_mx_security_command(app)
    register_dga_command(app) 
    register_timeline_command(app) 
    register_dnscount_command(app)
    register_screenshot_command(app)
