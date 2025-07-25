TEXTS = {
    # Welcome and main menu messages
    "welcome": "Hello.\n\nBalance: ${balance:.2f}\nDevices: {devices}",
    "welcome_no_balance": "Hello.\n\nDevices: {devices}",
    "welcome_no_api": "Hello.\n\nDevices: {devices}\n\nSet your API key first.",
    "welcome_normal_user": "Hello.\n\nWelcome to the certificate management bot.\n\nUse the buttons below to search for certificates or use your access keys.",
    
    # API key related
    "api_key_required": "Set your API key first.",
    "set_api_key": "Send your API key:",
    "api_key_success": "API key set. Balance: ${balance:.2f}",
    "api_key_invalid": "Invalid API key: {error}",
    
    # Registration process
    "select_plan_first": "Register UDID\n\nFirst, select a plan:",
    "register_udid_after_plan": "Selected Plan: {plan}\n\nNow send UDID (format: 00008130-0016051E223A001C):",
    "invalid_udid": "Invalid UDID format.\nUse: 00008130-0016051E223A001C",
    "registering": "Registering...",
    "registration_failed": "Registration failed: {error}",
    "registration_success": "UDID : {udid}\nAdded on : {date}\nStatus: {status} {emoji}\nName : {name}",
    
    # Search functionality
    "search": "Search\n\nSend UDID or Certificate ID to search:",
    "no_search_results": "No results found for: {query}",
    "search_result": "UDID : {udid}\nAdded on : {date}\nStatus: {status} {emoji}\nName : {name}",
    
    # Settings
    "settings": "Settings\n\nAPI Key: {api_status}\nP12 Thumbnail: {p12_status}\nMobileprovision Thumbnail: {mp_status}",
    "set_thumbnails_start": "Set Thumbnails\n\nFirst, send an image for P12 file thumbnail:",
    "p12_thumbnail_success": "P12 thumbnail set.\n\nNow send an image for mobileprovision file thumbnail:",
    "thumbnails_success": "Both thumbnails set successfully.",
    "thumbnail_error": "Please send an image file.",
    "thumbnail_save_error": "Error setting {type} thumbnail: {error}",
    
    # Certificate management
    "certificate_disabled": "Certificate is disabled.",
    "certificate_not_found": "Certificate not found for this UDID.",
    "certificate_processing": "Certificate is still processing. No mobileprovision available yet.",
    "certificate_no_files": "No certificate files available for download.",
    "certificate_download_error": "Error downloading certificate: {error}",
    "certificate_file_error": "Error preparing {file_type} file: {error}",
    "certificate_group_error": "Error sending files as group: {error}",
    "certificate_password": "Password: {password}",
    "certificate_signed_message": "The application has been signed for the specified {udid} and is now ready for installation.",
    
    # Status texts
    "status_active": "Active",
    "status_processing": "Processing",
    "status_enabled": "Enabled",
    "status_disabled": "Disabled",
    "status_set": "Set",
    "status_not_set": "Not Set",
    
    # Key management
    "create_keys_start": "Create Keys\n\nCurrent Keys:\n{stats}\n\nSelect plan to create keys:",
    "no_keys_yet": "No keys created yet",
    "key_plan_selected": "Selected Plan: {plan}\n\nHow many keys do you want to create?\nSend a number (1-100):",
    "key_quantity_invalid": "Please enter a number between 1 and 100:",
    "key_quantity_error": "Please enter a valid number:",
    "keys_created": "Created {quantity} keys for {plan}\n\n{keys}\n\nSave these keys. You can use them with the 'Use Key' button.",
    "use_key_start": "Use Key\n\nSend your key code (e.g., JKSD678HJD):",
    "key_format_invalid": "Invalid key format. Key should be 10 characters (letters and numbers).\nExample: JKSD678HJD",
    "key_not_found": "Key not found. Please check your key code.",
    "key_already_used": "This key has already been used.",
    "key_valid": "Valid key for {plan}\n\nNow send UDID to register:",
    "key_registration_success": "UDID : {udid}\nAdded on : {date}\nStatus: {status} {emoji}\nName : {name}\nPlan: {plan}\nKey Used: {key_code}",
    
    # IPA management
    "ipa_management": "IPA Management\n\nYour IPAs: {count}\n\nUpload IPA files to automatically sign them with your certificates.",
    "upload_ipa_start": "Upload IPA\n\nSend your IPA file (it will be saved locally for signing):",
    "ipa_file_invalid": "Please send a valid IPA file.",
    "ipa_uploading": "Uploading IPA file...",
    "ipa_upload_success": "IPA Uploaded Successfully.\n\nFile: {filename}\nSize: {size:.1f} MB\nStored locally on server\n\nYour IPA will be automatically signed when you download certificates.",
    "ipa_upload_error": "Error processing IPA: {error}",
    "no_ipas": "No IPAs uploaded yet.\n\nUpload your first IPA to get started.",
    "ipa_list_header": "Your IPAs:\n\n",
    "ipa_details": "{app_name}\n\nBundle ID: {bundle_id}\nVersion: {version}\nFile: {filename}\nSize: {size:.1f} MB\nUploaded: {date}\nLocal File: {local_status}\n\nStatus: {status}",
    "ipa_local_available": "Available",
    "ipa_local_missing": "Missing",
    "ipa_status_ready": "Ready for installation",
    "ipa_status_waiting": "Waiting for signing",
    "ipa_signed_date": "\nSigned: {date}",
    "ipa_not_found": "IPA not found.",
    "ipa_not_signed": "IPA not signed yet. Download a certificate first.",
    "ipa_install_link": "Install Link for {app_name}\n\nDirect Install:\n{install_url}\n\nPlist URL:\n{plist_url}\n\nIPA URL:\n{ipa_url}\n\nTap the install link on your iOS device to install the app.",
    "ipa_deleted": "IPA deleted successfully.",
    "ipa_preparing_link": "Preparing install link...",
    "ipa_install_button": "🚀 Install {app_name}",
    "ipa_install_message": "{app_name}\n\nTap the button below to install:",
    
    # Button texts
    "btn_register_udid": "📱 Register UDID",
    "btn_search": "🔍 Check UDiD",
    "btn_use_key": "🎫 Use Key",
    "btn_manage_ipas": "📦 Manage IPAs",
    "btn_settings": "⚙️ Settings",
    "btn_back": "🔙 Back",
    "btn_set_api_key": "Set API Key",
    "btn_set_thumbnails": "Set Thumbnails",
    "btn_create_keys": "Create Keys",
    "btn_get_certificate": "📜 Get Certificate",
    "btn_upload_ipa": "📤 Upload IPA",
    "btn_list_ipas": "📋 List IPAs",
    "btn_get_install_link": "🔗 Get Install Link",
    "btn_delete": "🗑️ Delete",
    "btn_enabled": "🟢 Enabled",
    "btn_disabled": "🔴 Disabled",
    
    # Plan names
    "plan_super0": "⚡ Super Plan - 0 Days",
    "plan_super40": "⚡ Super Plan - 40 Days",
    "plan_super90": "⚡ Super Plan - 90 Days",
    "plan_super180": "⚡ Super Plan - 180 Days",
    "plan_super360": "⚡ Super Plan - 360 Days",
    "plan_super_ipad360": "⚡ Super iPad - 360 Days",
    "plan_ordinary0": "⏳ Ordinary Plan - 0 Days",
    "plan_ordinary40": "⏳ Ordinary Plan - 40 Days",
    
    # Error messages
    "error_api_key_first": "Set your API key first.",
    "error_certificate_validation": "Certificate file validation failed",
    "error_zsign_failed": "zsign failed with return code {code}",
    "error_signed_ipa_not_found": "Signed IPA file not found",
    "error_upload_failed": "Failed to upload to storage",
    "error_signing_failed": "Error signing IPA: {error}",
    "error_updating_status": "Error updating status: {error}",
    
    # Success messages
    "success_registration": "Registration successful.",
    "success_certificate_downloaded": "Certificate downloaded successfully.",
    "success_key_created": "Key created successfully.",
    "success_ipa_uploaded": "IPA uploaded successfully.",
    "success_ipa_signed": "IPA signed successfully.",
    
    # General messages
    "unknown_command": "Use /start to see options.",
    "processing": "Processing...",
    "please_wait": "Please wait...",
    "operation_completed": "Operation completed.",
    "operation_failed": "Operation failed.",
    
    # File types for errors
    "file_type_p12": "P12",
    "file_type_mobileprovision": "mobileprovision",
    
    # Validation messages
    "validation_udid_format": "Invalid UDID format.\nUse: 00008130-0016051E223A001C",
    "validation_key_format": "Invalid key format. Key should be 10 characters (letters and numbers).\nExample: JKSD678HJD",
    "validation_number_range": "Please enter a number between {min} and {max}:",
    "validation_valid_number": "Please enter a valid number:",
    "validation_image_required": "Please send an image file.",
    "validation_ipa_required": "Please send a valid IPA file.",
    
    # Date and time
    "date_format": "%d/%m/%Y",
    "datetime_format": "%d/%m/%Y %H:%M",
    
    # File size units
    "size_mb": "{size:.1f} MB",
    "size_kb": "{size:.1f} KB",
    "size_bytes": "{size} bytes",
    
    # Statistics
    "stats_unused_keys": "{plan}: {unused}/{total} unused",
    "stats_balance": "Balance: ${balance:.2f}",
    "stats_devices": "Devices: {count}",
    "stats_ipas": "Your IPAs: {count}",
}
