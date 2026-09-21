from threadium import Threadium
import time as t
import os

# The class below is used to patch all the chrome profiles
class PatchHandler:
    def __init__(self, accounts):
        self.accounts = accounts
        self.start_time = t.time()
    def patch(self):
        """Patches all the chrome profiles"""
        # patches all the chrome profiles
        self.start_time
        print(f"Patching {self.accounts} chrome profile(s), estimated time is {self.accounts*2} seconds(s); please wait...")
        try:
            Threadium().patch_profile_dirs(src="chrome_profile_data", dir="user-data-dir")
            print(f"Success! All {self.accounts} chrome profile(s) were successfully patched! Finished in {round(t.time() - self.start_time, 0)} seconds!")
        except Exception as e: 
            raise RuntimeError(f"Failure! The following exception occurred while attempting to patch chrome profile(s) (most likely due to user-data being left in the chrome profile): {e}")
if __name__ == "__main__":
    #NOTE: VERY IMPORTANT: Make sure ANY user-data profiles are removed PRIOR to using the PatchHandler class in the chrome_profile directory!!!
    #NOTE: WHEN USING A CHROME FILE'S CONTENT FOR THE chrome_profile directory, get the contents out of the the user_data_dir folder!!! Not the default folder!!!
    #NOTE: the following line of code is for creating a chrome profile for each user account
    accounts_file = os.path.join('text_files', 'accounts.txt')
    num_of_accounts = 0
    if os.path.exists(accounts_file):
        with open(accounts_file, 'r', encoding='utf-8') as f:
            usernames = [line for line in f.readlines() if line.strip() and not line.strip().startswith('#')]
            num_of_accounts = len(usernames)
    PatchHandler(num_of_accounts).patch()
        
