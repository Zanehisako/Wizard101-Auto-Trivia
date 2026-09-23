import time as t
import dill
import os
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *

class WebDriver():
    def __init__(self): 
        self.crowns_earned = 0

    def dump(self, obj):
        '''
        Dumps the data to a file.
        '''
        os.makedirs("text_files", exist_ok=True)
        with open(os.path.join("text_files", "data.txt"), 'w', encoding='utf-8') as f:
            f.write(f'Total Lifetime Crowns Earned: {obj}\n')
        with open('data.pkl', 'wb') as f:
            dill.dump(obj, f)

    def retry_captcha(self, driver):
        """Retries the captcha if it fails."""
        try:
            driver.switch_to.default_content()
            retries = driver.find_elements(By.XPATH, '//*[@id="quizFormComponent"]//a')
            if retries:
                retries[0].click()
                t.sleep(2)
        except Exception:
            pass

    def solveCaptcha(self, driver): 
        '''
        Solves the captcha in the reward popup, clicks submit, and confirms reward was claimed.
        '''
        print("Handling quiz completion reward popup & captcha...")
        t.sleep(2)
        jpop_list = driver.find_elements(By.ID, "jPopFrame_content")
        if not jpop_list or not jpop_list[0].is_displayed():
            return "NO_POPUP"

        limit_phrases = [
            "exceeded the number of quizzes allowed today",
            "come back tomorrow",
            "maximum crowns",
            "already earned",
            "daily limit",
            "100 crowns",
        ]

        try:
            driver.switch_to.frame(jpop_list[0])
            
            # 1. Check for daily crowns/quiz limit inside the popup
            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                if any(x in body_text for x in limit_phrases):
                    print("Daily crown / quiz limit detected in reward popup!")
                    driver.switch_to.default_content()
                    return "DAILY_LIMIT"
            except Exception:
                pass

            # 2. Dismiss cookie banner inside popup if present
            try:
                c_btn = driver.find_elements(By.XPATH, '//button[contains(@id, "accept") or contains(@id, "onetrust")]')
                if c_btn and c_btn[0].is_displayed():
                    c_btn[0].click()
                    t.sleep(1)
            except Exception:
                pass

            # 3. Locate reCAPTCHA anchor and click checkbox if present
            anchor_found = False
            for _ in range(5):
                anchors = driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="recaptcha/api2/anchor"]')
                if anchors:
                    anchor_found = True
                    try:
                        driver.switch_to.frame(anchors[0])
                        anchor = WebDriverWait(driver, 3).until(EC.element_to_be_clickable((By.ID, "recaptcha-anchor")))
                        if anchor.get_attribute("aria-checked") != "true":
                            anchor.click()
                            print("Clicked reCAPTCHA checkbox...")
                            t.sleep(2)
                    except Exception:
                        pass
                    driver.switch_to.default_content()
                    driver.switch_to.frame(driver.find_element(By.ID, "jPopFrame_content"))
                    break
                t.sleep(1)

            # 4. If reCAPTCHA present, wait and solve challenge with Buster
            if anchor_found:
                print("Waiting for captcha challenge to be solved...")
                start_time = t.time()
                while t.time() - start_time < 60:
                    try:
                        # Check if anchor is already checked
                        driver.switch_to.default_content()
                        driver.switch_to.frame(driver.find_element(By.ID, "jPopFrame_content"))
                        anchors = driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="recaptcha/api2/anchor"]')
                        if anchors:
                            driver.switch_to.frame(anchors[0])
                            if driver.find_element(By.ID, "recaptcha-anchor").get_attribute("aria-checked") == "true":
                                print("Quiz captcha successfully verified!")
                                break

                        # Check for challenge bframe (inside jPop or default content)
                        driver.switch_to.default_content()
                        driver.switch_to.frame(driver.find_element(By.ID, "jPopFrame_content"))
                        bframes = driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="recaptcha/api2/bframe"]')
                        if not bframes:
                            driver.switch_to.default_content()
                            bframes = driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="recaptcha/api2/bframe"]')

                        if bframes and bframes[0].is_displayed():
                            driver.switch_to.frame(bframes[0])
                            buster_btns = driver.find_elements(By.CSS_SELECTOR, '#solver-button, .help-button-holder, button[id*="solver"]')
                            if buster_btns and buster_btns[0].is_displayed() and buster_btns[0].is_enabled():
                                print("Buster extension detected! Clicking auto-solve...")
                                buster_btns[0].click()
                                t.sleep(4)
                    except Exception:
                        pass
                    t.sleep(1.5)

            # 5. Switch to popup frame and click submit / claim button
            driver.switch_to.default_content()
            jpop = driver.find_elements(By.ID, "jPopFrame_content")
            if jpop and jpop[0].is_displayed():
                driver.switch_to.frame(jpop[0])
                claim_btns = driver.find_elements(
                    By.XPATH,
                    '//*[@id="submit"] | //input[@id="submit"] | //a[contains(@class, "buttonsubmit")] | //input[@type="submit"]'
                )
                if claim_btns:
                    try:
                        driver.execute_script("arguments[0].click();", claim_btns[0])
                        print("Clicked submit to claim 10 crowns!")
                    except Exception:
                        try:
                            claim_btns[0].click()
                            print("Clicked submit to claim 10 crowns!")
                        except Exception as e:
                            print(f"Could not click claim button: {e}")

                # 6. Wait for reward response and verify confirmation
                reward_confirmed = False
                for _ in range(8):
                    t.sleep(1.5)
                    try:
                        body_text = driver.find_element(By.TAG_NAME, "body").text.lower()
                        if any(x in body_text for x in limit_phrases):
                            print("Daily limit reached according to popup confirmation!")
                            driver.switch_to.default_content()
                            return "DAILY_LIMIT"
                        if any(x in body_text for x in ["awarded", "earned", "crowns", "congratulations", "success"]):
                            reward_confirmed = True
                            print("KingsIsle confirmed reward claim!")
                            break
                    except Exception:
                        # Popup closed or navigated
                        reward_confirmed = True
                        break

            driver.switch_to.default_content()

            # Check if popup closed (normal behavior after successful claim)
            t.sleep(2)
            remaining_jpops = driver.find_elements(By.ID, "jPopFrame_content")
            if not remaining_jpops or not remaining_jpops[0].is_displayed():
                reward_confirmed = True

            # Dismiss any leftover alert
            try:
                alert = driver.switch_to.alert
                alert.accept()
            except Exception:
                pass

            if reward_confirmed:
                if os.path.exists('data.pkl') and os.stat('data.pkl').st_size != 0:
                    try:
                        with open('data.pkl', 'rb') as f:
                            self.crowns_earned = dill.load(f)
                    except Exception:
                        pass
                self.crowns_earned += 10
                print(f"Received 10 crowns! Lifetime total: {self.crowns_earned} crowns!")
                try:
                    self.dump(self.crowns_earned)
                except Exception as e:
                    print(f"Error saving crowns: {e}")
                return "SUCCESS"
            else:
                print("Could not confirm reward claim for this quiz.")
                return "UNCONFIRMED"

        except Exception as e:
            driver.switch_to.default_content()
            print(f"Quiz captcha step error: {e}")
            return "ERROR"

    def solveVerification(self, driver): 
        '''Solves a captcha if the verification message pops up during login.'''
        t.sleep(2)
        jpop_list = driver.find_elements(By.ID, "jPopFrame_content")
        if not jpop_list or not jpop_list[0].is_displayed():
            return

        print("Login verification popup detected!")
        try:
            driver.switch_to.frame(jpop_list[0])
            
            # Find recaptcha anchor iframe inside jpop
            anchor_frames = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'iframe[src*="recaptcha/api2/anchor"]'))
            )
            driver.switch_to.frame(anchor_frames[0])
            
            # Click recaptcha anchor checkbox
            anchor = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "recaptcha-anchor"))
            )
            anchor.click()
            t.sleep(2)
            
            driver.switch_to.default_content()
            driver.switch_to.frame(driver.find_element(By.ID, "jPopFrame_content"))

            # Check if challenge bframe is visible
            bframes = driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="recaptcha/api2/bframe"]')
            if bframes and bframes[0].is_displayed():
                driver.switch_to.frame(bframes[0])
                buster_btns = driver.find_elements(By.CSS_SELECTOR, '#solver-button, .help-button-holder, button[id*="solver"]')
                if buster_btns:
                    print("Buster extension detected! Clicking auto-solve...")
                    buster_btns[0].click()
                    t.sleep(4)
                else:
                    print("Please complete the captcha challenge in the browser window if prompted...")
                driver.switch_to.default_content()
                driver.switch_to.frame(driver.find_element(By.ID, "jPopFrame_content"))

            # Wait for captcha to be checked (up to 90 seconds)
            print("Waiting for captcha verification...")
            start_time = t.time()
            while t.time() - start_time < 90:
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(driver.find_element(By.ID, "jPopFrame_content"))
                    anchor_f = driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="recaptcha/api2/anchor"]')
                    if anchor_f:
                        driver.switch_to.frame(anchor_f[0])
                        if driver.find_element(By.ID, "recaptcha-anchor").get_attribute("aria-checked") == "true":
                            print("Captcha verified successfully!")
                            break
                except Exception:
                    pass
                t.sleep(1.5)

            # Switch back to popup and click bp_login
            driver.switch_to.default_content()
            driver.switch_to.frame(driver.find_element(By.ID, "jPopFrame_content"))
            login_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "bp_login"))
            )
            login_btn.click()
            driver.switch_to.default_content()
            t.sleep(4)
            print("Login verification completed!")
        except Exception as e:
            driver.switch_to.default_content()
            print(f"Verification process finished or bypassed: {e}")

    def clickCookies(self, driver):
        """Accepts cookies if the banner is present."""
        try:
            cookie_buttons = driver.find_elements(By.ID, "onetrust-accept-btn-handler")
            if cookie_buttons and cookie_buttons[0].is_displayed():
                cookie_buttons[0].click()
                t.sleep(1)
        except Exception:
            pass
