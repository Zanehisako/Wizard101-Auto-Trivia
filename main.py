from trivia_qa import wizard101_trivia_questions_and_answers as wt
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
        for key, value in self.user_account.items():
            print(f"Starting thread for the user: {key}...")
            th = Thread(target=self.process_account, args=(key, value))
            th.start()
            th.join()  # Wait for the thread to complete before moving on to the next account
            print(f"Success! {key}'s thread is complete!")
        print("Success! All accounts have successfully completed the trivia!")

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

        # All the button xpath's/frames/clickables/etc. that are used in the script:
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

        # Loop through each quiz directly
        for quiz_idx, quiz_name in enumerate(quizes, start=1):
            slug = quiz_name.lower().replace(" ", "-")
            quiz_url = f"https://www.wizard101.com/quiz/trivia/game/{slug}"
            print(f"\n==========================================")
            print(f"[{quiz_idx}/{len(quizes)}] Starting: {quiz_name}")
            print(f"==========================================")

            driver.get(quiz_url)
            t.sleep(3)
            self.chromewebdriver.clickCookies(driver=driver)

            # Check if quiz questions exist or if already completed
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CLASS_NAME, 'quizQuestion'))
                )
            except TimeoutException:
                if driver.find_elements(By.XPATH, '//*[@id="quizFormComponent"]//a[contains(text(), "TAKE ANOTHER QUIZ")]'):
                    print(f"Quiz '{quiz_name}' appears already completed today. Moving to next...")
                else:
                    print(f"Quiz '{quiz_name}' questions could not be loaded. Moving to next...")
                continue

            # Answer questions for this quiz
            consecutive_errors = 0
            quiz_finished = False

            while not quiz_finished and consecutive_errors < 5:
                try:
                    # Check if 'Get Results' or continue button is visible
                    results_candidates = driver.find_elements(
                        By.XPATH,
                        '//*[@id="quizFormComponent"]//a[contains(text(), "Results") or @id="bp_continue"] | '
                        '//*[@id="quizFormComponent"]/div[3]/div[3]/a | '
                        '//*[@id="bp_continue"]'
                    )

                    if results_candidates:
                        print("Quiz questions answered! Submitting for results...")
                        try:
                            results_candidates[0].click()
                            t.sleep(3)
                        except Exception:
                            pass

                        # If reward popup appears, click submit / claim
                        jpop_frames = driver.find_elements(By.ID, "jPopFrame_content")
                        if jpop_frames and jpop_frames[0].is_displayed():
                            try:
                                driver.switch_to.frame(jpop_frames[0])
                                claim_btn = driver.find_elements(By.XPATH, '//*[@id="submit"] | //input[@type="submit"]')
                                if claim_btn:
                                    claim_btn[0].click()
                                    t.sleep(2)
                                driver.switch_to.default_content()
                            except Exception:
                                driver.switch_to.default_content()

                        # Solve completion captcha
                        self.chromewebdriver.solveCaptcha(driver=driver)

                        # Update crowns
                        if os.path.exists('data.pkl') and os.stat('data.pkl').st_size != 0:
                            try:
                                with open('data.pkl', 'rb') as f:
                                    self.chromewebdriver.crowns_earned = dill.load(f)
                            except Exception:
                                pass
                        self.chromewebdriver.crowns_earned += 10
                        print(f"Received 10 crowns! Lifetime total: {self.chromewebdriver.crowns_earned} crowns!")
                        try:
                            self.chromewebdriver.dump(self.chromewebdriver.crowns_earned)
                        except Exception as e:
                            print(f"Error saving crowns: {e}")

                        quiz_finished = True
                        break

                    # Wait for the question to be visible
                    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, 'quizQuestion')))
                    question_el = driver.find_element(By.CLASS_NAME, 'quizQuestion')
                    question_text = question_el.text

                    # Find closest matching question
                    parsed_question = difflib.get_close_matches(question_text, wt.keys())
                    if parsed_question:
                        answer = wt.get(parsed_question[0])
                    else:
                        answer = ""

                    # Wait for nextQuestion button to be clickable
                    WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'nextQuestion')))

                    # Collect candidate answer choices
                    answers = []
                    for a_el in driver.find_elements(By.CLASS_NAME, "answerText"):
                        clean_text = a_el.text.replace('', '')
                        answers.append(clean_text)

                    # Match closest answer
                    parsed_answer = difflib.get_close_matches(answer, answers)
                    if parsed_answer:
                        ans_idx = answers.index(parsed_answer[0])
                    else:
                        ans_idx = 0

                    # Click the matched answer box
                    answer_boxes = driver.find_elements(By.CLASS_NAME, "answerBox")
                    if ans_idx < len(answer_boxes):
                        answer_boxes[ans_idx].click()
                        t.sleep(0.5)

                    # Click next question button
                    next_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, 'nextQuestion')))
                    next_btn.click()
                    t.sleep(2)
                    consecutive_errors = 0

                except Exception as e:
                    consecutive_errors += 1
                    t.sleep(2)
                    # Check if results button appeared during error
                    check_results = driver.find_elements(
                        By.XPATH,
                        '//*[@id="quizFormComponent"]//a[contains(text(), "Results") or @id="bp_continue"] | '
                        '//*[@id="quizFormComponent"]/div[3]/div[3]/a | '
                        '//*[@id="bp_continue"]'
                    )
                    if check_results:
                        continue
                    print(f"Retrying question step ({consecutive_errors}/5)...")

            print(f"Finished quiz {quiz_idx}/{len(quizes)}: {quiz_name}!")
            t.sleep(2)

        print(f"\nAll quizes have been completed for {user}'s account! Now moving on to the next account...")
        driver.quit()
    # continue with your code
if __name__ == "__main__":
    # initialize the class and run the setup function to start the script 
    at = AutoTrivia()
    accounts_file = os.path.join('text_files', 'accounts.txt')
    if os.path.exists(accounts_file):
        with open(accounts_file, 'r', encoding='utf-8') as accounts:
            for i in accounts.readlines():
                line = i.strip()
                if line and not line.startswith('#'):
                    parts = line.split(' ')
                    if len(parts) >= 2:
                        at.user_account[parts[0]] = parts[1]
    at.setup()
