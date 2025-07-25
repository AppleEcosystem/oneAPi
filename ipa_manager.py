import os
import subprocess
import tempfile
import uuid
import shutil
import base64
import re
from typing import Dict, Any, Optional
from r2_storage import R2Storage

class IPAManager:
    """Manages IPA files, signing, and plist generation"""
    
    def __init__(self):
        self.r2 = R2Storage()
        self.local_ipa_dir = "local_ipas"  # Local directory for original IPAs
        self.ensure_local_directory()
    
    def ensure_local_directory(self):
        """Ensure local IPA directory exists"""
        if not os.path.exists(self.local_ipa_dir):
            os.makedirs(self.local_ipa_dir)
    
    async def save_ipa_locally(self, ipa_data: bytes, filename: str) -> str:
        """Save IPA file locally and return the local path"""
        try:
            # Generate unique filename to avoid conflicts
            unique_filename = f"{uuid.uuid4().hex}_{filename}"
            local_path = os.path.join(self.local_ipa_dir, unique_filename)
            
            with open(local_path, 'wb') as f:
                f.write(ipa_data)
            
            return local_path
            
        except Exception as e:
            raise
    
    def validate_certificate_files(self, p12_path: str, prov_path: str) -> bool:
        """Validate P12 and mobileprovision files"""
        try:
            # Check if files exist
            if not os.path.exists(p12_path):
                return False
            
            if not os.path.exists(prov_path):
                return False
            
            # Check file sizes
            p12_size = os.path.getsize(p12_path)
            prov_size = os.path.getsize(prov_path)
            
            if p12_size == 0:
                return False
            
            if prov_size == 0:
                return False
            
            # Try to validate P12 file
            try:
                p12_check = subprocess.run([
                    'openssl', 'pkcs12', '-info', '-in', p12_path, 
                    '-passin', 'pass:1', '-noout'
                ], capture_output=True, text=True)
                
                if p12_check.returncode == 0:
                    pass
                else:
                    # Don't return False here as some P12 files might still work
                    pass
            except Exception as e:
                pass
            
            # Try to validate mobileprovision file
            try:
                # Check if it's a valid plist/XML
                prov_check = subprocess.run([
                    'security', 'cms', '-D', '-i', prov_path
                ], capture_output=True, text=True)
                
                if prov_check.returncode == 0:
                    # Log some info about the provisioning profile
                    if 'TeamName' in prov_check.stdout:
                        pass
                    if 'UUID' in prov_check.stdout:
                        pass
                else:
                    # Try alternative validation
                    try:
                        with open(prov_path, 'rb') as f:
                            content = f.read()
                        
                        # Check if it starts with typical mobileprovision markers
                        if b'<?xml' in content or b'<plist' in content:
                            pass
                        else:
                            return False
                    except Exception as e:
                        return False
            except Exception as e:
                pass
            
            return True
            
        except Exception as e:
            return False
    
    def parse_zsign_output(self, zsign_output: str) -> Dict[str, str]:
        """Parse zsign output to extract app information"""
        info = {
            'app_name': 'Unknown',
            'bundle_id': 'com.unknown.app',
            'version': '1.0'
        }
        
        try:
            # Extract AppName
            app_name_match = re.search(r'>>> AppName:\s+(.+)', zsign_output)
            if app_name_match:
                info['app_name'] = app_name_match.group(1).strip()
            
            # Extract BundleId
            bundle_id_match = re.search(r'>>> BundleId:\s+(.+)', zsign_output)
            if bundle_id_match:
                info['bundle_id'] = bundle_id_match.group(1).strip()
            
            # Extract Version
            version_match = re.search(r'>>> Version:\s+(.+)', zsign_output)
            if version_match:
                info['version'] = version_match.group(1).strip()
            
        except Exception as e:
            pass
        
        return info
    
    async def sign_ipa_from_local(self, local_ipa_path: str, p12_data: bytes, mobileprovision_data: bytes, 
                                 ipa_name: str, bundle_id: str, version: str, title: str) -> Optional[Dict[str, str]]:
        """Sign IPA file from local storage using zsign and upload signed version to B2"""
        temp_dir = None
        try:
            # Check if local IPA file exists
            if not os.path.exists(local_ipa_path):
                return None
            
            # Validate input data
            if not p12_data or len(p12_data) == 0:
                return None
            
            if not mobileprovision_data or len(mobileprovision_data) == 0:
                return None
            
            # Create temporary directory for signing process
            temp_dir = tempfile.mkdtemp()
            
            # Write certificate files to temp directory
            p12_path = os.path.join(temp_dir, "dev.p12")
            prov_path = os.path.join(temp_dir, "dev.mobileprovision")
            output_path = os.path.join(temp_dir, "output.ipa")
            
            # Write P12 file
            try:
                with open(p12_path, 'wb') as f:
                    f.write(p12_data)
            except Exception as e:
                return None
            
            # Write mobileprovision file
            try:
                with open(prov_path, 'wb') as f:
                    f.write(mobileprovision_data)
            except Exception as e:
                return None
            
            # Validate certificate files
            if not self.validate_certificate_files(p12_path, prov_path):
                return None
            
            # Check if zsign is available
            zsign_check = subprocess.run(['which', 'zsign'], capture_output=True, text=True)
            if zsign_check.returncode != 0:
                return None
            
            zsign_path = zsign_check.stdout.strip()
            
            abs_ipa_path = os.path.abspath(local_ipa_path)

            # Run zsign command with local IPA file
            cmd = [
                'zsign',
                '-k', p12_path,
                '-p', '1',  # Password is always 1
                '-m', prov_path,
                '-o', output_path,
                '-f',  # Force sign without cache
                '-d',  # Generate debug output
                abs_ipa_path  # Use absolute path to local IPA file
            ]
            
            # Run with more detailed output
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=temp_dir)
            
            if result.returncode != 0:
                # List files in temp directory for debugging
                try:
                    temp_files = os.listdir(temp_dir)
                    
                    # Show file sizes
                    for file in temp_files:
                        file_path = os.path.join(temp_dir, file)
                        if os.path.isfile(file_path):
                            size = os.path.getsize(file_path)
                    
                    # Check if debug folder was created
                    debug_folder = os.path.join(temp_dir, '.zsign_debug')
                    if os.path.exists(debug_folder):
                        debug_files = os.listdir(debug_folder)
                        
                        # Show debug file contents if they exist
                        for debug_file in debug_files:
                            debug_path = os.path.join(debug_folder, debug_file)
                            if os.path.isfile(debug_path) and debug_file.endswith('.txt'):
                                try:
                                    with open(debug_path, 'r') as f:
                                        debug_content = f.read()
                                except Exception as e:
                                    pass
                    
                except Exception as e:
                    pass
                
                return None
            
            # Parse zsign output to get actual app information
            app_info = self.parse_zsign_output(result.stdout)
            
            # Check if output file was created
            if not os.path.exists(output_path):
                # List all files in temp directory
                try:
                    all_files = []
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            all_files.append(os.path.join(root, file))
                except Exception as e:
                    pass
                return None
            
            # Read signed IPA
            with open(output_path, 'rb') as f:
                signed_ipa_data = f.read()
            
            # Generate unique filenames for B2 storage
            ipa_filename = f"{uuid.uuid4().hex}.ipa"
            plist_filename = f"{uuid.uuid4().hex}.plist"
            
            # Upload signed IPA to B2
            ipa_uploaded = await self.r2.upload_file(
                signed_ipa_data, 
                ipa_filename, 
                "application/octet-stream"
            )
            
            if not ipa_uploaded:
                return None
            
            # Generate and upload plist using parsed information
            plist_content = self.generate_plist(
                ipa_filename, 
                app_info['bundle_id'], 
                app_info['version'], 
                app_info['app_name']
            )
            
            plist_uploaded = await self.r2.upload_file(
                plist_content.encode('utf-8'),
                plist_filename,
                "application/xml"
            )
            
            if not plist_uploaded:
                # Clean up IPA if plist upload failed
                await self.r2.delete_file(ipa_filename)
                return None
            
            return {
                "ipa_filename": ipa_filename,
                "plist_filename": plist_filename,
                "ipa_url": self.r2.get_public_url(ipa_filename),
                "plist_url": self.r2.get_public_url(plist_filename),
                "install_url": f"itms-services://?action=download-manifest&url={self.r2.get_public_url(plist_filename)}",
                "app_info": app_info  # Include parsed app info
            }
            
        except Exception as e:
            return None
        finally:
            # Clean up temp directory
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                except Exception as e:
                    pass
    
    def generate_plist(self, ipa_filename: str, bundle_id: str, version: str, title: str) -> str:
        """Generate plist file for IPA installation"""
        ipa_url = self.r2.get_public_url(ipa_filename)
        
        # Use a default icon URL
        icon_url = "https://tempdays.s3.eu-central-003.backblazeb2.com/default-app-icon.png"
        
        plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>items</key>
    <array>
      <dict>
        <key>assets</key>
        <array>
          <dict>
            <key>kind</key>
            <string>software-package</string>
            <key>url</key>
            <string><![CDATA[{ipa_url}]]></string>
          </dict>
          <dict>
            <key>kind</key>
            <string>full-size-image</string>
            <key>url</key>
            <string><![CDATA[{icon_url}]]></string>
          </dict>
          <dict>
            <key>kind</key>
            <string>display-image</string>
            <key>url</key>
            <string><![CDATA[{icon_url}]]></string>
          </dict>
        </array>
        <key>metadata</key>
        <dict>
          <key>bundle-identifier</key>
          <string><![CDATA[{bundle_id}]]></string>
          <key>bundle-version</key>
          <string>{version}</string>
          <key>kind</key>
          <string>software</string>
          <key>title</key>
          <string><![CDATA[{title}]]></string>
        </dict>
      </dict>
    </array>
  </dict>
</plist>'''
        return plist_content
    
    async def delete_ipa_files(self, ipa_filename: str, plist_filename: str) -> bool:
        """Delete signed IPA and plist files from B2 (local files remain)"""
        ipa_deleted = await self.r2.delete_file(ipa_filename)
        plist_deleted = await self.r2.delete_file(plist_filename)
        return ipa_deleted and plist_deleted
    
    def delete_local_ipa(self, local_path: str) -> bool:
        """Delete local IPA file"""
        try:
            if os.path.exists(local_path):
                os.remove(local_path)
                return True
            return False
        except Exception as e:
            return False
    
    def get_local_ipa_size(self, local_path: str) -> int:
        """Get size of local IPA file in bytes"""
        try:
            if os.path.exists(local_path):
                return os.path.getsize(local_path)
            return 0
        except Exception as e:
            return 0
    
    async def sign_all_user_ipas(self, user_ipas: list, p12_data: bytes, mobileprovision_data: bytes, db) -> int:
        """Sign all IPAs for a user and update database"""
        signed_count = 0
        
        for ipa in user_ipas:
            # Skip if already signed
            if ipa.get('install_url'):
                continue
            
            local_path = ipa.get('local_path')
            if not local_path or not os.path.exists(local_path):
                continue
            
            try:
                # Extract app name from filename (remove .ipa extension)
                app_name = ipa['app_name'] if ipa['app_name'] != 'Unknown' else ipa['original_filename'].replace('.ipa', '')
                bundle_id = ipa['bundle_id'] if ipa['bundle_id'] != 'com.unknown.app' else f"com.signed.{app_name.lower().replace(' ', '').replace('-', '')}"
                version = ipa['version'] if ipa['version'] != '1.0' else '1.0'
            
                # Sign the IPA
                sign_result = await self.sign_ipa_from_local(
                    local_path,
                    p12_data,
                    mobileprovision_data,
                    app_name,
                    bundle_id,
                    version,
                    app_name
                )
                
                if sign_result:
                    # Update database with signed IPA info and parsed app info
                    await db.update_ipa_signed_info(
                        ipa['id'],
                        sign_result['ipa_filename'],
                        sign_result['plist_filename'],
                        sign_result['ipa_url'],
                        sign_result['plist_url'],
                        sign_result['install_url']
                    )
                    
                    # Update app info in database if we have better information
                    if 'app_info' in sign_result:
                        app_info = sign_result['app_info']
                        await db.update_ipa_metadata(
                            ipa['id'],
                            app_info['app_name'],
                            app_info['bundle_id'],
                            app_info['version']
                        )
                    
                    signed_count += 1
                else:
                    pass
                    
            except Exception as e:
                continue
        
        return signed_count
    
    def test_zsign_installation(self) -> bool:
        """Test if zsign is properly installed and working"""
        try:
            # Test zsign version
            result = subprocess.run(['zsign', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                return True
            else:
                return False
        except Exception as e:
            return False
