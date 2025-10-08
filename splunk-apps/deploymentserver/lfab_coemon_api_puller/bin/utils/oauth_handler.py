import requests
import time
import logging
from datetime import datetime, timedelta

class OAuthHandler:
    def __init__(self, client_id, client_secret, token_url, verify, scope=None):
        """
        Initialize the OAuth Handler.
        
        Args:
            client_id: OAuth client ID
            client_secret: OAuth client secret
            token_url: URL to get the token
            scope: OAuth scope (optional)
            verify: Verify SSL certificate
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_url = token_url
        self.verify = verify
        self.scope = scope
        self.token = None
        self.token_expiry = None
        self.token_type = "bearer"  # Default token type
        
    def get_token(self):
        """
        Get a valid OAuth token, refreshing if necessary.
        
        Returns:
            str: The valid access token
        """
        current_time = datetime.now()
        
        # If we don't have a token or it's expired or about to expire in the next 4 hours
        if (self.token is None or 
            self.token_expiry is None or 
            current_time + timedelta(hours=4) >= self.token_expiry):
            self._request_new_token()
            
        return self.token
    
    def _request_new_token(self):
        """Request a new token from the OAuth server."""
        try:
            data = {
                'grant_type': 'client_credentials',
                'client_id': self.client_id,
                'client_secret': self.client_secret
            }
            
            #if self.scope:
            #    data['scope'] = self.scope
                
            logging.info(f"Requesting new OAuth token from {self.token_url}")
            response = requests.post(
                self.token_url,
                data=data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                verify=self.verify
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.token = token_data.get('access_token')
                
                # Calculate token expiry time
                expires_in = token_data.get('expires_in', 3600)  # Default to 1 hour
                self.token_expiry = datetime.now() + timedelta(seconds=expires_in)
                
                # Get token type if available
                self.token_type = token_data.get('token_type', 'bearer').lower()
                
                logging.info(f"OAuth token obtained successfully, expires in {expires_in} seconds")
            else:
                logging.error(f"Failed to get OAuth token. Status: {response.status_code}, Response: {response.text}")
                self.token = None
                self.token_expiry = None
                
        except Exception as e:
            logging.error(f"Error getting OAuth token: {str(e)}")
            self.token = None
            self.token_expiry = None
