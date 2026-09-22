from trivia_qa import wizard101_trivia_questions_and_answers as wt
from answers import Wizard101_Trivia as answers_dict
import difflib
import os
import time as t
from selenium.common.exceptions import *
import dill
from functions import WebDriver
from threadium import *
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import pathlib
import requests
from bs4 import BeautifulSoup
from random import choice
from threadium import Threadium

class AutoTrivia():
    """Main module that automates the trivia"""
    def __init__(self):
        self.user_account = {}
        self.chromewebdriver = WebDriver()
        self.script_directory = pathlib.Path().absolute()
        self.chrome_driver_path = None
        self.has_quizes = True
    
    def setup(self):
        """Opens a unique driver per account and adds arguments"""
        if not self.user_account:
            print("No accounts found in text_files/accounts.txt. Please add accounts in 'username password' format.")
            return

        print(f"\n==========================================")
        print(f"Loaded {len(self.user_account)} account(s): {', '.join(self.user_account.keys())}")
        print(f"==========================================\n")

        for key, value in self.user_account.items():
            print(f"\n==========================================")
            print(f"Starting thread for user: {key}...")
            print(f"==========================================")
            th = Thread(target=self.process_account, args=(key, value))
            th.start()
            th.join()  # Wait for the thread to complete before moving on to the next account
            print(f"\nSuccess! {key}'s thread is complete!")
        print("\nSuccess! All accounts have successfully completed the trivia!")

    def process_account(self, key, value):
        """Processes a single account"""
        th = Threadium(1)
        th.start_all(
            args=(key, value),
            single_target=self.run,
            profile_dir=[os.path.join("user-data-dir", f"{key}-dir"), f"{key}-user-data"],
        )
        
    def proxy_generator(self):
        return None    
        
    def run(self, user, passwrd, driver):
        # Merge question & answer datasets for maximum accuracy
        qa_dict = {**wt, **answers_dict}

        quizes = [
            "Pirate101 Valencia Trivia", 
            "Wizard101 Adventuring Trivia", 
            "Wizard101 Conjuring Trivia", 
            "Wizard101 Magical Trivia", 
            "Wizard101 Marleybone Trivia", 
            "Wizard101 Mystical Trivia", 
            "Wizard101 Spellbinding Trivia", 
            "Wizard101 Spells Trivia", 
            "Wizard101 Wizard City Trivia", 
            "Wizard101 Zafaria Trivia"
        ]

        driver.get("https://www.wizard101.com/quiz/trivia/game/kingsisle-trivia")

        # Switch to the tab with the Wizard101 website
        for handle in driver.window_handles:
            driver.switch_to.window(handle)
            if any(name in driver.title for name in ["Wizard101", "KingsIsle", "Trivia"]):
                break
        driver.delete_all_cookies()
        driver.refresh()
        t.sleep(4)
        self.chromewebdriver.clickCookies(driver=driver)

        # Login elements
        username_button = '//*[@id="loginUserName"]'
        password_button = '//*[@id="loginPassword"]'
        login_button = '//*[@id="wizardLoginButton"]//input[@type="submit" or @value="Login"]'

        # Wait for the username button to appear
        if driver.find_elements(By.XPATH, username_button):
            try:
                print(f"Logging in user: {user}...")
                username = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, username_button)))
                username.clear()
                username.send_keys(user)
                password = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.XPATH, password_button)))
                password.clear()
                password.send_keys(passwrd)
            
                # Click the login button
                login_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.XPATH, login_button)))
                login_btn.click()
                t.sleep(4)

                self.chromewebdriver.clickCookies(driver=driver)
                self.chromewebdriver.solveVerification(driver=driver)
                print(f"Login step completed for {user}!")
            except Exception as e:
                print(f"Error while logging in: {e}")
        self.chromewebdriver.clickCookies(driver=driver)

        # Track completed quizzes and status
        completed_quizes = set()
        daily_limit_reached = False
        quizzes_claimed = 0

        print(f"\nStarting trivia automation for {user}. Aiming to complete all quizzes until daily limit (100 crowns)...")

        # Multi-pass loop: up to 2 passes over the quiz pool in case any need retry
        for pass_num in range(1, 3):
            if daily_limit_reached or quizzes_claimed >= 10:
                break

            quizes_to_run = [q for q in quizes if q not in completed_quizes]
            if not quizes_to_run:
                break

            if pass_num > 1:
                print(f"\n--- Starting Pass {pass_num} for remaining {len(quizes_to_run)} quizzes ---")

            for quiz_idx, quiz_name in enumerate(quizes_to_run, start=1):
                if daily_limit_reached or quizzes_claimed >= 10:
                    break

                slug = quiz_name.lower().replace(" ", "-")
                quiz_url = f"https://www.wizard101.com/quiz/trivia/game/{slug}"
                print(f"\n==========================================")
                print(f"[{quiz_idx}/{len(quizes_to_run)}] Starting: {quiz_name}")
                print(f"==========================================")

                driver.get(quiz_url)
                t.sleep(3)
                self.chromewebdriver.clickCookies(driver=driver)

                # Check if daily limit message is displayed on page
                try:
                    body_text = driver.find_element(By.TAG_NAME, 'body').text.lower()
                    if any(msg in body_text for msg in ["maximum crowns you can earn today", "already earned your crowns for today", "already earned 100 crowns"]):
                        print("KingsIsle indicates the daily crowns limit (100 crowns) has already been reached today!")
                        daily_limit_reached = True
                        break
                except Exception:
                    pass

                # Check if this quiz was already completed today
                questions_check = driver.find_elements(By.CLASS_NAME, 'quizQuestion')
                another_quiz_btn = driver.find_elements(
                    By.XPATH,
                    '//*[@id="quizFormComponent"]//*[contains(text(), "TAKE ANOTHER QUIZ") or contains(text(), "YOU FINISHED")]'
                )
                if another_quiz_btn and (not questions_check or not questions_check[0].is_displayed()):
                    print(f"Quiz '{quiz_name}' appears already completed today. Moving to next...")
                    completed_quizes.add(quiz_name)
                    continue

                # Wait for first question to appear
                try:
                    WebDriverWait(driver, 12).until(
                        EC.presence_of_element_located((By.CLASS_NAME, 'quizQuestion'))
                    )
                except TimeoutException:
                    print(f"Could not load questions for '{quiz_name}'. Moving to next...")
                    continue

                # Answer questions for this quiz (up to 15 questions)
                last_q_text = ""
                same_q_count = 0

                for step in range(1, 16):
                    q_els = driver.find_elements(By.CLASS_NAME, 'quizQuestion')
                    if not q_els or not q_els[0].is_displayed():
                        # No more questions visible; quiz finished!
                        break

                    q_text = q_els[0].text.strip()
                    if not q_text:
                        t.sleep(1)
                        q_els = driver.find_elements(By.CLASS_NAME, 'quizQuestion')
                        if not q_els or not q_els[0].is_displayed():
                            break
                        q_text = q_els[0].text.strip()
                        if not q_text:
                            break

                    if q_text == last_q_text:
                        same_q_count += 1
                        if same_q_count >= 3:
                            print("  Question stuck, submitting again...")
                            same_q_count = 0
                        else:
                            t.sleep(1)
                            continue
                    else:
                        same_q_count = 0
                        last_q_text = q_text

                    print(f"  Q{step}: {q_text[:65]}...")

                    # Match target answer
                    target_ans = ""
                    matches = difflib.get_close_matches(q_text, qa_dict.keys(), n=1, cutoff=0.5)
                    if matches:
                        target_ans = qa_dict[matches[0]]

                    # Extract candidate choices using JavaScript
                    choice_texts = driver.execute_script("""
                        return Array.from(document.querySelectorAll('.answersContainer .answer')).map(function(el) {
                            return el.textContent.trim();
                        });
                    """) or []

                    ans_idx = 0
                    if target_ans and choice_texts:
                        clean_target = target_ans.strip(" .?!'\"").lower()
                        clean_choices = [c.strip(" .?!'\"").lower() for c in choice_texts]

                        found = False
                        for idx, c in enumerate(clean_choices):
                            if c == clean_target:
                                ans_idx = idx
                                found = True
                                break
                        if not found:
                            for idx, c in enumerate(clean_choices):
                                if clean_target in c or c in clean_target:
                                    ans_idx = idx
                                    found = True
                                    break
                        if not found:
                            m = difflib.get_close_matches(clean_target, clean_choices, n=1, cutoff=0.4)
                            if m:
                                ans_idx = clean_choices.index(m[0])

                    # Select answer and submit via updateQuiz()
                    driver.execute_script("""
                        var nodes = document.getElementsByName('answers');
                        if (nodes.length > arguments[0]) {
                            nodes[arguments[0]].checked = true;
                            if (typeof updateQuiz === 'function') {
                                updateQuiz();
                            } else {
                                var btn = document.getElementById('nextQuestion');
                                if (btn) btn.click();
                            }
                        }
                    """, ans_idx)

                    t.sleep(1.8)

                print(f"All questions answered for '{quiz_name}'! Looking for CLAIM YOUR REWARD button...")
                t.sleep(2)
                self.chromewebdriver.clickCookies(driver=driver)

                # Click CLAIM YOUR REWARD or See Your Score to open the reward popup
                claim_btns = driver.find_elements(
                    By.XPATH,
                    '//*[@id="quizFormComponent"]//a[contains(@class, "kiaccountsbutton") or contains(text(), "CLAIM YOUR REWARD") or contains(text(), "See Your Score")]'
                )
                if claim_btns:
                    print("Clicking CLAIM YOUR REWARD button to open reward popup...")
                    try:
                        driver.execute_script("arguments[0].click();", claim_btns[-1])
                    except Exception:
                        try:
                            claim_btns[-1].click()
                        except Exception:
                            pass
                    t.sleep(3)

                # Check if daily limit reached
                try:
                    body_text = driver.find_element(By.TAG_NAME, 'body').text.lower()
                    if any(msg in body_text for msg in ["maximum crowns you can earn today", "already earned your crowns for today", "already earned 100 crowns"]):
                        print("Daily crowns limit reached!")
                        daily_limit_reached = True
                        completed_quizes.add(quiz_name)
                        break
                except Exception:
                    pass

                # Wait up to 8 seconds for reward popup (jPopFrame_content)
                popup_visible = False
                for _ in range(8):
                    jpop = driver.find_elements(By.ID, "jPopFrame_content")
                    if jpop and jpop[0].is_displayed():
                        popup_visible = True
                        break
                    t.sleep(1)

                if popup_visible:
                    status = self.chromewebdriver.solveCaptcha(driver=driver)
                    if status == "DAILY_LIMIT":
                        print("Daily crowns limit reached according to popup!")
                        daily_limit_reached = True
                        completed_quizes.add(quiz_name)
                        break
                    elif status == "SUCCESS":
                        quizzes_claimed += 1
                        completed_quizes.add(quiz_name)
                        print(f"Quiz '{quiz_name}' successfully completed! ({quizzes_claimed}/10 claimed today)")
                    else:
                        completed_quizes.add(quiz_name)
                        print(f"Quiz '{quiz_name}' completed with status: {status}")
                else:
                    completed_quizes.add(quiz_name)
                    print(f"Quiz '{quiz_name}' completed without popup (already claimed or score under 75%).")

                t.sleep(2)

        if daily_limit_reached or quizzes_claimed >= 10:
            print(f"\nCompleted all quizzes possible! Daily maximum crowns reached for {user}.")
        else:
            print(f"\nFinished iterating through all quizzes for {user}. Total quizzes claimed this session: {quizzes_claimed}.")

        driver.quit()
    # continue with your code
if __name__ == "__main__":
    # initialize the class and run the setup function to start the script 
    at = AutoTrivia()
    accounts_file = os.path.join('text_files', 'accounts.txt')
    if os.path.exists(accounts_file):
        with open(accounts_file, 'r', encoding='utf-8') as accounts:
            for idx, i in enumerate(accounts.readlines(), 1):
                line = i.strip()
                if not line or line.startswith('#'):
                    continue
                if ':' in line:
                    parts = [p.strip() for p in line.split(':', 1)]
                else:
                    parts = line.split()
                if len(parts) >= 2:
                    at.user_account[parts[0]] = parts[1]
                else:
                    print(f"Warning: Line {idx} in accounts.txt could not be parsed: '{line}' (expected 'username password' or 'username:password')")
    else:
        print(f"Accounts file not found at: {accounts_file}")
    at.setup()
