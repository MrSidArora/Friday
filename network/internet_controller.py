"""
Friday AI - Internet Controller

This module handles safe and controlled access to the internet,
providing domain whitelisting and user confirmation.
"""

import os
import json
import aiohttp
import asyncio
import logging
from typing import Dict, Any, Optional, Callable, Union, Coroutine
from urllib.parse import urlparse

class InternetController:
    def __init__(self):
        """Initialize the Internet Controller with safety measures."""
        self.whitelist = {}
        self.whitelist_file = "data/whitelist.json"
        self.confirmation_callback = None
        self.session = None
        self.logger = logging.getLogger("internet_controller")
        self.require_confirmation_for_all = False
        
    async def initialize(self):
        """Initialize the controller and load the whitelist."""
        # Create session for HTTP requests
        self.session = aiohttp.ClientSession()
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.whitelist_file), exist_ok=True)
        
        # Load whitelist
        await self.load_whitelist()
        
        # Add default domains to whitelist if not present
        default_domains = [
            "openai.com",  # OpenAI API
            "wikipedia.org",  # Wikipedia
            "python.org",  # Python documentation
            "www.wikipedia.org",  # Wikipedia www subdomain
        ]
        
        for domain in default_domains:
            if domain not in self.whitelist:
                self.whitelist[domain] = {
                    "approved": True,
                    "reason": "Default whitelisted domain",
                    "timestamp": None
                }
        
        # Save updated whitelist
        await self.save_whitelist()
        
    async def close(self):
        """Close resources when shutting down."""
        if self.session:
            await self.session.close()
            
    def set_confirmation_callback(self, callback):
        """Set the callback for domain confirmation.
        
        Args:
            callback: Function to call for domain confirmation
                      Should take domain and reason as parameters
                      Should return dict with 'approved' key
        """
        self.confirmation_callback = callback
        
    async def _get_confirmation(self, domain, reason):
        """Get confirmation using the callback, handling both sync and async callbacks."""
        if self.confirmation_callback:
            result = self.confirmation_callback(domain, reason)
            # Check if the result is a coroutine
            if asyncio.iscoroutine(result):
                return await result
            return result
        # Default to auto-approval in case no callback is set
        return {"approved": True}
        
    def set_require_confirmation_for_all(self, require_confirmation):
        """Set whether all domains require confirmation, even whitelisted ones.
        
        Args:
            require_confirmation: True if all domains need confirmation
        """
        self.require_confirmation_for_all = require_confirmation
        
    async def load_whitelist(self):
        """Load domain whitelist from file."""
        try:
            if os.path.exists(self.whitelist_file):
                with open(self.whitelist_file, 'r') as f:
                    self.whitelist = json.load(f)
        except Exception as e:
            self.logger.error(f"Error loading whitelist: {str(e)}")
            self.whitelist = {}
            
    async def save_whitelist(self):
        """Save domain whitelist to file."""
        try:
            with open(self.whitelist_file, 'w') as f:
                json.dump(self.whitelist, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving whitelist: {str(e)}")
            
    def get_whitelist(self):
        """Get the current domain whitelist.
        
        Returns:
            Dict of whitelisted domains
        """
        return self.whitelist
        
    def remove_domain_from_whitelist(self, domain):
        """Remove a domain from the whitelist.
        
        Args:
            domain: Domain to remove
            
        Returns:
            Dict with success status
        """
        if domain in self.whitelist:
            del self.whitelist[domain]
            return {"success": True, "domain": domain}
        return {"success": False, "domain": domain, "error": "Domain not in whitelist"}
        
    async def add_domain_to_whitelist(self, domain, reason, auto_approve=False):
        """Add a domain to the whitelist.
        
        Args:
            domain: Domain to add
            reason: Reason for adding the domain
            auto_approve: Whether to auto-approve without confirmation
            
        Returns:
            Dict with success status
        """
        # Check if domain already whitelisted
        if domain in self.whitelist and self.whitelist[domain]["approved"]:
            return {"success": True, "domain": domain, "approved": True, "message": "Domain already in whitelist"}
            
        # Get confirmation if needed
        if not auto_approve and self.confirmation_callback:
            confirmation = await self._get_confirmation(domain, reason)
            approved = confirmation.get("approved", False)
        else:
            approved = True
            
        # Add to whitelist if approved
        if approved:
            self.whitelist[domain] = {
                "approved": True,
                "reason": reason,
                "timestamp": None  # Could use datetime.now().isoformat() if needed
            }
            await self.save_whitelist()
            return {"success": True, "domain": domain, "approved": approved}
        else:
            return {"success": False, "domain": domain, "approved": approved, "message": "Domain not approved"}
            
    async def request(self, url, method="GET", data=None, headers=None, reason=None, require_confirmation=True):
        """Make a web request with safety checks.
        
        Args:
            url: URL to request
            method: HTTP method (GET, POST, etc.)
            data: Request data for POST, etc.
            headers: Request headers
            reason: Reason for the request
            require_confirmation: Whether to require confirmation
            
        Returns:
            Dict with response data
        """
        if not self.session:
            return {"success": False, "error": "Session not initialized"}
            
        try:
            # Parse domain from URL
            parsed_url = urlparse(url)
            domain = parsed_url.netloc
            
            # Always check domain permission
            domain_allowed = await self._check_domain_permission(domain, reason or f"Request to {url}", require_confirmation)
            
            if not domain_allowed["allowed"]:
                return {"success": False, "error": "Domain not allowed", "domain": domain}
                
            # Make the request
            try:
                if method.upper() == "GET":
                    response = await self.session.get(url, headers=headers)
                elif method.upper() == "POST":
                    response = await self.session.post(url, data=data, headers=headers)
                elif method.upper() == "PUT":
                    response = await self.session.put(url, data=data, headers=headers)
                elif method.upper() == "DELETE":
                    response = await self.session.delete(url, headers=headers)
                else:
                    return {"success": False, "error": f"Unsupported method: {method}"}
                    
                # Get response data
                try:
                    content_type = response.headers.get('Content-Type', '')
                    if 'application/json' in content_type:
                        response_data = await response.json()
                    else:
                        response_data = await response.text()
                except Exception as e:
                    response_data = await response.text()
                    
                # Log the successful request
                self._log_request(domain, url, method, response.status, success=True)
                
                # Return response data
                return {
                    "success": True,
                    "status": response.status,
                    "content_type": content_type,
                    "data": response_data,
                    "headers": dict(response.headers)
                }
                
            except Exception as e:
                self._log_request(domain, url, method, None, success=False, error=str(e))
                return {"success": False, "error": str(e)}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
            
    async def _check_domain_permission(self, domain, reason, require_confirmation):
        """Check if domain is allowed and get confirmation if needed.
        
        Args:
            domain: Domain to check
            reason: Reason for the request
            require_confirmation: Whether to require confirmation
            
        Returns:
            Dict with allowed status
        """
        # Check if domain is whitelisted
        domain_in_whitelist = domain in self.whitelist and self.whitelist[domain]["approved"]
        
        # If domain is whitelisted and we don't require confirmation for all domains
        if domain_in_whitelist and not self.require_confirmation_for_all and not require_confirmation:
            return {"allowed": True, "domain": domain, "whitelisted": True}
            
        # Otherwise, get confirmation
        if self.confirmation_callback:
            confirmation = await self._get_confirmation(domain, reason)
            approved = confirmation.get("approved", False)
            
            # If approved, add to whitelist
            if approved and not domain_in_whitelist:
                await self.add_domain_to_whitelist(domain, reason, auto_approve=True)
                
            return {"allowed": approved, "domain": domain, "whitelisted": domain_in_whitelist}
        else:
            # No callback, use whitelist
            return {"allowed": domain_in_whitelist, "domain": domain, "whitelisted": domain_in_whitelist}
            
    def _log_request(self, domain, url, method, status, success, error=None):
        """Log a web request for auditing purposes.
        
        Args:
            domain: Domain requested
            url: Full URL
            method: HTTP method
            status: Response status
            success: Whether request succeeded
            error: Error message if failed
        """
        log_data = {
            "timestamp": None,  # Could use datetime.now().isoformat() if needed
            "domain": domain,
            "url": url,
            "method": method,
            "success": success
        }
        
        if status:
            log_data["status"] = status
            
        if error:
            log_data["error"] = error
            
        self.logger.info(json.dumps(log_data))