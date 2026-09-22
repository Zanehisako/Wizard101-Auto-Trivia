import os
import platform
import subprocess
import re
import undetected_chromedriver as uc
from threading import Barrier, Thread
import time as t
from selenium.common.exceptions import *
from selenium.webdriver.chrome.options import Options
import shutil
import pathlib
from stealth import Stealth
from fake_useragent import UserAgent

class Threadium():
    """A Python module that makes implementing threads with selenium chrome easier."""
    def __init__(self, threads=0):
        self.user_accounts = {}
        self.threads = threads
        try:
            self.user_agent = UserAgent().chrome
        except Exception:
            self.user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.script_directory = pathlib.Path().absolute()
        self.chrome_options = Options()
        self.random = 'random'
        if platform.system() == "Windows" and os.path.exists('chromedriver.exe'):
            self.chrome_driver_path = os.path.abspath('chromedriver.exe')
        else:
            self.chrome_driver_path = None

        # Load Buster extension if available
        buster_path = self.get_buster_extension_path()
        if buster_path:
            self.chrome_options.add_argument(f"--load-extension={buster_path}")
            print(f"Buster extension loaded from: {buster_path}")

    def get_buster_extension_path(self):
        """Locates the Buster extension in local project or user's Chrome directory."""
        # 1. Project local directory
        local_ext = os.path.join(str(self.script_directory), "extensions", "buster")
        if os.path.exists(os.path.join(local_ext, "manifest.json")):
            return os.path.abspath(local_ext)

        # 2. macOS Chrome Default extensions
        mac_ext_base = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Extensions/mpbjkejclgfgadiemmefgebjfooflfhl")
        if os.path.exists(mac_ext_base):
            versions = [os.path.join(mac_ext_base, d) for d in os.listdir(mac_ext_base) if os.path.isdir(os.path.join(mac_ext_base, d))]
            if versions:
                return sorted(versions)[-1]

        # 3. Windows Chrome Default extensions
        win_ext_base = os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data\Default\Extensions\mpbjkejclgfgadiemmefgebjfooflfhl")
        if os.path.exists(win_ext_base):
            versions = [os.path.join(win_ext_base, d) for d in os.listdir(win_ext_base) if os.path.isdir(os.path.join(win_ext_base, d))]
            if versions:
                return sorted(versions)[-1]

        return None

    def add_user_accounts(self):
        """Gets all user accounts"""
        accounts_path = os.path.join('text_files', 'accounts.txt')
        if os.path.exists(accounts_path):
            with open(accounts_path, 'r', encoding='utf-8') as accounts:
                for i in accounts.readlines():
                    line = i.strip()
                    if line and not line.startswith('#'):
                        parts = line.split(' ')
                        if len(parts) >= 2:
                            self.user_accounts[parts[0]] = parts[1]

    def create_user_data_dir(self, funnel):
        """Creates a chrome directory
        
        funnel -> tuple/list [path to chrome user data directory, profile name]
        """
        try:
            user_data_path = os.path.abspath(os.path.join(self.script_directory, funnel[0]))
            profile_name = funnel[1] if len(funnel) > 1 else "Default"
            target_profile = os.path.join(user_data_path, profile_name)

            # Auto-install Buster and profile settings if not yet present
            template_path = os.path.join(str(self.script_directory), "chrome_profile_data")
            if not os.path.exists(target_profile) and os.path.exists(template_path):
                print(f"Auto-installing Buster extension into new profile for {profile_name}...")
                os.makedirs(os.path.dirname(target_profile), exist_ok=True)
                shutil.copytree(template_path, target_profile)

            self.chrome_options.add_argument(f"--user-data-dir={user_data_path}")
        except Exception as e:
            raise Exception(f"Failure! The following error has occured while attempting to make a chrome profile: {e}")

    def create_profile_dir(self, funnel=None):
        """Creates a chrome profile

        funnel -> tuple/list [path to chrome user data directory, profile name]
        """
        try:
            self.chrome_options.add_argument(f"--profile-directory={funnel[1]}")
        except Exception as e:
            raise Exception(f"Failure! The following error has occured while attempting to make a chrome profile: {e}")

    def patch_profile_dirs(self, src="chrome_profile_data", dir="user-data-dir"):
        """Replaces a dir of chrome profiles with a src profile"""
        self.add_user_accounts()
        try:
            total = len(self.user_accounts)
            for idx, key in enumerate(self.user_accounts.keys(), start=1):
                print(f"Patching the user {key}'s chrome profile...")
                profile_path = os.path.join(dir, f"{key}-dir", f"{key}-user-data")
                if os.path.exists(profile_path):
                    shutil.rmtree(profile_path)
                if os.path.exists(src):
                    shutil.copytree(src, profile_path)
                print(f"{key}'s chrome profile was successfully patched!")
                progress = round((idx / total) * 100, 0) if total > 0 else 100
                print(f"Progress:{progress}%")
        except Exception as e:
            raise Exception(f"Failure! The following error has occured while attempting to patch the chrome profiles: {e}")

    def set_user_agent(self, user_agent=None):
        """Sets the user agent"""
        if user_agent is not None and user_agent != self.random:
            Stealth().create_useragent()
        elif user_agent is not None and user_agent == self.random:
            Stealth().create_random_useragent()

    def get_chrome_major_version(self):
        """Detects the major version of the installed Google Chrome."""
        try:
            exe = uc.find_chrome_executable()
            if not exe:
                return None

            if platform.system() == "Darwin":
                try:
                    out = subprocess.check_output(
                        ["defaults", "read", "/Applications/Google Chrome.app/Contents/Info.plist", "CFBundleShortVersionString"],
                        text=True, stderr=subprocess.DEVNULL
                    ).strip()
                    m = re.search(r"^(\d+)", out)
                    if m:
                        return int(m.group(1))
                except Exception:
                    pass

            if platform.system() == "Windows":
                try:
                    cmd = f'(Get-Item "{exe}").VersionInfo.ProductVersion'
                    out = subprocess.check_output(["powershell", "-Command", cmd], text=True, stderr=subprocess.DEVNULL).strip()
                    m = re.search(r"(\d+)", out)
                    if m:
                        return int(m.group(1))
                except Exception:
                    pass

            out = subprocess.check_output([exe, "--version"], text=True, stderr=subprocess.DEVNULL).strip()
            m = re.search(r"(\d+)\.", out)
            if m:
                return int(m.group(1))
        except Exception as e:
            print(f"Could not auto-detect Chrome version: {e}")
        return None

    def start_all(self, args, stealth=False, profile_dir=None, user_agent=None, single_target=None):
        """Starts all the Chrome webdriver threads."""
        self.chrome_options.add_argument("--window-size=1800,1800")
        self.chrome_options.add_argument("--no-first-run")
        self.chrome_options.add_argument("--no-default-browser-check")
        if single_target is not None:
            for _ in range(self.threads):
                if profile_dir is not None:
                    self.create_user_data_dir(funnel=profile_dir)
                    self.create_profile_dir(funnel=profile_dir)

                driver_kwargs = {"options": self.chrome_options}
                if self.chrome_driver_path and platform.system() == "Windows":
                    driver_kwargs["driver_executable_path"] = self.chrome_driver_path

                chrome_version = self.get_chrome_major_version()
                if chrome_version:
                    driver_kwargs["version_main"] = chrome_version
                    print(f"Detected Chrome major version: {chrome_version}")

                try:
                    driver = uc.Chrome(**driver_kwargs)
                except SessionNotCreatedException as e:
                    m = re.search(r"Current browser version is (\d+)", str(e))
                    if m:
                        v = int(m.group(1))
                        print(f"Retrying with detected browser version {v}...")
                        driver_kwargs["version_main"] = v
                        driver = uc.Chrome(**driver_kwargs)
                    else:
                        raise e

                th = Thread(target=single_target, args=args + (driver,))
                th.start()
                th.join()
