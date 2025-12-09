# cache_manager.py

import os
import json
from django.conf import settings
from pathlib import Path

class FacebookCacheManager:
    def __init__(self):
        self.cache_dir = Path(settings.BASE_DIR) / 'facebook_cache'
        self.cache_dir.mkdir(exist_ok=True)
    
    def get_user_cache_path(self, facebook_user):
        """Get the cache file path for a specific Facebook user."""
        safe_username = facebook_user.replace('@', '_at_').replace('.', '_dot_')
        return self.cache_dir / f'{safe_username}_cookies.json'
    
    def save_user_cookies(self, facebook_user, cookies):
        """Save cookies for a specific Facebook user."""
        cache_path = self.get_user_cache_path(facebook_user)
        with open(cache_path, 'w') as f:
            json.dump(cookies, f)
    
    def load_user_cookies(self, facebook_user):
        """Load cookies for a specific Facebook user."""
        cache_path = self.get_user_cache_path(facebook_user)
        try:
            with open(cache_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def clear_user_cache(self, facebook_user):
        """Clear cache for a specific Facebook user."""
        cache_path = self.get_user_cache_path(facebook_user)
        if cache_path.exists():
            cache_path.unlink()