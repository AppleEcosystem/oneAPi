import os
from dataclasses import dataclass

@dataclass
class Config:
    """Configuration class for the bot"""
    BOT_TOKEN: str = "bot_token"
    API_BASE_URL: str = "https://api.bot1.org"
    DATABASE_PATH: str = "database.db"
    ADMIN_USER_ID: int = 7084874895
    
    B2 Storage Configuration
    B2_ENDPOINT_URL: str = "https://s3.eu-central-003.backblazeb2.com"
    B2_ACCESS_KEY_ID: str = "00317ebc9a22aa50sda324x000003"
    B2_SECRET_ACCESS_KEY: str = "K003Cl2dSBNN7xiqIYbbgLfdas43435348s"
    B2_REGION_NAME: str = "eu-central-0033333"
    B2_BUCKET_NAME: str = "tempdays"
    B2_PUBLIC_URL_BASE: str = "https://tempdays.s3.eu-central-003.backblazeb2.com"
    
    def __init__(self):
        # Keep the hardcoded values, but allow environment override if needed
        self.BOT_TOKEN = os.getenv("BOT_TOKEN", self.BOT_TOKEN)
        self.API_BASE_URL = os.getenv("API_BASE_URL", self.API_BASE_URL)
        self.DATABASE_PATH = os.getenv("DATABASE_PATH", self.DATABASE_PATH)
        
        # B2 Storage overrides
        self.B2_ENDPOINT_URL = os.getenv("B2_ENDPOINT_URL", self.B2_ENDPOINT_URL)
        self.B2_ACCESS_KEY_ID = os.getenv("B2_ACCESS_KEY_ID", self.B2_ACCESS_KEY_ID)
        self.B2_SECRET_ACCESS_KEY = os.getenv("B2_SECRET_ACCESS_KEY", self.B2_SECRET_ACCESS_KEY)
        self.B2_REGION_NAME = os.getenv("B2_REGION_NAME", self.B2_REGION_NAME)
        self.B2_BUCKET_NAME = os.getenv("B2_BUCKET_NAME", self.B2_BUCKET_NAME)
        self.B2_PUBLIC_URL_BASE = os.getenv("B2_PUBLIC_URL_BASE", self.B2_PUBLIC_URL_BASE)
        
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is required")

def get_plan_name(plan_id: str) -> str:
    """Get localized plan name"""
    from languages import lang_manager
    return lang_manager.get_text(f"plan_{plan_id}", default=plan_id)

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id == 7084874895

PLANS = {
    "super0": "plan_super0",
    "super40": "plan_super40", 
    "super90": "plan_super90",
    "super180": "plan_super180",
    "super360": "plan_super360",
    "super_ipad360": "plan_super_ipad360",
    "ordinary0": "plan_ordinary0",
    "ordinary40": "plan_ordinary40"
}
