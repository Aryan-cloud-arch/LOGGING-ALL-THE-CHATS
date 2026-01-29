#!/usr/bin/env python3
"""
Telegram Mirror Bot - Interactive Setup
========================================
Beautiful, user-friendly setup wizard for configuration.

Features:
    ✨ Interactive prompts
    ✨ Input validation
    ✨ Connection testing
    ✨ Automatic .env generation
    ✨ Configuration backup
    ✨ Error handling
    ✨ Beautiful UI
"""

import os
import sys
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from getpass import getpass

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    COLORS_AVAILABLE = True
except ImportError:
    COLORS_AVAILABLE = False
    
    # Fallback for no colorama
    class Fore:
        GREEN = RED = YELLOW = CYAN = BLUE = MAGENTA = WHITE = RESET = ""
    
    class Style:
        BRIGHT = DIM = RESET_ALL = ""

# Banner
SETUP_BANNER = f"""
{Fore.CYAN}{Style.BRIGHT}
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║              🚀 TELEGRAM MIRROR BOT SETUP 🚀              ║
║                                                           ║
║          Interactive Configuration Wizard v1.0            ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
{Style.RESET_ALL}
"""


class SetupWizard:
    """
    Interactive setup wizard with validation and testing.
    
    Features:
        ✅ Step-by-step configuration
        ✅ Input validation
        ✅ Connection testing
        ✅ Error recovery
        ✅ Beautiful UI
    """
    
    def __init__(self):
        """Initialize setup wizard."""
        self.config: Dict[str, Any] = {}
        self.env_vars: Dict[str, str] = {}
    
    def print_header(self, text: str) -> None:
        """Print section header."""
        print(f"\n{Fore.CYAN}{Style.BRIGHT}{'=' * 60}")
        print(f"  {text}")
        print(f"{'=' * 60}{Style.RESET_ALL}\n")
    
    def print_step(self, step: int, total: int, description: str) -> None:
        """Print step information."""
        print(f"{Fore.YELLOW}[Step {step}/{total}] {description}{Style.RESET_ALL}\n")
    
    def print_success(self, message: str) -> None:
        """Print success message."""
        print(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}")
    
    def print_error(self, message: str) -> None:
        """Print error message."""
        print(f"{Fore.RED}❌ {message}{Style.RESET_ALL}")
    
    def print_warning(self, message: str) -> None:
        """Print warning message."""
        print(f"{Fore.YELLOW}⚠️  {message}{Style.RESET_ALL}")
    
    def print_info(self, message: str) -> None:
        """Print info message."""
        print(f"{Fore.CYAN}💡 {message}{Style.RESET_ALL}")
    
    def prompt(self, question: str, default: str = None, secret: bool = False) -> str:
        """
        Prompt user for input.
        
        Args:
            question: Question to ask
            default: Default value
            secret: Hide input (for passwords)
            
        Returns:
            str: User input
        """
        if default:
            prompt_text = f"{Fore.WHITE}{question} [{Fore.GREEN}{default}{Fore.WHITE}]: {Style.RESET_ALL}"
        else:
            prompt_text = f"{Fore.WHITE}{question}: {Style.RESET_ALL}"
        
        if secret:
            value = getpass(prompt_text)
        else:
            value = input(prompt_text)
        
        return value.strip() or default
    
    def prompt_yes_no(self, question: str, default: bool = True) -> bool:
        """
        Prompt yes/no question.
        
        Args:
            question: Question to ask
            default: Default value
            
        Returns:
            bool: User response
        """
        default_str = "Y/n" if default else "y/N"
        response = self.prompt(f"{question} ({default_str})", "y" if default else "n")
        
        return response.lower() in ['y', 'yes', '1', 'true']
    
    async def run(self) -> bool:
        """
        Run the setup wizard.
        
        Returns:
            bool: True if setup successful
        """
        try:
            print(SETUP_BANNER)
            print(f"{Fore.WHITE}Welcome! Let's configure your Telegram Mirror Bot.{Style.RESET_ALL}")
            print(f"{Fore.WHITE}This wizard will guide you through the setup process.{Style.RESET_ALL}\n")
            
            # Step 1: Telegram Configuration
            if not await self.setup_telegram():
                return False
            
            # Step 2: MongoDB Configuration
            if not await self.setup_mongodb():
                return False
            
            # Step 3: Optional Settings
            if not await self.setup_optional():
                return False
            
            # Step 4: Save Configuration
            if not await self.save_configuration():
                return False
            
            # Step 5: Test Connections
            if self.prompt_yes_no("\nWould you like to test connections now?", True):
                await self.test_connections()
            
            # Success!
            self.print_header("✅ SETUP COMPLETE!")
            print(f"{Fore.GREEN}Your Telegram Mirror Bot is now configured!{Style.RESET_ALL}\n")
            print(f"{Fore.CYAN}Next steps:{Style.RESET_ALL}")
            print(f"  1. Review your configuration in {Fore.YELLOW}.env{Style.RESET_ALL}")
            print(f"  2. Add both bots to your backup group")
            print(f"  3. Run the bot: {Fore.GREEN}python main.py{Style.RESET_ALL}\n")
            
            return True
            
        except KeyboardInterrupt:
            print(f"\n\n{Fore.YELLOW}Setup cancelled by user.{Style.RESET_ALL}")
            return False
        except Exception as e:
            self.print_error(f"Setup failed: {e}")
            return False
    
    async def setup_telegram(self) -> bool:
        """Setup Telegram configuration."""
        self.print_header("📱 TELEGRAM CONFIGURATION")
        self.print_step(1, 5, "Telegram API & Bots")
        
        print(f"{Fore.CYAN}First, we need your Telegram API credentials.{Style.RESET_ALL}")
        self.print_info("Get them from: https://my.telegram.org/apps\n")
        
        # API ID
        while True:
            api_id = self.prompt("Enter your API ID")
            if api_id and api_id.isdigit():
                self.env_vars['TELEGRAM_API_ID'] = api_id
                self.config['api_id'] = int(api_id)
                break
            self.print_error("Invalid API ID. Must be a number.")
        
        # API Hash
        while True:
            api_hash = self.prompt("Enter your API Hash", secret=True)
            if api_hash and len(api_hash) == 32:
                self.env_vars['TELEGRAM_API_HASH'] = api_hash
                self.config['api_hash'] = api_hash
                break
            self.print_error("Invalid API Hash. Should be 32 characters.")
        
        print(f"\n{Fore.CYAN}Now, let's setup your bots.{Style.RESET_ALL}")
        self.print_info("Create bots with @BotFather on Telegram\n")
        
        # Your Bot Token
        while True:
            your_token = self.prompt("Enter YOUR bot token (for your messages)", secret=True)
            if self.validate_bot_token(your_token):
                self.env_vars['TELEGRAM_YOUR_BOT_TOKEN'] = your_token
                self.config['your_bot_token'] = your_token
                break
            self.print_error("Invalid bot token format.")
        
        # Your Bot Name
        your_name = self.prompt("Enter YOUR bot name", "YourBot")
        self.env_vars['TELEGRAM_YOUR_BOT_NAME'] = your_name
        self.config['your_bot_name'] = your_name
        
        # Her Bot Token
        while True:
            her_token = self.prompt("Enter HER bot token (for her messages)", secret=True)
            if self.validate_bot_token(her_token):
                self.env_vars['TELEGRAM_HER_BOT_TOKEN'] = her_token
                self.config['her_bot_token'] = her_token
                break
            self.print_error("Invalid bot token format.")
        
        # Her Bot Name
        her_name = self.prompt("Enter HER bot name", "HerBot")
        self.env_vars['TELEGRAM_HER_BOT_NAME'] = her_name
        self.config['her_bot_name'] = her_name
        
        print(f"\n{Fore.CYAN}Account & User Information{Style.RESET_ALL}\n")
        
        # Your Phone
        while True:
            phone = self.prompt("Enter YOUR phone number (with +)", "+1234567890")
            if phone.startswith('+') and phone[1:].replace(' ', '').isdigit():
                self.env_vars['TELEGRAM_YOUR_PHONE'] = phone
                self.config['your_phone'] = phone
                break
            self.print_error("Invalid phone format. Must start with + and contain digits.")
        
        # Your Name
        your_display_name = self.prompt("Enter YOUR display name", "You")
        self.env_vars['TELEGRAM_YOUR_NAME'] = your_display_name
        self.config['your_name'] = your_display_name
        
        # Her User ID
        print(f"\n{Fore.CYAN}To get her Telegram ID, you can:{Style.RESET_ALL}")
        print("  1. Forward a message from her to @userinfobot")
        print("  2. Use @RawDataBot\n")
        
        while True:
            her_id = self.prompt("Enter HER Telegram User ID")
            if her_id and (her_id.isdigit() or (her_id.startswith('-') and her_id[1:].isdigit())):
                self.env_vars['TELEGRAM_HER_USER_ID'] = her_id
                self.config['her_user_id'] = int(her_id)
                break
            self.print_error("Invalid User ID. Must be a number.")
        
        # Her Name
        her_display_name = self.prompt("Enter HER display name", "Her")
        self.env_vars['TELEGRAM_HER_NAME'] = her_display_name
        self.config['her_name'] = her_display_name
        
        # Backup Group ID
        print(f"\n{Fore.CYAN}Backup Group Configuration{Style.RESET_ALL}")
        print("Create a group and add both bots to it.")
        print("To get group ID, forward a message from the group to @userinfobot\n")
        
        while True:
            group_id = self.prompt("Enter BACKUP GROUP ID (starts with -100)")
            if group_id and group_id.startswith('-100') and group_id[1:].isdigit():
                self.env_vars['TELEGRAM_GROUP_ID'] = group_id
                self.config['group_id'] = int(group_id)
                break
            self.print_error("Invalid Group ID. Should start with -100")
        
        self.print_success("Telegram configuration complete!\n")
        return True
    
    async def setup_mongodb(self) -> bool:
        """Setup MongoDB configuration."""
        self.print_header("🗄️  MONGODB CONFIGURATION")
        self.print_step(2, 5, "Database Settings")
        
        print(f"{Fore.CYAN}Configure your MongoDB connection.{Style.RESET_ALL}\n")
        
        # MongoDB Host
        host = self.prompt("MongoDB Host", "localhost")
        self.env_vars['MONGODB_HOST'] = host
        self.config['mongodb_host'] = host
        
        # MongoDB Port
        port = self.prompt("MongoDB Port", "27017")
        self.env_vars['MONGODB_PORT'] = port
        self.config['mongodb_port'] = int(port)
        
        # Authentication
        if self.prompt_yes_no("Does MongoDB require authentication?", False):
            username = self.prompt("MongoDB Username")
            password = self.prompt("MongoDB Password", secret=True)
            
            self.env_vars['MONGODB_USERNAME'] = username
            self.env_vars['MONGODB_PASSWORD'] = password
            self.config['mongodb_username'] = username
            self.config['mongodb_password'] = password
        
        # Database Name
        database = self.prompt("Database Name", "telegram_mirror")
        self.env_vars['MONGODB_DATABASE'] = database
        self.config['mongodb_database'] = database
        
        self.print_success("MongoDB configuration complete!\n")
        return True
    
    async def setup_optional(self) -> bool:
        """Setup optional settings."""
        self.print_header("⚙️  OPTIONAL SETTINGS")
        self.print_step(3, 5, "Optimization & Features")
        
        if not self.prompt_yes_no("Configure advanced settings?", False):
            self.print_info("Using default settings for all optional configurations.")
            return True
        
        print(f"\n{Fore.CYAN}Media Processing{Style.RESET_ALL}\n")
        
        # Photo Optimization
        if self.prompt_yes_no("Enable automatic photo optimization?", True):
            self.env_vars['MEDIA_OPTIMIZE_PHOTOS'] = "true"
            quality = self.prompt("Photo quality (1-100)", "85")
            self.env_vars['MEDIA_PHOTO_QUALITY'] = quality
        
        # Video Compression
        if self.prompt_yes_no("Enable automatic video compression?", False):
            self.env_vars['MEDIA_COMPRESS_VIDEOS'] = "true"
        
        print(f"\n{Fore.CYAN}Logging{Style.RESET_ALL}\n")
        
        # Log Level
        log_level = self.prompt("Log level (DEBUG/INFO/WARNING/ERROR)", "INFO")
        self.env_vars['LOGGING_LEVEL'] = log_level.upper()
        
        # Colored Logs
        if self.prompt_yes_no("Use colored console output?", True):
            self.env_vars['LOGGING_USE_COLORS'] = "true"
        
        self.print_success("Optional settings configured!\n")
        return True
    
    async def save_configuration(self) -> bool:
        """Save configuration to files."""
        self.print_header("💾 SAVING CONFIGURATION")
        self.print_step(4, 5, "Writing Configuration Files")
        
        try:
            # Create .env file
            env_path = Path('.env')
            
            if env_path.exists():
                if not self.prompt_yes_no("\n.env file exists. Overwrite?", False):
                    self.print_warning("Configuration not saved. Exiting.")
                    return False
                
                # Backup existing
                backup_path = Path('.env.backup')
                env_path.rename(backup_path)
                self.print_info(f"Existing .env backed up to {backup_path}")
            
            # Write .env
            with open(env_path, 'w') as f:
                f.write("# Telegram Mirror Bot Configuration\n")
                f.write("# Generated by setup wizard\n\n")
                
                # Telegram Section
                f.write("# === TELEGRAM CONFIGURATION ===\n")
                for key, value in self.env_vars.items():
                    if key.startswith('TELEGRAM_'):
                        f.write(f"{key}={value}\n")
                
                # MongoDB Section
                f.write("\n# === MONGODB CONFIGURATION ===\n")
                for key, value in self.env_vars.items():
                    if key.startswith('MONGODB_'):
                        f.write(f"{key}={value}\n")
                
                # Other Sections
                f.write("\n# === OPTIONAL SETTINGS ===\n")
                for key, value in self.env_vars.items():
                    if not key.startswith('TELEGRAM_') and not key.startswith('MONGODB_'):
                        f.write(f"{key}={value}\n")
            
            self.print_success(f"Configuration saved to {env_path}")
            
            # Create config.json for backup
            config_path = Path('config.json')
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            self.print_success(f"Backup config saved to {config_path}\n")
            
            return True
            
        except Exception as e:
            self.print_error(f"Failed to save configuration: {e}")
            return False
    
    async def test_connections(self) -> None:
        """Test connections to services."""
        self.print_header("🧪 TESTING CONNECTIONS")
        self.print_step(5, 5, "Connectivity Tests")
        
        print(f"{Fore.CYAN}Testing MongoDB connection...{Style.RESET_ALL}")
        
        try:
            from motor.motor_asyncio import AsyncIOMotorClient
            
            # Build MongoDB URI
            if 'mongodb_username' in self.config:
                uri = f"mongodb://{self.config['mongodb_username']}:{self.config['mongodb_password']}@{self.config['mongodb_host']}:{self.config['mongodb_port']}"
            else:
                uri = f"mongodb://{self.config['mongodb_host']}:{self.config['mongodb_port']}"
            
            # Test connection
            client = AsyncIOMotorClient(uri, serverSelectionTimeoutMS=5000)
            await client.admin.command('ping')
            
            self.print_success("MongoDB connection successful!")
            
            client.close()
            
        except Exception as e:
            self.print_error(f"MongoDB connection failed: {e}")
            self.print_warning("Please check your MongoDB configuration.")
        
        print(f"\n{Fore.CYAN}Note: Bot token validation requires running the main bot.{Style.RESET_ALL}")
    
    def validate_bot_token(self, token: str) -> bool:
        """
        Validate bot token format.
        
        Args:
            token: Bot token to validate
            
        Returns:
            bool: True if valid format
        """
        if not token:
            return False
        
        parts = token.split(':')
        if len(parts) != 2:
            return False
        
        return parts[0].isdigit() and len(parts[1]) > 20
    
    @staticmethod
    def validate_phone(phone: str) -> bool:
        """
        Validate phone number format.
        
        Args:
            phone: Phone number
            
        Returns:
            bool: True if valid
        """
        return phone.startswith('+') and phone[1:].replace(' ', '').isdigit()


# ==================== MAIN FUNCTION ====================

async def main():
    """Main setup entry point."""
    wizard = SetupWizard()
    success = await wizard.run()
    
    return 0 if success else 1


# ==================== ENTRY POINT ====================

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Setup cancelled.{Style.RESET_ALL}")
        sys.exit(1)
    except Exception as e:
        print(f"\n{Fore.RED}Setup error: {e}{Style.RESET_ALL}")
        sys.exit(1)
