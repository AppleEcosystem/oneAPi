import aiosqlite
import json
import random
import string
from datetime import datetime
from typing import Optional, Dict, Any, List

class Database:
    """Database handler for the bot"""
    
    def __init__(self, db_path: str = "bot_database.db"):
        self.db_path = db_path
        self.connection: Optional[aiosqlite.Connection] = None
    
    async def init_db(self):
        """Initialize database connection and create tables"""
        self.connection = await aiosqlite.connect(self.db_path)
        await self._create_tables()
        await self._migrate_database()
    
    async def _create_tables(self):
        """Create necessary database tables"""
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                api_key TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS registrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                udid TEXT NOT NULL,
                certificate_id TEXT,
                plan TEXT NOT NULL,
                api_response TEXT,
                status TEXT DEFAULT 'active',
                enabled INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS certificates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                udid TEXT NOT NULL,
                certificate_id TEXT NOT NULL,
                certificate_data TEXT,
                fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS thumbnails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                p12_thumbnail_data TEXT,
                mobileprovision_thumbnail_data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS keys (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                key_code TEXT UNIQUE NOT NULL,
                plan TEXT NOT NULL,
                used INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        await self.connection.execute("""
            CREATE TABLE IF NOT EXISTS ipas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                original_filename TEXT NOT NULL,
                app_name TEXT NOT NULL,
                bundle_id TEXT NOT NULL,
                version TEXT NOT NULL,
                local_path TEXT NOT NULL,
                file_size INTEGER DEFAULT 0,
                ipa_filename TEXT,
                plist_filename TEXT,
                ipa_url TEXT,
                plist_url TEXT,
                install_url TEXT,
                signed_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        """)
        
        await self.connection.commit()
    
    async def _migrate_database(self):
        """Migrate existing database to add new columns"""
        try:
            # Check if enabled column exists in registrations
            cursor = await self.connection.execute("PRAGMA table_info(registrations)")
            columns = await cursor.fetchall()
            column_names = [column[1] for column in columns]
        
            if 'enabled' not in column_names:
                await self.connection.execute("""
                    ALTER TABLE registrations ADD COLUMN enabled INTEGER DEFAULT 1
                """)
                await self.connection.commit()
        
            # Handle keys table migration more carefully
            cursor = await self.connection.execute("PRAGMA table_info(keys)")
            columns = await cursor.fetchall()
            column_names = [column[1] for column in columns]
        
            # If keys table exists but doesn't have key_code, we need to recreate it
            if columns and 'key_code' not in column_names:
            
                # Create new keys table with proper structure
                await self.connection.execute("""
                    CREATE TABLE IF NOT EXISTS keys_new (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        key_code TEXT UNIQUE NOT NULL,
                        plan TEXT NOT NULL,
                        used INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        used_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users (user_id)
                    )
                """)
            
                # Copy existing data if any, generating key codes for existing entries
                cursor = await self.connection.execute("SELECT * FROM keys")
                existing_keys = await cursor.fetchall()
            
                for key_row in existing_keys:
                    # Generate a unique key code for existing entries
                    key_code = self.generate_key_code()
                    # Ensure uniqueness
                    while True:
                        check_cursor = await self.connection.execute("""
                            SELECT id FROM keys_new WHERE key_code = ?
                        """, (key_code,))
                        if not await check_cursor.fetchone():
                            break
                        key_code = self.generate_key_code()
                
                    # Insert into new table
                    await self.connection.execute("""
                        INSERT INTO keys_new (id, user_id, key_code, plan, used, created_at, used_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (key_row[0], key_row[1], key_code, key_row[2], key_row[3], key_row[4], key_row[5] if len(key_row) > 5 else None))
            
                # Drop old table and rename new one
                await self.connection.execute("DROP TABLE keys")
                await self.connection.execute("ALTER TABLE keys_new RENAME TO keys")
                await self.connection.commit()
        
            # Check if ipas table needs migration for nullable columns
            cursor = await self.connection.execute("PRAGMA table_info(ipas)")
            columns = await cursor.fetchall()
        
            if columns:
                # Check if we need to recreate ipas table to make columns nullable
                needs_recreation = False
                for column in columns:
                    column_name = column[1]
                    is_nullable = not column[3]  # column[3] is the NOT NULL flag
                
                    # Check if signing columns are NOT NULL (they should be nullable)
                    if column_name in ['ipa_filename', 'plist_filename', 'ipa_url', 'plist_url', 'install_url'] and not is_nullable:
                        needs_recreation = True
                        break
            
                if needs_recreation:
                
                    # Create new ipas table with proper structure
                    await self.connection.execute("""
                        CREATE TABLE IF NOT EXISTS ipas_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            user_id INTEGER,
                            original_filename TEXT NOT NULL,
                            app_name TEXT NOT NULL,
                            bundle_id TEXT NOT NULL,
                            version TEXT NOT NULL,
                            local_path TEXT NOT NULL,
                            file_size INTEGER DEFAULT 0,
                            ipa_filename TEXT,
                            plist_filename TEXT,
                            ipa_url TEXT,
                            plist_url TEXT,
                            install_url TEXT,
                            signed_at TIMESTAMP,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            FOREIGN KEY (user_id) REFERENCES users (user_id)
                        )
                    """)
                
                    # Copy existing data
                    cursor = await self.connection.execute("SELECT * FROM ipas")
                    existing_ipas = await cursor.fetchall()
                
                    for ipa_row in existing_ipas:
                        # Handle different column counts for backward compatibility
                        values = list(ipa_row)
                        # Ensure we have all columns, pad with None if necessary
                        while len(values) < 15:  # 15 columns in new table
                            values.append(None)
                    
                        await self.connection.execute("""
                            INSERT INTO ipas_new VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, values[:15])
                
                    # Drop old table and rename new one
                    await self.connection.execute("DROP TABLE ipas")
                    await self.connection.execute("ALTER TABLE ipas_new RENAME TO ipas")
                    await self.connection.commit()
        
            # Add missing columns if they don't exist
            cursor = await self.connection.execute("PRAGMA table_info(ipas)")
            columns = await cursor.fetchall()
            column_names = [column[1] for column in columns]
        
            if 'local_path' not in column_names:
                await self.connection.execute("""
                    ALTER TABLE ipas ADD COLUMN local_path TEXT
                """)
                await self.connection.commit()
        
            if 'file_size' not in column_names:
                await self.connection.execute("""
                    ALTER TABLE ipas ADD COLUMN file_size INTEGER DEFAULT 0
                """)
                await self.connection.commit()
        
            if 'signed_at' not in column_names:
                await self.connection.execute("""
                    ALTER TABLE ipas ADD COLUMN signed_at TIMESTAMP
                """)
                await self.connection.commit()
            
        except Exception as e:
            pass
    
    def generate_key_code(self) -> str:
        """Generate a random key code"""
        return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    
    async def save_user(self, user_id: int, username: str = None, api_key: str = None):
        """Save or update user information"""
        await self.connection.execute("""
            INSERT OR REPLACE INTO users (user_id, username, api_key, updated_at)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, api_key, datetime.now()))
        await self.connection.commit()
    
    async def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Get user information"""
        cursor = await self.connection.execute(
            "SELECT * FROM users WHERE user_id = ?", (user_id,)
        )
        row = await cursor.fetchone()
        if row:
            return {
                "user_id": row[0],
                "username": row[1], 
                "api_key": row[2],
                "created_at": row[3],
                "updated_at": row[4]
            }
        return None
    
    async def save_registration(self, user_id: int, udid: str, certificate_id: str, 
                              plan: str, api_response: Dict[str, Any], status: str = 'active'):
        """Save registration information"""
        await self.connection.execute("""
            INSERT INTO registrations (user_id, udid, certificate_id, plan, api_response, status, enabled)
            VALUES (?, ?, ?, ?, ?, ?, 1)
        """, (user_id, udid, certificate_id, plan, json.dumps(api_response), status))
        await self.connection.commit()
    
    async def get_user_registrations(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all registrations for a user"""
        cursor = await self.connection.execute("""
            SELECT * FROM registrations WHERE user_id = ? ORDER BY created_at DESC
        """, (user_id,))
        rows = await cursor.fetchall()
        
        registrations = []
        for row in rows:
            # Handle both old and new database structures
            registration = {
                "id": row[0],
                "user_id": row[1],
                "udid": row[2],
                "certificate_id": row[3],
                "plan": row[4],
                "api_response": json.loads(row[5]) if row[5] else {},
                "status": row[6] if len(row) > 6 else 'active',
                "enabled": bool(row[7]) if len(row) > 7 else True,
                "created_at": row[8] if len(row) > 8 else row[7] if len(row) > 7 else datetime.now().isoformat()
            }
            registrations.append(registration)
        return registrations
    
    async def get_processing_registrations(self) -> List[Dict[str, Any]]:
        """Get all registrations with processing status"""
        cursor = await self.connection.execute("""
            SELECT r.*, u.api_key FROM registrations r 
            JOIN users u ON r.user_id = u.user_id 
            WHERE r.status = 'processing'
        """)
        rows = await cursor.fetchall()
        
        registrations = []
        for row in rows:
            # Handle both old and new database structures
            registration = {
                "id": row[0],
                "user_id": row[1],
                "udid": row[2],
                "certificate_id": row[3],
                "plan": row[4],
                "api_response": json.loads(row[5]) if row[5] else {},
                "status": row[6] if len(row) > 6 else 'active',
                "enabled": bool(row[7]) if len(row) > 7 else True,
                "created_at": row[8] if len(row) > 8 else row[7] if len(row) > 7 else datetime.now().isoformat(),
                "api_key": row[-1]  # API key is always the last column
            }
            registrations.append(registration)
        return registrations
    
    async def update_registration_status(self, udid: str, status: str):
        """Update registration status"""
        await self.connection.execute("""
            UPDATE registrations SET status = ? WHERE udid = ?
        """, (status, udid))
        await self.connection.commit()
    
    async def toggle_registration_enabled(self, user_id: int, udid: str) -> bool:
        """Toggle registration enabled status and return new status"""
        cursor = await self.connection.execute("""
            SELECT enabled FROM registrations WHERE user_id = ? AND udid = ?
        """, (user_id, udid))
        row = await cursor.fetchone()
        
        if row:
            current_enabled = row[0] if row[0] is not None else 1
            new_enabled = 0 if current_enabled else 1
            await self.connection.execute("""
                UPDATE registrations SET enabled = ? WHERE user_id = ? AND udid = ?
            """, (new_enabled, user_id, udid))
            await self.connection.commit()
            return bool(new_enabled)
        return False
    
    async def get_registration_by_udid(self, user_id: int, udid: str) -> Optional[Dict[str, Any]]:
        """Get registration by UDID"""
        cursor = await self.connection.execute("""
            SELECT * FROM registrations WHERE user_id = ? AND udid = ?
        """, (user_id, udid))
        row = await cursor.fetchone()
        
        if row:
            return {
                "id": row[0],
                "user_id": row[1],
                "udid": row[2],
                "certificate_id": row[3],
                "plan": row[4],
                "api_response": json.loads(row[5]) if row[5] else {},
                "status": row[6] if len(row) > 6 else 'active',
                "enabled": bool(row[7]) if len(row) > 7 else True,
                "created_at": row[8] if len(row) > 8 else row[7] if len(row) > 7 else datetime.now().isoformat()
            }
        return None
    
    async def save_certificate(self, user_id: int, udid: str, certificate_id: str, 
                             certificate_data: Dict[str, Any]):
        """Save certificate information"""
        await self.connection.execute("""
            INSERT OR REPLACE INTO certificates (user_id, udid, certificate_id, certificate_data, fetched_at)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, udid, certificate_id, json.dumps(certificate_data), datetime.now()))
        await self.connection.commit()
    
    async def get_certificate(self, user_id: int, udid: str = None, 
                            certificate_id: str = None) -> Optional[Dict[str, Any]]:
        """Get certificate information"""
        query = "SELECT * FROM certificates WHERE user_id = ?"
        params = [user_id]
        
        if udid:
            query += " AND udid = ?"
            params.append(udid)
        
        if certificate_id:
            query += " AND certificate_id = ?"
            params.append(certificate_id)
        
        query += " ORDER BY fetched_at DESC LIMIT 1"
        
        cursor = await self.connection.execute(query, params)
        row = await cursor.fetchone()
        
        if row:
            return {
                "id": row[0],
                "user_id": row[1],
                "udid": row[2],
                "certificate_id": row[3],
                "certificate_data": json.loads(row[4]) if row[4] else {},
                "fetched_at": row[5]
            }
        return None
    
    async def save_thumbnails(self, user_id: int, p12_thumbnail_data: str = None, mobileprovision_thumbnail_data: str = None):
        """Save thumbnail base64 data for user"""
        # Check if user already has thumbnails
        cursor = await self.connection.execute("""
            SELECT * FROM thumbnails WHERE user_id = ?
        """, (user_id,))
        existing = await cursor.fetchone()
        
        if existing:
            # Update existing thumbnails
            if p12_thumbnail_data:
                await self.connection.execute("""
                    UPDATE thumbnails SET p12_thumbnail_data = ?, updated_at = ? WHERE user_id = ?
                """, (p12_thumbnail_data, datetime.now(), user_id))
            if mobileprovision_thumbnail_data:
                await self.connection.execute("""
                    UPDATE thumbnails SET mobileprovision_thumbnail_data = ?, updated_at = ? WHERE user_id = ?
                """, (mobileprovision_thumbnail_data, datetime.now(), user_id))
        else:
            # Insert new thumbnails
            await self.connection.execute("""
                INSERT INTO thumbnails (user_id, p12_thumbnail_data, mobileprovision_thumbnail_data)
                VALUES (?, ?, ?)
            """, (user_id, p12_thumbnail_data, mobileprovision_thumbnail_data))
        
        await self.connection.commit()

    async def get_thumbnails(self, user_id: int) -> Optional[Dict[str, str]]:
        """Get thumbnail base64 data for user"""
        cursor = await self.connection.execute("""
            SELECT p12_thumbnail_data, mobileprovision_thumbnail_data FROM thumbnails WHERE user_id = ?
        """, (user_id,))
        row = await cursor.fetchone()
        
        if row:
            return {
                "p12_thumbnail": row[0],
                "mobileprovision_thumbnail": row[1]
            }
        return None

    async def get_global_thumbnails(self) -> Optional[Dict[str, str]]:
        """Get the most recent thumbnails from any user (global thumbnails)"""
        cursor = await self.connection.execute("""
            SELECT p12_thumbnail_data, mobileprovision_thumbnail_data 
            FROM thumbnails 
            WHERE p12_thumbnail_data IS NOT NULL OR mobileprovision_thumbnail_data IS NOT NULL
            ORDER BY updated_at DESC 
            LIMIT 1
        """)
        row = await cursor.fetchone()
        
        if row:
            return {
                "p12_thumbnail": row[0],
                "mobileprovision_thumbnail": row[1]
            }
        return None
    
    async def create_keys(self, user_id: int, plan: str, quantity: int) -> List[str]:
        """Create multiple keys for a user and return the key codes"""
        key_codes = []
        for _ in range(quantity):
            # Generate unique key code
            while True:
                key_code = self.generate_key_code()
                # Check if key code already exists
                cursor = await self.connection.execute("""
                    SELECT id FROM keys WHERE key_code = ?
                """, (key_code,))
                if not await cursor.fetchone():
                    break
            
            await self.connection.execute("""
                INSERT INTO keys (user_id, key_code, plan) VALUES (?, ?, ?)
            """, (user_id, key_code, plan))
            key_codes.append(key_code)
        
        await self.connection.commit()
        return key_codes
    
    async def get_user_keys(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all keys for a user"""
        cursor = await self.connection.execute("""
            SELECT * FROM keys WHERE user_id = ? ORDER BY created_at DESC
        """, (user_id,))
        rows = await cursor.fetchall()
        
        keys = []
        for row in rows:
            keys.append({
                "id": row[0],
                "user_id": row[1],
                "key_code": row[2],
                "plan": row[3],
                "used": bool(row[4]),
                "created_at": row[5],
                "used_at": row[6]
            })
        return keys
    
    async def get_key_by_code(self, key_code: str) -> Optional[Dict[str, Any]]:
        """Get key by key code"""
        cursor = await self.connection.execute("""
            SELECT * FROM keys WHERE key_code = ?
        """, (key_code,))
        row = await cursor.fetchone()
        
        if row:
            return {
                "id": row[0],
                "user_id": row[1],
                "key_code": row[2],
                "plan": row[3],
                "used": bool(row[4]),
                "created_at": row[5],
                "used_at": row[6]
            }
        return None
    
    async def get_unused_key(self, user_id: int, plan: str = None) -> Optional[Dict[str, Any]]:
        """Get an unused key for a user"""
        query = "SELECT * FROM keys WHERE user_id = ? AND used = 0"
        params = [user_id]
        
        if plan:
            query += " AND plan = ?"
            params.append(plan)
        
        query += " ORDER BY created_at ASC LIMIT 1"
        
        cursor = await self.connection.execute(query, params)
        row = await cursor.fetchone()
        
        if row:
            return {
                "id": row[0],
                "user_id": row[1],
                "key_code": row[2],
                "plan": row[3],
                "used": bool(row[4]),
                "created_at": row[5],
                "used_at": row[6]
            }
        return None
    
    async def use_key(self, key_code: str):
        """Mark a key as used by key code"""
        await self.connection.execute("""
            UPDATE keys SET used = 1, used_at = ? WHERE key_code = ?
        """, (datetime.now(), key_code))
        await self.connection.commit()
    
    async def get_key_stats(self, user_id: int) -> Dict[str, int]:
        """Get key statistics for a user"""
        cursor = await self.connection.execute("""
            SELECT plan, COUNT(*) as total, SUM(used) as used_count 
            FROM keys WHERE user_id = ? GROUP BY plan
        """, (user_id,))
        rows = await cursor.fetchall()
        
        stats = {}
        for row in rows:
            plan = row[0]
            total = row[1]
            used = row[2] or 0
            unused = total - used
            stats[plan] = {"total": total, "used": used, "unused": unused}
        
        return stats
    
    async def save_ipa(self, user_id: int, original_filename: str, local_path: str, file_size: int) -> int:
        """Save IPA information with local path and return IPA ID"""
        cursor = await self.connection.execute("""
            INSERT INTO ipas (user_id, original_filename, local_path, file_size, app_name, bundle_id, version)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (user_id, original_filename, local_path, file_size, "Unknown", "com.unknown.app", "1.0"))
        await self.connection.commit()
        return cursor.lastrowid

    async def update_ipa_signed_info(self, ipa_id: int, ipa_filename: str, plist_filename: str,
                                   ipa_url: str, plist_url: str, install_url: str):
        """Update IPA with signed file information"""
        await self.connection.execute("""
            UPDATE ipas SET 
                ipa_filename = ?, 
                plist_filename = ?, 
                ipa_url = ?, 
                plist_url = ?, 
                install_url = ?,
                signed_at = ?
            WHERE id = ?
        """, (ipa_filename, plist_filename, ipa_url, plist_url, install_url, datetime.now(), ipa_id))
        await self.connection.commit()

    async def update_ipa_metadata(self, ipa_id: int, app_name: str, bundle_id: str, version: str):
        """Update IPA metadata with information from zsign"""
        await self.connection.execute("""
            UPDATE ipas SET 
                app_name = ?, 
                bundle_id = ?, 
                version = ?
            WHERE id = ?
        """, (app_name, bundle_id, version, ipa_id))
        await self.connection.commit()

    async def get_user_ipas(self, user_id: int) -> List[Dict[str, Any]]:
        """Get all IPAs for a user"""
        cursor = await self.connection.execute("""
            SELECT * FROM ipas WHERE user_id = ? ORDER BY created_at DESC
        """, (user_id,))
        rows = await cursor.fetchall()
        
        ipas = []
        for row in rows:
            ipas.append({
                "id": row[0],
                "user_id": row[1],
                "original_filename": row[2],
                "app_name": row[3],
                "bundle_id": row[4],
                "version": row[5],
                "local_path": row[6],
                "file_size": row[7],
                "ipa_filename": row[8],
                "plist_filename": row[9],
                "ipa_url": row[10],
                "plist_url": row[11],
                "install_url": row[12],
                "signed_at": row[13],
                "created_at": row[14]
            })
        return ipas

    async def get_ipa_by_id(self, ipa_id: int) -> Optional[Dict[str, Any]]:
        """Get IPA by ID"""
        cursor = await self.connection.execute("""
            SELECT * FROM ipas WHERE id = ?
        """, (ipa_id,))
        row = await cursor.fetchone()
        
        if row:
            return {
                "id": row[0],
                "user_id": row[1],
                "original_filename": row[2],
                "app_name": row[3],
                "bundle_id": row[4],
                "version": row[5],
                "local_path": row[6],
                "file_size": row[7],
                "ipa_filename": row[8],
                "plist_filename": row[9],
                "ipa_url": row[10],
                "plist_url": row[11],
                "install_url": row[12],
                "signed_at": row[13],
                "created_at": row[14]
            }
        return None

    async def delete_ipa(self, ipa_id: int, user_id: int) -> Optional[Dict[str, str]]:
        """Delete IPA and return filenames for cleanup"""
        cursor = await self.connection.execute("""
            SELECT local_path, ipa_filename, plist_filename FROM ipas WHERE id = ? AND user_id = ?
        """, (ipa_id, user_id))
        row = await cursor.fetchone()
        
        if row:
            await self.connection.execute("""
                DELETE FROM ipas WHERE id = ? AND user_id = ?
            """, (ipa_id, user_id))
            await self.connection.commit()
            return {
                "local_path": row[0],
                "ipa_filename": row[1],
                "plist_filename": row[2]
            }
        return None

    async def get_all_ipas(self) -> List[Dict[str, Any]]:
        """Get all IPAs for signing when certificate is downloaded"""
        cursor = await self.connection.execute("""
            SELECT * FROM ipas ORDER BY created_at DESC
        """, ())
        rows = await cursor.fetchall()
        
        ipas = []
        for row in rows:
            ipas.append({
                "id": row[0],
                "user_id": row[1],
                "original_filename": row[2],
                "app_name": row[3],
                "bundle_id": row[4],
                "version": row[5],
                "local_path": row[6],
                "file_size": row[7],
                "ipa_filename": row[8],
                "plist_filename": row[9],
                "ipa_url": row[10],
                "plist_url": row[11],
                "install_url": row[12],
                "signed_at": row[13],
                "created_at": row[14]
            })
        return ipas

    async def get_unsigned_ipas(self, user_id: int = None) -> List[Dict[str, Any]]:
        """Get all unsigned IPAs (for signing when certificate is available)"""
        query = "SELECT * FROM ipas WHERE install_url IS NULL OR install_url = ''"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY created_at DESC"
        
        cursor = await self.connection.execute(query, params)
        rows = await cursor.fetchall()
        
        ipas = []
        for row in rows:
            ipas.append({
                "id": row[0],
                "user_id": row[1],
                "original_filename": row[2],
                "app_name": row[3],
                "bundle_id": row[4],
                "version": row[5],
                "local_path": row[6],
                "file_size": row[7],
                "ipa_filename": row[8],
                "plist_filename": row[9],
                "ipa_url": row[10],
                "plist_url": row[11],
                "install_url": row[12],
                "signed_at": row[13],
                "created_at": row[14]
            })
        return ipas
    
    async def get_signed_ipas(self, user_id: int = None) -> List[Dict[str, Any]]:
        """Get all signed IPAs (for showing install buttons)"""
        query = "SELECT * FROM ipas WHERE install_url IS NOT NULL AND install_url != ''"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        query += " ORDER BY signed_at DESC"
        
        cursor = await self.connection.execute(query, params)
        rows = await cursor.fetchall()
        
        ipas = []
        for row in rows:
            ipas.append({
                "id": row[0],
                "user_id": row[1],
                "original_filename": row[2],
                "app_name": row[3],
                "bundle_id": row[4],
                "version": row[5],
                "local_path": row[6],
                "file_size": row[7],
                "ipa_filename": row[8],
                "plist_filename": row[9],
                "ipa_url": row[10],
                "plist_url": row[11],
                "install_url": row[12],
                "signed_at": row[13],
                "created_at": row[14]
            })
        return ipas
    
    async def close(self):
        """Close database connection"""
        if self.connection:
            await self.connection.close()
