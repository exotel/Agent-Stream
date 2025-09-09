#!/usr/bin/env python3
"""
Universal Bot Launcher - Easy interface for creating and managing different types of AI bots
Supports sales, support, service collection, and custom bots with hot-reloading capabilities

Usage:
    python bot_launcher.py --interactive     # Interactive bot creation
    python bot_launcher.py --demo            # Run demo scenarios
    python bot_launcher.py --quick-start     # Quick start guide
"""

import asyncio
import argparse
import sys
import os
import json
from datetime import datetime
from typing import Dict, List, Optional

from bot_framework import BotManager, BotType, BotPersonality

class BotLauncher:
    """Universal launcher for creating and managing AI bots"""
    
    def __init__(self):
        self.bot_manager = BotManager()
        self.active_sessions = {}
    
    def display_banner(self):
        """Display welcome banner"""
        print("\n" + "="*80)
        print("🤖 UNIVERSAL AI BOT LAUNCHER 🚀")
        print("Create, customize, and deploy AI bots for any use case!")
        print("="*80)
        print("✨ Features:")
        print("  • Multi-sample rate support (8kHz, 16kHz, 24kHz)")
        print("  • Hot-reload configuration changes")
        print("  • Variable chunk processing")
        print("  • Enhanced Exotel integration")
        print("  • Multiple bot types: Sales, Support, Service Collection, etc.")
        print("="*80)
    
    async def interactive_mode(self):
        """Interactive bot creation and management"""
        self.display_banner()
        
        while True:
            print("\n🎯 MAIN MENU")
            print("1. Create New Bot")
            print("2. Manage Existing Bots")
            print("3. Run Demo Scenarios")
            print("4. View Templates")
            print("5. Import/Export Bots")
            print("6. Help & Documentation")
            print("7. Exit")
            
            choice = input("\nSelect an option (1-7): ").strip()
            
            if choice == '1':
                await self.create_bot_wizard()
            elif choice == '2':
                await self.manage_bots_menu()
            elif choice == '3':
                await self.demo_scenarios_menu()
            elif choice == '4':
                self.view_templates()
            elif choice == '5':
                await self.import_export_menu()
            elif choice == '6':
                self.show_help()
            elif choice == '7':
                print("👋 Goodbye! Shutting down all bots...")
                await self.shutdown_all_bots()
                break
            else:
                print("❌ Invalid option. Please try again.")
    
    async def create_bot_wizard(self):
        """Interactive bot creation wizard"""
        print("\n🧙‍♂️ BOT CREATION WIZARD")
        print("="*40)
        
        # Step 1: Choose bot type
        print("\n📋 Step 1: Choose Bot Type")
        bot_types = {
            '1': ('sales', 'Sales & Lead Generation'),
            '2': ('support', 'Customer Support'),
            '3': ('service_collection', 'Service Collection/Debt Recovery'),
            '4': ('appointment_booking', 'Appointment Booking'),
            '5': ('survey', 'Survey & Feedback Collection'),
            '6': ('custom', 'Custom Configuration')
        }
        
        for key, (_, description) in bot_types.items():
            print(f"  {key}. {description}")
        
        bot_type_choice = input("\nSelect bot type (1-6): ").strip()
        if bot_type_choice not in bot_types:
            print("❌ Invalid selection")
            return
        
        bot_type, bot_description = bot_types[bot_type_choice]
        
        # Step 2: Basic configuration
        print(f"\n🔧 Step 2: Configure {bot_description} Bot")
        bot_id = input("Bot ID (unique identifier): ").strip()
        if not bot_id:
            print("❌ Bot ID is required")
            return
        
        company_name = input("Company/Organization Name: ").strip() or "Your Company"
        service_description = input("Service Description: ").strip() or "Professional services"
        
        # Step 3: AI Configuration
        print("\n🤖 Step 3: AI Configuration")
        voices = {
            '1': 'alloy', '2': 'echo', '3': 'fable', 
            '4': 'onyx', '5': 'nova', '6': 'shimmer', '7': 'coral'
        }
        
        print("Available voices:")
        for key, voice in voices.items():
            print(f"  {key}. {voice}")
        
        voice_choice = input("Select voice (1-7, default=1): ").strip() or '1'
        voice = voices.get(voice_choice, 'alloy')
        
        temperature = input("AI Temperature (0.1-1.0, default=0.7): ").strip()
        try:
            temperature = float(temperature) if temperature else 0.7
            temperature = max(0.1, min(1.0, temperature))
        except ValueError:
            temperature = 0.7
        
        # Step 4: Advanced options
        print("\n⚙️ Step 4: Advanced Options")
        
        personalities = {
            '1': 'professional', '2': 'friendly', '3': 'casual',
            '4': 'empathetic', '5': 'direct', '6': 'enthusiastic'
        }
        
        print("Bot personalities:")
        for key, personality in personalities.items():
            print(f"  {key}. {personality}")
        
        personality_choice = input("Select personality (1-6, default=1): ").strip() or '1'
        personality = personalities.get(personality_choice, 'professional')
        
        custom_instructions = input("Custom instructions (optional): ").strip()
        
        # Step 5: Create the bot
        print(f"\n🚀 Step 5: Creating Bot '{bot_id}'")
        
        config_overrides = {
            "company_name": company_name,
            "service_description": service_description,
            "voice": voice,
            "temperature": temperature,
            "personality": personality
        }
        
        try:
            bot_config = self.bot_manager.create_bot(
                bot_type=bot_type,
                bot_id=bot_id,
                config_overrides=config_overrides,
                custom_instructions=custom_instructions
            )
            
            print(f"✅ Bot '{bot_id}' created successfully!")
            
            # Ask if user wants to start the bot
            start_now = input("\nStart the bot now? (y/n, default=y): ").strip().lower()
            if start_now != 'n':
                port = input("Port number (default=auto): ").strip()
                if port:
                    try:
                        port = int(port)
                    except ValueError:
                        port = None
                
                await self.bot_manager.start_bot(bot_id, port=port)
                bot_info = self.bot_manager.get_bot_info(bot_id)
                
                print(f"🚀 Bot started on port {bot_info['port']}")
                print("📞 WebSocket endpoints:")
                for endpoint in bot_info['endpoints']:
                    print(f"   • {endpoint}")
                
                print(f"\n🧪 Test your bot:")
                print(f"python test_enhanced_bot.py --server ws://localhost:{bot_info['port']} --interactive")
            
        except Exception as e:
            print(f"❌ Failed to create bot: {e}")
    
    async def manage_bots_menu(self):
        """Manage existing bots"""
        print("\n🔧 BOT MANAGEMENT")
        print("="*30)
        
        available_bots = self.bot_manager.list_available_bots()
        active_bots = self.bot_manager.list_active_bots()
        
        if not available_bots:
            print("No bots found. Create a bot first!")
            return
        
        print("\n📋 Available Bots:")
        for i, bot_id in enumerate(available_bots, 1):
            status = "🟢 ACTIVE" if bot_id in active_bots else "⚪ INACTIVE"
            info = self.bot_manager.get_bot_info(bot_id)
            bot_type = info.get('config', {}).get('bot_type', 'unknown')
            print(f"  {i}. {bot_id} ({bot_type}) - {status}")
        
        print("\nActions:")
        print("1. Start Bot")
        print("2. Stop Bot")
        print("3. Modify Bot")
        print("4. View Bot Details")
        print("5. Delete Bot")
        print("6. Back to Main Menu")
        
        action = input("\nSelect action (1-6): ").strip()
        
        if action in ['1', '2', '3', '4', '5']:
            bot_choice = input("Enter bot number: ").strip()
            try:
                bot_index = int(bot_choice) - 1
                if 0 <= bot_index < len(available_bots):
                    bot_id = available_bots[bot_index]
                    
                    if action == '1':
                        await self.start_bot_interactive(bot_id)
                    elif action == '2':
                        await self.stop_bot_interactive(bot_id)
                    elif action == '3':
                        await self.modify_bot_interactive(bot_id)
                    elif action == '4':
                        self.view_bot_details(bot_id)
                    elif action == '5':
                        await self.delete_bot_interactive(bot_id)
                else:
                    print("❌ Invalid bot number")
            except ValueError:
                print("❌ Invalid input")
    
    async def start_bot_interactive(self, bot_id: str):
        """Start a bot interactively"""
        if bot_id in self.bot_manager.list_active_bots():
            print(f"⚠️ Bot '{bot_id}' is already running")
            return
        
        port = input("Port number (default=auto): ").strip()
        if port:
            try:
                port = int(port)
            except ValueError:
                port = None
        
        try:
            await self.bot_manager.start_bot(bot_id, port=port)
            bot_info = self.bot_manager.get_bot_info(bot_id)
            print(f"✅ Started bot '{bot_id}' on port {bot_info['port']}")
            
            print("📞 WebSocket endpoints:")
            for endpoint in bot_info['endpoints']:
                print(f"   • {endpoint}")
                
        except Exception as e:
            print(f"❌ Failed to start bot: {e}")
    
    async def stop_bot_interactive(self, bot_id: str):
        """Stop a bot interactively"""
        if bot_id not in self.bot_manager.list_active_bots():
            print(f"⚠️ Bot '{bot_id}' is not running")
            return
        
        try:
            await self.bot_manager.stop_bot(bot_id)
            print(f"✅ Stopped bot '{bot_id}'")
        except Exception as e:
            print(f"❌ Failed to stop bot: {e}")
    
    async def modify_bot_interactive(self, bot_id: str):
        """Modify a bot interactively"""
        print(f"\n🔧 Modifying Bot: {bot_id}")
        
        current_info = self.bot_manager.get_bot_info(bot_id)
        if 'config' in current_info:
            config = current_info['config']
            print(f"Current voice: {config.get('voice', 'unknown')}")
            print(f"Current personality: {config.get('personality', 'unknown')}")
        
        modifications = {}
        
        # Voice modification
        new_voice = input("New voice (leave empty to keep current): ").strip()
        if new_voice:
            voices = ['alloy', 'echo', 'fable', 'onyx', 'nova', 'shimmer', 'coral']
            if new_voice in voices:
                modifications['voice'] = new_voice
            else:
                print(f"⚠️ Invalid voice. Available: {', '.join(voices)}")
        
        # Temperature modification
        new_temp = input("New temperature (0.1-1.0, leave empty to keep current): ").strip()
        if new_temp:
            try:
                temp = float(new_temp)
                if 0.1 <= temp <= 1.0:
                    modifications['temperature'] = temp
                else:
                    print("⚠️ Temperature must be between 0.1 and 1.0")
            except ValueError:
                print("⚠️ Invalid temperature value")
        
        # Custom instructions
        new_instructions = input("New custom instructions (leave empty to keep current): ").strip()
        if new_instructions:
            modifications['custom_instructions'] = new_instructions
        
        if modifications:
            try:
                self.bot_manager.modify_bot(bot_id, modifications)
                print(f"✅ Modified bot '{bot_id}' - changes applied via hot-reload!")
                for key, value in modifications.items():
                    print(f"   {key}: {value}")
            except Exception as e:
                print(f"❌ Failed to modify bot: {e}")
        else:
            print("No modifications made")
    
    def view_bot_details(self, bot_id: str):
        """View detailed bot information"""
        print(f"\n📊 Bot Details: {bot_id}")
        print("="*40)
        
        info = self.bot_manager.get_bot_info(bot_id)
        
        if 'config' in info:
            config = info['config']
            print(f"Type: {config.get('bot_type', 'unknown')}")
            print(f"Voice: {config.get('voice', 'unknown')}")
            print(f"Personality: {config.get('personality', 'unknown')}")
            print(f"Capabilities: {', '.join(config.get('capabilities', []))}")
        
        if info.get('active'):
            print(f"Status: 🟢 ACTIVE")
            print(f"Host: {info['host']}")
            print(f"Port: {info['port']}")
            print("Endpoints:")
            for endpoint in info['endpoints']:
                print(f"  • {endpoint}")
        else:
            print("Status: ⚪ INACTIVE")
    
    async def delete_bot_interactive(self, bot_id: str):
        """Delete a bot interactively"""
        confirm = input(f"❓ Delete bot '{bot_id}'? This cannot be undone (y/n): ").strip().lower()
        if confirm == 'y':
            try:
                # Stop bot if running
                if bot_id in self.bot_manager.list_active_bots():
                    await self.bot_manager.stop_bot(bot_id)
                
                # Delete configuration file
                config_file = self.bot_manager.bots_dir / f"{bot_id}.json"
                if config_file.exists():
                    config_file.unlink()
                
                # Remove from memory
                if bot_id in self.bot_manager.bot_configs:
                    del self.bot_manager.bot_configs[bot_id]
                
                print(f"✅ Deleted bot '{bot_id}'")
            except Exception as e:
                print(f"❌ Failed to delete bot: {e}")
    
    async def demo_scenarios_menu(self):
        """Demo scenarios menu"""
        print("\n🎪 DEMO SCENARIOS")
        print("="*30)
        print("1. Restaurant Reservation Bot")
        print("2. E-Commerce Support System (3 bots)")
        print("3. Hot-Reload Demonstration")
        print("4. Multi-Sample Rate Testing")
        print("5. Back to Main Menu")
        
        choice = input("\nSelect demo (1-5): ").strip()
        
        if choice == '1':
            await self.run_restaurant_demo()
        elif choice == '2':
            await self.run_ecommerce_demo()
        elif choice == '3':
            await self.run_hot_reload_demo()
        elif choice == '4':
            await self.run_sample_rate_demo()
    
    async def run_restaurant_demo(self):
        """Run restaurant reservation bot demo"""
        print("\n🍽️ Starting Restaurant Reservation Bot Demo...")
        
        # Import and run the restaurant example
        try:
            import subprocess
            result = subprocess.run([
                sys.executable, 
                "examples/restaurant_bot.py"
            ], cwd=os.getcwd())
            
        except Exception as e:
            print(f"❌ Failed to run restaurant demo: {e}")
    
    async def run_ecommerce_demo(self):
        """Run e-commerce support system demo"""
        print("\n🛍️ Starting E-Commerce Support System Demo...")
        
        try:
            import subprocess
            result = subprocess.run([
                sys.executable,
                "examples/ecommerce_support_bot.py"
            ], cwd=os.getcwd())
            
        except Exception as e:
            print(f"❌ Failed to run e-commerce demo: {e}")
    
    async def run_hot_reload_demo(self):
        """Run hot-reload demonstration"""
        print("\n🔄 Starting Hot-Reload Demo...")
        
        try:
            import subprocess
            result = subprocess.run([
                sys.executable,
                "examples/ecommerce_support_bot.py",
                "--hot-reload-demo"
            ], cwd=os.getcwd())
            
        except Exception as e:
            print(f"❌ Failed to run hot-reload demo: {e}")
    
    async def run_sample_rate_demo(self):
        """Run multi-sample rate testing demo"""
        print("\n🎵 Multi-Sample Rate Testing Demo")
        print("="*40)
        
        # Create a test bot for sample rate testing
        test_bot = self.bot_manager.create_bot(
            "support",
            "sample-rate-test",
            {"voice": "coral", "temperature": 0.5}
        )
        
        await self.bot_manager.start_bot("sample-rate-test", port=5098)
        
        print("✅ Test bot created and started on port 5098")
        print("\n🧪 Test different sample rates:")
        
        sample_rates = [8000, 16000, 24000]
        for rate in sample_rates:
            print(f"\n🎵 Testing {rate}Hz:")
            print(f"python test_enhanced_bot.py --server ws://localhost:5098 --sample-rate {rate}")
        
        input("\nPress Enter to stop the test bot and continue...")
        
        await self.bot_manager.stop_bot("sample-rate-test")
        print("✅ Sample rate demo complete")
    
    def view_templates(self):
        """View available bot templates"""
        print("\n📋 AVAILABLE BOT TEMPLATES")
        print("="*40)
        
        templates = self.bot_manager.template_manager.list_templates()
        for i, template in enumerate(templates, 1):
            print(f"{i}. {template}")
        
        if templates:
            choice = input(f"\nView template details (1-{len(templates)}, or press Enter to continue): ").strip()
            if choice:
                try:
                    template_index = int(choice) - 1
                    if 0 <= template_index < len(templates):
                        template_name = templates[template_index]
                        template_config = self.bot_manager.template_manager.get_template(template_name)
                        if template_config:
                            print(f"\n📋 Template: {template_name}")
                            print(f"Type: {template_config.bot_type.value}")
                            print(f"Personality: {template_config.personality.value}")
                            print(f"Voice: {template_config.voice}")
                            print(f"Temperature: {template_config.temperature}")
                            print(f"Description: {template_config.base_instructions[:200]}...")
                except ValueError:
                    pass
    
    async def import_export_menu(self):
        """Import/Export bots menu"""
        print("\n📦 IMPORT/EXPORT BOTS")
        print("="*30)
        print("1. Export Bot Configuration")
        print("2. Import Bot Configuration") 
        print("3. Back to Main Menu")
        
        choice = input("\nSelect option (1-3): ").strip()
        
        if choice == '1':
            await self.export_bot_interactive()
        elif choice == '2':
            await self.import_bot_interactive()
    
    async def export_bot_interactive(self):
        """Export bot configuration interactively"""
        available_bots = self.bot_manager.list_available_bots()
        
        if not available_bots:
            print("No bots to export")
            return
        
        print("\nAvailable bots to export:")
        for i, bot_id in enumerate(available_bots, 1):
            print(f"  {i}. {bot_id}")
        
        choice = input("Select bot to export (number): ").strip()
        try:
            bot_index = int(choice) - 1
            if 0 <= bot_index < len(available_bots):
                bot_id = available_bots[bot_index]
                export_path = input("Export file path (default: exported_bot.json): ").strip()
                if not export_path:
                    export_path = "exported_bot.json"
                
                self.bot_manager.export_bot(bot_id, export_path)
                print(f"✅ Exported bot '{bot_id}' to '{export_path}'")
        except ValueError:
            print("❌ Invalid selection")
    
    async def import_bot_interactive(self):
        """Import bot configuration interactively"""
        import_path = input("Import file path: ").strip()
        if not import_path or not os.path.exists(import_path):
            print("❌ File not found")
            return
        
        new_bot_id = input("New bot ID (leave empty to use original): ").strip() or None
        
        try:
            imported_config = self.bot_manager.import_bot(import_path, new_bot_id)
            print(f"✅ Imported bot: {imported_config.bot_id}")
        except Exception as e:
            print(f"❌ Failed to import bot: {e}")
    
    def show_help(self):
        """Show help information"""
        print("\n📚 HELP & DOCUMENTATION")
        print("="*40)
        print("""
🤖 UNIVERSAL AI BOT LAUNCHER

This tool helps you create, customize, and manage AI bots for various purposes:

BOT TYPES:
• Sales & Lead Generation - For converting prospects into customers
• Customer Support - For helping existing customers with issues
• Service Collection - For payment reminders and debt recovery
• Appointment Booking - For scheduling meetings and reservations
• Survey & Feedback - For collecting user opinions and data
• Custom - For specialized use cases with custom configuration

KEY FEATURES:
• Multi-sample rate support (8kHz, 16kHz, 24kHz) for Exotel integration
• Hot-reload configuration changes without restarting bots
• Variable chunk processing for optimal audio quality
• Multiple voice options and personality types
• Template system for quick bot creation
• Import/Export for sharing configurations

TESTING:
Once a bot is created and started, test it with:
python test_enhanced_bot.py --server ws://localhost:PORT --interactive

CONFIGURATION FILES:
• Bot configurations are stored in active_bots/ directory
• Templates are stored in bot_templates/ directory
• Modify JSON files directly for advanced customization

EXOTEL INTEGRATION:
Your bots support Exotel WebSocket endpoints with sample rate parameters:
• ws://your-domain.com/?sample-rate=8000
• ws://your-domain.com/?sample-rate=16000  
• ws://your-domain.com/?sample-rate=24000

For more detailed documentation, see DEVELOPER_GUIDE.md
        """)
        
        input("\nPress Enter to continue...")
    
    async def shutdown_all_bots(self):
        """Shutdown all active bots"""
        active_bots = self.bot_manager.list_active_bots()
        for bot_id in active_bots:
            try:
                await self.bot_manager.stop_bot(bot_id)
                print(f"  Stopped {bot_id}")
            except Exception as e:
                print(f"  ❌ Failed to stop {bot_id}: {e}")
        
        self.bot_manager.shutdown()

async def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Universal AI Bot Launcher")
    parser.add_argument("--interactive", action="store_true", help="Interactive mode")
    parser.add_argument("--demo", action="store_true", help="Run demo scenarios")
    parser.add_argument("--quick-start", action="store_true", help="Show quick start guide")
    
    args = parser.parse_args()
    
    launcher = BotLauncher()
    
    if args.interactive or len(sys.argv) == 1:
        await launcher.interactive_mode()
    elif args.demo:
        await launcher.demo_scenarios_menu()
    elif args.quick_start:
        launcher.show_help()
    else:
        parser.print_help()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Exiting...")
    except Exception as e:
        print(f"❌ Error: {e}") 