import asyncio
from datetime import datetime
from api_client import OneBotAPIClient
from database import Database
from config import Config

class BackgroundTaskManager:
    """Manages background tasks for the bot"""
    
    def __init__(self, db: Database, config: Config):
        self.db = db
        self.config = config
        self.running = False
    
    async def start(self):
        """Start background tasks"""
        self.running = True
        
        # Start the processing checker task
        asyncio.create_task(self.check_processing_certificates())
    
    async def stop(self):
        """Stop background tasks"""
        self.running = False
    
    def determine_status(self, api_response: dict) -> str:
        """Determine status based on API response"""
        # Check if mobileprovision exists and is not empty
        mobileprovision = api_response.get('mobileprovision')
        p12 = api_response.get('p12')
        
        # If both p12 and mobileprovision exist and are not empty, it's active
        if p12 and mobileprovision and mobileprovision.strip():
            return 'active'
        # If only p12 exists or mobileprovision is empty, it's processing
        elif p12 and (not mobileprovision or not mobileprovision.strip()):
            return 'processing'
        # Default to processing for safety
        else:
            return 'processing'
    
    async def check_processing_certificates(self):
        """Check processing certificates every hour"""
        while self.running:
            try:
                # Get all registrations with processing status
                processing_regs = await self.db.get_processing_registrations()
                
                for reg in processing_regs:
                    try:
                        api_client = OneBotAPIClient(self.config.API_BASE_URL)
                        certificates = await api_client.get_certificate(
                            reg['api_key'], 
                            udid=reg['udid']
                        )
                        await api_client.close()
                        
                        if certificates:
                            cert_data = certificates[0]
                            
                            # Check current status
                            current_status = self.determine_status(cert_data)
                            
                            # If status changed from processing to active
                            if current_status == 'active' and reg['status'] == 'processing':
                                # Update status to active
                                await self.db.update_registration_status(reg['udid'], 'active')
                                
                                # Update certificate data
                                await self.db.save_certificate(
                                    reg['user_id'],
                                    reg['udid'],
                                    cert_data.get("id", ""),
                                    cert_data
                                )
                    
                    except Exception as e:
                        continue
                
            except Exception as e:
                pass
            
            # Wait for 1 hour (3600 seconds)
            await asyncio.sleep(3600)
