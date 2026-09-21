from selenium_stealth import stealth
from fake_useragent import UserAgent
import platform

# This is a class that contains all the functions that are used to make the chrome driver stealthy
class Stealth():
    def __init__(self, driver=None):
        self.stealth_driver = driver
        try:
            self.user_agent = UserAgent(browsers=['chrome'])
            self.user_agent_random = UserAgent(browsers=["chrome", "edge", "firefox", "safari", "opera"])
        except Exception:
            self.user_agent = None
            self.user_agent_random = None

    def stealth(self):
        # This function makes the chrome driver stealthy
        is_mac = platform.system() == "Darwin"
        plat = "MacIntel" if is_mac else "Win32"
        vendor = "Apple Computer, Inc." if is_mac else "Google Inc."
        stealth(self.stealth_driver,
            languages=["en-US", "en"],
            vendor=vendor,
            platform=plat,
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        return self.stealth_driver

    def create_useragent(self):
        # This function creates a user agent for the chrome driver
        if self.user_agent:
            return self.user_agent
        return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def create_random_useragent(self):
        # This function creates a random user agent for the chrome driver
        if self.user_agent_random:
            return self.user_agent_random.random
        return "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"