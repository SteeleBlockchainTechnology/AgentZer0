""" 
Discord bot module for the AgentZer0 integration. 
""" 
import discord 
from discord.ext import commands 
import logging 

logger = logging.getLogger(__name__) 

class DiscordBot: 
    """Discord bot implementation.""" 
    
    def __init__(self, token, prefix="!"): 
        """Initialize the Discord bot. 
        
        Args: 
            token (str): Discord bot token. 
            prefix (str): Command prefix for the bot. 
        """ 
        self.token = token 
        self.prefix = prefix 
        
        # Set up intents (permissions) 
        intents = discord.Intents.default() 
        intents.message_content = True 
        intents.members = True 
        intents.guilds = True 
        
        # Create bot instance 
        self.bot = commands.Bot(command_prefix=self.prefix, intents=intents) 
        
        # Store message handlers 
        self.message_handlers = [] 
    
    def add_message_handler(self, handler): 
        """Add a message handler function. 
        
        Args: 
            handler (callable): Function that takes a message and returns a coroutine. 
        """ 
        self.message_handlers.append(handler) 
    
    async def setup_events(self): 
        """Set up bot events.""" 
        
        @self.bot.event 
        async def on_ready(): 
            """Event fired when bot is ready.""" 
            logger.info(f"Logged in as {self.bot.user.name} ({self.bot.user.id})") 
            logger.info(f"Connected to {len(self.bot.guilds)} guilds") 
            
            # Set bot status 
            await self.bot.change_presence( 
                activity=discord.Activity( 
                    type=discord.ActivityType.listening, 
                    name=f"{self.prefix}help" 
                ) 
            ) 
        
        @self.bot.event 
        async def on_message(message): 
            """Event fired when a message is received.""" 
            # Ignore messages from bots to prevent loops 
            if message.author.bot: 
                return 
            
            # Process commands 
            await self.bot.process_commands(message) 
            
            # If message doesn't start with command prefix, process as conversation 
            if not message.content.startswith(self.prefix): 
                for handler in self.message_handlers: 
                    await handler(message) 
    
    def get_channel(self, channel_id): 
        """Get a Discord channel by ID. 
        
        Args: 
            channel_id (int): Discord channel ID. 
            
        Returns: 
            discord.Channel: Channel object or None if not found. 
        """ 
        return self.bot.get_channel(int(channel_id)) 
    
    def run(self): 
        """Run the Discord bot.""" 
        logger.info("Starting Discord bot...") 
        self.bot.run(self.token)