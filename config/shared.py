from multiprocessing import Manager

# Create a single Manager instance
manager = Manager()

# Shared dictionary for bot statistics
bot_stats = manager.dict()
