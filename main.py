#!/usr/bin/env python3
"""
Telegram DM Mirror Bot
======================
Real-time conversation backup with bot personas.

Features:
    🔥 Automatic message mirroring
    🔥 View-once media capture
    🔥 Edit/delete tracking
    🔥 Reply chain preservation
    🔥 Unlimited file size support
    🔥 MongoDB persistence
    🔥 Auto-recovery on restart

Author: Your Name
Version: 1.0.0
"""

import sys
import os
import asyncio
import signal
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from config import init_config, get_config, ConfigValidator
from src.monitor import Monitor
from utils.logger import setup_logging, get_logger, get_log_stats
from utils.helpers import MemoryMonitor, TimeTracker
from utils.media_utils import cleanup_temp

# ASCII Art Banner
BANNER = """
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ████████╗███████╗██╗     ███████╗ ██████╗ ██████╗      ║
║   ╚══██╔══╝██╔════╝██║     ██╔════╝██╔════╝ ██╔══██╗     ║
║      ██║   █████╗  ██║     █████╗  ██║  ███╗██████╔╝     ║
║      ██║   ██╔══╝  ██║     ██╔══╝  ██║   ██║██╔══██╗     ║
║      ██║   ███████╗███████╗███████╗╚██████╔╝██║  ██║     ║
║      ╚═╝   ╚══════╝╚══════╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝     ║
║                                                           ║
║          📱 TELEGRAM DM MIRROR BOT 📱                     ║
║          Real-time Conversation Backup                   ║
║                  Version 1.0.0                           ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
"""


class Application:
    """
    Main application controller.
    
    Responsibilities:
        - Application lifecycle management
        - Component initialization
        - Graceful shutdown
        - Error recovery
        - Signal handling
    """
    
    def __init__(self):
        """Initialize application."""
        self.monitor: Optional[Monitor] = None
        self.memory_monitor: Optional[MemoryMonitor] = None
        self.running = False
        self.shutdown_event = asyncio.Event()
        self.logger = None
        self.config = None
        self.start_time = TimeTracker("Application")
    
    async def initialize(self) -> bool:
        """
        Initialize all application components.
        
        Returns:
            bool: True if initialization successful
        """
        try:
            print(BANNER)
            print("🚀 Initializing Telegram Mirror Bot...\n")
            
            # Step 1: Load Configuration
            print("📋 [1/6] Loading configuration...")
            self.config = init_config()
            print(f"    ✅ Environment: {self.config.environment.value}")
            print(f"    ✅ Debug Mode: {self.config.debug}\n")
            
            # Step 2: Setup Logging
            print("📝 [2/6] Setting up logging system...")
            setup_logging(
                level=self.config.logging.level,
                log_file=f"{self.config.logging.log_dir}/{self.config.logging.log_file}",
                use_colors=self.config.logging.use_colors,
                use_json=self.config.logging.use_json
            )
            self.logger = get_logger(__name__)
            self.logger.info("Logging system initialized")
            print("    ✅ Logging configured\n")
            
            # Step 3: Validate Configuration
            print("🔍 [3/6] Validating configuration...")
            validator = ConfigValidator(self.config)
            is_valid = await validator.validate_all()
            
            if not is_valid:
                print("    ❌ Configuration validation failed!")
                return False
            print("    ✅ Configuration valid\n")
            
            # Step 4: Initialize Memory Monitor
            if self.config.monitoring.enable_stats:
                print("🧠 [4/6] Starting memory monitor...")
                self.memory_monitor = MemoryMonitor(
                    threshold_mb=self.config.monitoring.memory_threshold_mb
                )
                await self.memory_monitor.start_monitoring()
                print("    ✅ Memory monitoring active\n")
            else:
                print("⏭️  [4/6] Memory monitoring disabled\n")
            
            # Step 5: Cleanup Old Files
            print("🧹 [5/6] Cleaning up old files...")
            await cleanup_temp(older_than_hours=24)
            print("    ✅ Cleanup completed\n")
            
            # Step 6: Initialize Monitor
            print("🔧 [6/6] Initializing monitor...")
            self.monitor = Monitor(self.config)
            
            if not await self.monitor.initialize():
                print("    ❌ Monitor initialization failed!")
                return False
            
            print("    ✅ Monitor ready\n")
            
            self.logger.info("=" * 60)
            self.logger.info("🎉 ALL SYSTEMS INITIALIZED SUCCESSFULLY!")
            self.logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Initialization failed: {e}", exc_info=True)
            else:
                print(f"❌ FATAL ERROR: {e}")
            return False
    
    async def run(self) -> None:
        """
        Run the main application loop.
        """
        try:
            self.running = True
            self.start_time.start()
            
            # Setup signal handlers
            self._setup_signal_handlers()
            
            self.logger.info("🚀 Starting monitor...")
            print("\n" + "=" * 60)
            print("🟢 BOT IS NOW RUNNING!")
            print("=" * 60)
            print(f"👤 Monitoring: {self.config.HER_NAME} (ID: {self.config.HER_USER_ID})")
            print(f"📦 Backup Group: {self.config.GROUP_ID}")
            print(f"🤖 Your Bot: @{self.config.YOUR_BOT_NAME}")
            print(f"🤖 Her Bot: @{self.config.HER_BOT_NAME}")
            print("=" * 60)
            print("\n💡 Press Ctrl+C to stop\n")
            
            # Start monitor
            monitor_task = asyncio.create_task(self.monitor.run())
            
            # Wait for shutdown signal or monitor completion
            done, pending = await asyncio.wait(
                [monitor_task, self.shutdown_event.wait()],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel pending tasks
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"Runtime error: {e}", exc_info=True)
        finally:
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """
        Gracefully shutdown application.
        """
        if not self.running:
            return
        
        self.running = False
        elapsed = self.start_time.stop()
        
        print("\n" + "=" * 60)
        print("🛑 SHUTTING DOWN...")
        print("=" * 60)
        
        # Stop monitor
        if self.monitor:
            self.logger.info("Stopping monitor...")
            print("📴 Stopping monitor...")
            await self.monitor.stop()
            print("   ✅ Monitor stopped")
        
        # Stop memory monitor
        if self.memory_monitor:
            self.logger.info("Stopping memory monitor...")
            print("🧠 Stopping memory monitor...")
            await self.memory_monitor.stop_monitoring()
            print("   ✅ Memory monitor stopped")
        
        # Print statistics
        await self._print_statistics(elapsed)
        
        # Final cleanup
        print("\n🧹 Final cleanup...")
        await cleanup_temp()
        print("   ✅ Cleanup complete")
        
        print("\n" + "=" * 60)
        print("👋 GOODBYE! Bot stopped successfully.")
        print("=" * 60 + "\n")
        
        self.logger.info("Application shutdown complete")
    
    async def _print_statistics(self, runtime: float) -> None:
        """
        Print runtime statistics.
        
        Args:
            runtime: Total runtime in seconds
        """
        from utils.helpers import format_duration, format_file_size
        
        print("\n" + "=" * 60)
        print("📊 RUNTIME STATISTICS")
        print("=" * 60)
        
        # Runtime
        print(f"⏱️  Runtime: {format_duration(runtime)}")
        
        # Database stats
        if self.monitor and self.monitor.db:
            try:
                db_stats = await self.monitor.db.get_statistics()
                print(f"💬 Messages processed: {db_stats.total_messages}")
                print(f"📸 Media processed: {db_stats.total_media}")
                print(f"🔥 View-once saved: {db_stats.total_view_once}")
                print(f"✏️  Edits tracked: {db_stats.total_edits}")
                print(f"🗑️  Deletes tracked: {db_stats.total_deletes}")
            except Exception as e:
                self.logger.error(f"Failed to get DB stats: {e}")
        
        # Memory stats
        if self.memory_monitor:
            mem_stats = self.memory_monitor.get_stats()
            print(f"🧠 Memory (peak): {mem_stats.get('max_mb', 0):.1f} MB")
            print(f"🧠 Memory (avg): {mem_stats.get('average_mb', 0):.1f} MB")
        
        # Log stats
        log_stats = await get_log_stats().get_stats()
        print(f"📝 Total logs: {log_stats.get('total_logs', 0)}")
        print(f"❌ Errors: {log_stats.get('error_count', 0)}")
        
        print("=" * 60)
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(sig, frame):
            """Handle shutdown signals."""
            self.logger.info(f"Received signal {sig}")
            self.shutdown_event.set()
        
        # Register signals
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        if sys.platform != 'win32':
            signal.signal(signal.SIGHUP, signal_handler)


# ==================== MAIN FUNCTION ====================

async def main() -> int:
    """
    Main entry point.
    
    Returns:
        int: Exit code (0 = success, 1 = error)
    """
    app = Application()
    
    try:
        # Initialize
        if not await app.initialize():
            print("\n❌ Initialization failed. Please check your configuration.")
            return 1
        
        # Run
        await app.run()
        
        return 0
        
    except Exception as e:
        if app.logger:
            app.logger.critical(f"Fatal error: {e}", exc_info=True)
        else:
            print(f"\n💥 FATAL ERROR: {e}")
        
        return 1


# ==================== ENTRY POINT ====================

def check_python_version():
    """Check Python version compatibility."""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required!")
        print(f"   Current version: {sys.version}")
        sys.exit(1)


def check_requirements():
    """Check if required packages are installed."""
    required_packages = [
        'telethon',
        'pymongo',
        'motor',
        'pydantic',
        'python-dotenv',
        'colorama',
        'pillow',
        'aiofiles'
    ]
    
    missing = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)
    
    if missing:
        print("❌ Missing required packages:")
        for pkg in missing:
            print(f"   - {pkg}")
        print("\n💡 Install with: pip install -r requirements.txt")
        sys.exit(1)


if __name__ == "__main__":
    # Pre-flight checks
    check_python_version()
    
    # Check if setup was run
    if not Path('.env').exists() and not Path('config.json').exists():
        print("⚠️  Configuration not found!")
        print("💡 Please run setup first: python setup.py")
        sys.exit(1)
    
    check_requirements()
    
    # Run application
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n💥 FATAL ERROR: {e}")
        sys.exit(1)
