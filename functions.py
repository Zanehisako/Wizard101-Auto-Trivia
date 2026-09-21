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
        Solves the captcha at the end of the quiz, automatically re-does the captcha if needed.
        '''
        print("Handling quiz completion captcha...")
        t.sleep(2)
        jpop_list = driver.find_elements(By.ID, "jPopFrame_content")
        if not jpop_list or not jpop_list[0].is_displayed():
            return

        try:
            driver.switch_to.frame(jpop_list[0])
            
            # Click recaptcha anchor if not already checked
            anchors = driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="recaptcha/api2/anchor"]')
            if anchors:
                driver.switch_to.frame(anchors[0])
                anchor = WebDriverWait(driver, 5).until(EC.element_to_be_clickable((By.ID, "recaptcha-anchor")))
                if anchor.get_attribute("aria-checked") != "true":
                    anchor.click()
                    t.sleep(2)
                driver.switch_to.default_content()
                driver.switch_to.frame(driver.find_element(By.ID, "jPopFrame_content"))

            # Check challenge bframe for Buster extension button
            bframes = driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="recaptcha/api2/bframe"]')
            if bframes and bframes[0].is_displayed():
                driver.switch_to.frame(bframes[0])
                buster_btns = driver.find_elements(By.CSS_SELECTOR, '#solver-button, .help-button-holder, button[id*="solver"]')
                if buster_btns:
                    print("Buster extension detected! Clicking auto-solve...")
                    buster_btns[0].click()
                    t.sleep(4)
                else:
                    print("Please complete the quiz captcha challenge in the browser window if prompted...")
                driver.switch_to.default_content()
                driver.switch_to.frame(driver.find_element(By.ID, "jPopFrame_content"))

            # Wait for verification (up to 90 seconds)
            start_time = t.time()
            while t.time() - start_time < 90:
                try:
                    driver.switch_to.default_content()
                    driver.switch_to.frame(driver.find_element(By.ID, "jPopFrame_content"))
                    anchors = driver.find_elements(By.CSS_SELECTOR, 'iframe[src*="recaptcha/api2/anchor"]')
                    if anchors:
                        driver.switch_to.frame(anchors[0])
                        if driver.find_element(By.ID, "recaptcha-anchor").get_attribute("aria-checked") == "true":
                            print("Quiz captcha verified!")
                            break
                except Exception:
                    pass
                t.sleep(1.5)

            driver.switch_to.default_content()
        except Exception as e:
            driver.switch_to.default_content()
            print(f"Quiz captcha step finished: {e}")

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
