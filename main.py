from trivia_qa import wizard101_trivia_questions_and_answers as wt
from answers import Wizard101_Trivia as answers_dict
import difflib
import json
import os
import time as t
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
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
from urllib.parse import urlparse

class AutoTrivia():
    """Main module that automates the trivia"""
    def __init__(self):
        self.user_account = {}
        self.chromewebdriver = WebDriver()
        self.script_directory = pathlib.Path().absolute()
        self.chrome_driver_path = None
        self.has_quizes = True

    _ACCOUNT_STATE_FILE = os.path.join("text_files", "account_state.json")
    _DAILY_COOLDOWN_SECONDS = 22 * 3600

    @staticmethod
    def _load_account_state():
        try:
            with open(AutoTrivia._ACCOUNT_STATE_FILE, "r", encoding="utf-8") as f:
                state = json.load(f)
            return state if isinstance(state, dict) else {}
        except Exception:
            return {}

    @staticmethod
    def _record_daily_limit(user):
        try:
            os.makedirs("text_files", exist_ok=True)
            state = AutoTrivia._load_account_state()
            entry = state.get(user) or {}
            entry["daily_limit_at"] = t.time()
            state[user] = entry
            with open(AutoTrivia._ACCOUNT_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except Exception as e:
            print(f"Could not record daily-limit cooldown for {user}: {e}")

    @staticmethod
    def _record_quiz_cooldown(user, quiz_name):
        try:
            os.makedirs("text_files", exist_ok=True)
            state = AutoTrivia._load_account_state()
            entry = state.get(user) or {}
            cooldowns = entry.get("quiz_cooldowns") or {}
            cooldowns[quiz_name] = t.time()
            entry["quiz_cooldowns"] = cooldowns
            state[user] = entry
            with open(AutoTrivia._ACCOUNT_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(state, f)
        except Exception as e:
            print(f"Could not record quiz cooldown for {quiz_name}: {e}")

    @staticmethod
    def _quiz_cooldown_remaining(user, quiz_name):
        try:
            entry = AutoTrivia._load_account_state().get(user) or {}
            cooldowns = entry.get("quiz_cooldowns") or {}
            elapsed = t.time() - float(cooldowns.get(quiz_name, 0))
            remaining = AutoTrivia._DAILY_COOLDOWN_SECONDS - elapsed
            return remaining if remaining > 0 else 0
        except Exception:
            return 0

    @staticmethod
    def _cooldown_remaining(user):
        try:
            entry = AutoTrivia._load_account_state().get(user) or {}
            elapsed = t.time() - float(entry.get("daily_limit_at", 0))
            remaining = AutoTrivia._DAILY_COOLDOWN_SECONDS - elapsed
            return remaining if remaining > 0 else 0
        except Exception:
            return 0

    @staticmethod
    def _normalize_answer(value):
        text = (value or "").lower().replace("–", "-").replace("—", "-").replace("−", "-")
        text = text.strip(" .?!'\"")
        return " ".join(text.split()).replace(" - ", "-")

    def setup(self):
        if not self.user_account:
            print("No accounts found in text_files/accounts.txt. Please add accounts in 'username password' format.")
            return False

        print(f"\n==========================================")
        print(f"Loaded {len(self.user_account)} account(s): {', '.join(self.user_account.keys())}")
        print(f"==========================================\n")

        all_complete = True
        for key, value in self.user_account.items():
            print(f"\n==========================================")
            print(f"Starting thread for user: {key}...")
            print(f"==========================================")
            try:
                result = self.process_account(key, value)
            except Exception as e:
                result = {
                    "user": key,
                    "status": "ERROR",
                    "claimed": 0,
                    "error": str(e),
                }

            status = result.get("status", "ERROR") if result else "ERROR"
            claimed = result.get("claimed", 0) if result else 0
            if status in ("COMPLETED", "DAILY_LIMIT", "ALREADY_COMPLETED"):
                if status == "DAILY_LIMIT":
                    limit_reason = result.get("reason", "10 quizzes for the day are done") if result else "daily limit reached"
                    print(f"\nSuccess for {key}: Website confirmed 10 quizzes for the day are done ({claimed} claimed in this session). {limit_reason}")
                elif status == "ALREADY_COMPLETED":
                    print(f"\nFinished {key}: all quizzes were already completed on the website; no new reward was claimed.")
                else:
                    print(f"\nCompleted {key}: {claimed} quiz reward(s) explicitly confirmed.")
            elif status == "SUBMITTED":
                all_complete = False
                submitted = result.get("submitted", []) if result else []
                print(f"\n{key}: {claimed} confirmed, {len(submitted)} submitted-but-unconfirmed. Check the crown balance.")
            else:
                all_complete = False
                reason = result.get("reason", "one or more quizzes were not confirmed") if result else "worker returned no result"
                print(f"\nIncomplete {key}: {reason}. Confirmed claims: {claimed}.")

        if all_complete:
            print("\nSuccess! All account runs finished successfully.")
        else:
            print("\nFinished with incomplete account runs.")
        return all_complete

    def process_account(self, key, value):
        result_holder = {}
        progress = {
            "claimed": 0,
            "failed": [],
            "already_completed": 0,
            "submitted": [],
            "limited": [],
        }

        def target(user, passwrd, driver):
            try:
                result_holder["result"] = self.run(user, passwrd, driver, progress)
            except Exception as e:
                result_holder["error"] = e
            finally:
                try:
                    driver.quit()
                except Exception:
                    pass

        th = Threadium(1)
        th.start_all(
            args=(key, value),
            single_target=target,
            profile_dir=[os.path.join("user-data-dir", f"{key}-dir"), f"{key}-user-data"],
        )
        if "error" in result_holder:
            return {
                "user": key,
                "status": "ERROR",
                "claimed": progress.get("claimed", 0),
                "already_completed": progress.get("already_completed", 0),
                "submitted": progress.get("submitted", []),
                "limited": progress.get("limited", []),
                "failed": progress.get("failed", []),
                "reason": str(result_holder["error"]),
            }
        return result_holder.get("result")
        
    def proxy_generator(self):
        return None    
        
    @staticmethod
    def _login_failure_diagnostics(driver, user):
        try:
            print(f"Login page URL: {driver.current_url}")
        except Exception:
            pass
        try:
            print(f"Login page title: {driver.title}")
        except Exception:
            pass
        try:
            page_text = driver.find_element(By.TAG_NAME, "body").text
            error_markers = [
                line.strip()
                for line in page_text.splitlines()
                if line.strip() and any(
                    word in line.lower()
                    for word in ("incorrect", "invalid", "failed", "locked", "suspended", "verify", "captcha", "robot", "error", "denied")
                )
            ]
            if error_markers:
                print(f"Login page messages: {' | '.join(error_markers[:5])}")
        except Exception:
            pass
        try:
            os.makedirs("scratch", exist_ok=True)
            path = os.path.join("scratch", f"login-failure-{user}.png")
            driver.save_screenshot(path)
            print(f"Login failure screenshot saved to: {path}")
        except Exception as e:
            print(f"Could not save login failure screenshot: {e}")

    def run(self, user, passwrd, driver, progress=None):
        if progress is None:
            progress = {}
        progress.setdefault("claimed", 0)
        progress.setdefault("failed", [])
        progress.setdefault("already_completed", 0)
        progress.setdefault("submitted", [])
        qa_dict = {**answers_dict, **wt}

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

        selected_handle = None
        for handle in driver.window_handles:
            driver.switch_to.window(handle)
            current_url = driver.current_url.lower()
            host = urlparse(current_url).hostname or ""
            if host == "wizard101.com" or host.endswith(".wizard101.com"):
                selected_handle = handle
                break
        if selected_handle is None:
            raise RuntimeError("Wizard101 page was not found in the browser tabs.")

        if not self.chromewebdriver.reset_site_session(driver):
            raise RuntimeError("Could not clear the existing Wizard101 session; refusing to continue.")
        print("Cleared existing Wizard101 cookies and site storage before login.")
        driver.refresh()
        t.sleep(4)
        self.chromewebdriver.clickCookies(driver=driver)

        username_button = '//*[@id="loginUserName"]'
        password_button = '//*[@id="loginPassword"]'
        login_button = '//*[@id="wizardLoginButton"]//input[@type="submit" or @value="Login"]'

        try:
            username = WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.XPATH, username_button))
            )
        except TimeoutException as e:
            raise RuntimeError(
                "Login form was not visible after clearing the existing session; refusing to continue with an unknown account."
            ) from e

        print(f"Logging in user: {user}...")
        username.clear()
        username.send_keys(user)
        password = WebDriverWait(driver, 10).until(
            EC.visibility_of_element_located((By.XPATH, password_button))
        )
        password.clear()
        password.send_keys(passwrd)
        login_btn = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, login_button))
        )
        login_btn.click()
        t.sleep(4)
        self.chromewebdriver.clickCookies(driver=driver)
        if not self.chromewebdriver.solveVerification(driver=driver):
            raise RuntimeError(f"Login verification did not complete for {user}.")
        try:
            driver.get("https://www.wizard101.com/quiz/trivia/game/kingsisle-trivia")
            t.sleep(3)
        except Exception as e:
            raise RuntimeError(f"Could not verify the logged-in session for {user}.") from e
        try:
            WebDriverWait(driver, 15).until(
                EC.invisibility_of_element_located((By.XPATH, username_button))
            )
        except TimeoutException:
            print(f"Login form is still visible for {user}; retrying the login submit once...")
            try:
                retry_login_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, login_button))
                )
                retry_login_btn.click()
                t.sleep(4)
                if not self.chromewebdriver.solveVerification(driver=driver):
                    raise RuntimeError(f"Login verification did not complete for {user} on retry.")
                driver.get("https://www.wizard101.com/quiz/trivia/game/kingsisle-trivia")
                t.sleep(3)
                WebDriverWait(driver, 15).until(
                    EC.invisibility_of_element_located((By.XPATH, username_button))
                )
            except Exception as e:
                self._login_failure_diagnostics(driver, user)
                raise RuntimeError(
                    f"Login did not complete for {user}; the login form remained visible."
                ) from e
        print(f"Login step completed for {user}.")
        identity_status = self.chromewebdriver.account_identity(driver, user)
        if identity_status is False:
            raise RuntimeError(f"The page exposes a different account identity than {user}; refusing to continue.")
        if identity_status is None:
            print(f"Account identity for {user} is not exposed on the page; login submission was verified, but check the account manually.")
        self.chromewebdriver.clickCookies(driver=driver)

        completed_quizes = set()
        already_completed_quizes = set()
        failed_quizes = progress["failed"]
        submitted_quizes = progress["submitted"]
        quizzes_claimed = 0
        website_daily_limit_reached = False
        website_limit_message = ""

        def mark_failure(name, reason):
            failed_quizes[:] = [item for item in failed_quizes if item[0] != name]
            failed_quizes.append((name, reason))

        def clear_failure(name):
            failed_quizes[:] = [item for item in failed_quizes if item[0] != name]

        print(f"\nStarting trivia automation for {user}. Running all {len(quizes)} available quizzes...")

        max_passes = 3
        for pass_num in range(1, max_passes + 1):
            quizes_to_run = [q for q in quizes if q not in completed_quizes]
            if not quizes_to_run:
                break

            if pass_num > 1:
                print(f"\n--- Starting Pass {pass_num} for remaining {len(quizes_to_run)} quiz(zes) ---")

            for quiz_idx, quiz_name in enumerate(quizes_to_run, start=1):
                slug = quiz_name.lower().replace(" ", "-")
                quiz_url = f"https://www.wizard101.com/quiz/trivia/game/{slug}"
                print(f"\n==========================================")
                print(f"[{quiz_idx}/{len(quizes_to_run)}] Starting: {quiz_name}")
                print(f"==========================================")

                driver.get(quiz_url)
                t.sleep(3)
                self.chromewebdriver.clickCookies(driver=driver)

                first_question = None
                for _ in range(10):
                    q_check = driver.find_elements(By.CLASS_NAME, 'quizQuestion')
                    if q_check and q_check[0].is_displayed():
                        first_question = q_check[0]
                        break
                    t.sleep(1)

                if not first_question:
                    # Check if questions were already answered and a claim button is already waiting
                    claim_btns_check = self.chromewebdriver._visible_enabled(
                        driver.find_elements(
                            By.XPATH,
                            '//*[@id="quizFormComponent"]//a[contains(concat(" ", normalize-space(@class), " "), " kiaccountsbutton ") or contains(translate(normalize-space(.), "abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "CLAIM YOUR REWARD") or contains(translate(normalize-space(.), "abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "SEE YOUR SCORE")]',
                        )
                    )
                    if not claim_btns_check:
                        another_quiz_btn = self.chromewebdriver._visible_enabled(
                            driver.find_elements(
                                By.XPATH,
                                '//*[@id="quizFormComponent"]//*[contains(translate(normalize-space(.), "abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "TAKE ANOTHER QUIZ")]',
                            )
                        )
                        if another_quiz_btn:
                            print(f"Quiz '{quiz_name}' shows already completed today on the website; moving to next quiz.")
                            completed_quizes.add(quiz_name)
                            already_completed_quizes.add(quiz_name)
                            clear_failure(quiz_name)
                            progress["already_completed"] = len(already_completed_quizes)
                            continue

                        page_text = self.chromewebdriver.page_state_text(driver)
                        daily_match = self.chromewebdriver._daily_limit_match(page_text)
                        if daily_match:
                            website_daily_limit_reached = True
                            website_limit_message = daily_match
                            print(f"Quiz '{quiz_name}': website indicated limit ('{daily_match}'); moving to next quiz.")
                            self._record_daily_limit(user)
                            completed_quizes.add(quiz_name)
                            clear_failure(quiz_name)
                            continue

                        reason = "questions did not load"
                        print(f"Quiz '{quiz_name}' was not completed: {reason}; moving to next quiz.")
                        mark_failure(quiz_name, reason)
                        continue

                if first_question:
                    last_q_text = ""
                    same_q_count = 0
                    answered_count = 0
                    answer_failed = False
                    question_stuck = False
                    quiz_finished = False

                    for step in range(1, 16):
                        q_els = driver.find_elements(By.CLASS_NAME, 'quizQuestion')
                        if not q_els or not q_els[0].is_displayed():
                            quiz_finished = True
                            break

                        q_text = q_els[0].text.strip()
                        if not q_text:
                            t.sleep(1)
                            q_els = driver.find_elements(By.CLASS_NAME, 'quizQuestion')
                            if not q_els or not q_els[0].is_displayed():
                                quiz_finished = True
                                break
                            q_text = q_els[0].text.strip()
                            if not q_text:
                                answer_failed = True
                                break

                        if q_text == last_q_text:
                            same_q_count += 1
                            if same_q_count >= 3:
                                question_stuck = True
                                print("  Question did not advance; stopping this quiz attempt.")
                                break
                            t.sleep(1)
                            continue

                        same_q_count = 0
                        last_q_text = q_text
                        print(f"  Q{answered_count + 1}: {q_text[:65]}...")

                        matches = difflib.get_close_matches(q_text, qa_dict.keys(), n=1, cutoff=0.5)
                        if not matches:
                            answer_failed = True
                            print("  No answer mapping was found; no answer was submitted.")
                            break
                        target_ans = qa_dict[matches[0]]
                        choice_texts = driver.execute_script("""
                            return Array.from(document.querySelectorAll('.answersContainer .answer')).filter(function(el) {
                                return el.getClientRects().length > 0;
                            }).map(function(el) {
                                return el.textContent.trim();
                            });
                        """) or []
                        if not target_ans or not choice_texts:
                            answer_failed = True
                            print("  The answer choices were unavailable; no answer was submitted.")
                            break
                        answer_control_count = driver.execute_script("""
                            return Array.from(document.getElementsByName('answers')).filter(function(el) {
                                return !el.disabled;
                            }).length;
                        """)
                        if answer_control_count == 0:
                            answer_failed = True
                            print("  No enabled answer controls were found; no answer was submitted.")
                            break
                        if answer_control_count != len(choice_texts):
                            print(
                                f"  Found {answer_control_count} answer control(s) for "
                                f"{len(choice_texts)} choice label(s); using the page order."
                            )

                        clean_target = self._normalize_answer(target_ans)
                        clean_choices = [
                            self._normalize_answer(choice)
                            for choice in choice_texts
                        ]
                        ans_idx = None
                        for idx, choice in enumerate(clean_choices):
                            if choice == clean_target:
                                ans_idx = idx
                                break
                        if ans_idx is None:
                            for idx, choice in enumerate(clean_choices):
                                if clean_target in choice or choice in clean_target:
                                    ans_idx = idx
                                    break
                        if ans_idx is None:
                            fuzzy_matches = difflib.get_close_matches(
                                clean_target,
                                clean_choices,
                                n=1,
                                cutoff=0.4,
                            )
                            if fuzzy_matches:
                                ans_idx = clean_choices.index(fuzzy_matches[0])
                        if ans_idx is None:
                            answer_failed = True
                            print("  The mapped answer was not present; no answer was submitted.")
                            break

                        submitted = driver.execute_script("""
                            var nodes = Array.from(document.getElementsByName('answers')).filter(function(el) {
                                return !el.disabled;
                            });
                            if (nodes.length <= arguments[0]) {
                                return false;
                            }
                            nodes[arguments[0]].checked = true;
                            if (typeof updateQuiz === 'function') {
                                updateQuiz();
                                return true;
                            }
                            var btn = document.getElementById('nextQuestion');
                            if (btn) {
                                btn.click();
                                return true;
                            }
                            return false;
                        """, ans_idx)
                        if not submitted:
                            answer_failed = True
                            print("  The answer was selected but the quiz did not accept a submission.")
                            break
                        answered_count += 1
                        t.sleep(1.8)

                    if answer_failed or question_stuck or not quiz_finished or answered_count == 0:
                        reason = "answer mapping or submission failed"
                        if question_stuck:
                            reason = "quiz stopped advancing"
                        elif not quiz_finished:
                            reason = "quiz did not reach a result screen"
                        print(
                            f"Quiz '{quiz_name}' was not completed: {reason} "
                            f"after {answered_count} submitted answer(s)."
                        )
                        mark_failure(quiz_name, reason)
                        continue

                    print(
                        f"Answered {answered_count} questions for '{quiz_name}'. "
                        "Looking for a visible claim control..."
                    )
                    t.sleep(2)
                    self.chromewebdriver.clickCookies(driver=driver)
                else:
                    print(f"Quiz '{quiz_name}' questions already completed; looking for a visible claim control...")

                claim_btns = self.chromewebdriver._visible_enabled(
                    driver.find_elements(
                        By.XPATH,
                        '//*[@id="quizFormComponent"]//a[contains(concat(" ", normalize-space(@class), " "), " kiaccountsbutton ") or contains(translate(normalize-space(.), "abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "CLAIM YOUR REWARD") or contains(translate(normalize-space(.), "abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "SEE YOUR SCORE")]',
                    )
                )
                if not claim_btns:
                    body_text = driver.find_element(By.TAG_NAME, 'body').text
                    daily_match = self.chromewebdriver._daily_limit_match(body_text)
                    if daily_match:
                        website_daily_limit_reached = True
                        website_limit_message = daily_match
                        print(f"Quiz '{quiz_name}': daily limit shown on page ('{daily_match}'); moving to next quiz.")
                        self._record_daily_limit(user)
                        completed_quizes.add(quiz_name)
                        clear_failure(quiz_name)
                        continue
                    reason = "no visible claim or score control appeared"
                    print(f"Quiz '{quiz_name}' was not completed: {reason}.")
                    mark_failure(quiz_name, reason)
                    continue

                print("Clicking the visible claim control...")
                claim_clicked = False
                try:
                    driver.execute_script("arguments[0].click();", claim_btns[-1])
                    claim_clicked = True
                except Exception:
                    try:
                        claim_btns[-1].click()
                        claim_clicked = True
                    except Exception as e:
                        print(f"Could not click the claim control: {e}")
                if not claim_clicked:
                    reason = "claim control could not be clicked"
                    print(f"Quiz '{quiz_name}' was not completed: {reason}.")
                    mark_failure(quiz_name, reason)
                    continue
                t.sleep(3)

                try:
                    body_text = driver.find_element(By.TAG_NAME, 'body').text
                    daily_match = self.chromewebdriver._daily_limit_match(body_text)
                    if daily_match:
                        website_daily_limit_reached = True
                        website_limit_message = daily_match
                except Exception:
                    pass

                popup_visible = False
                for _ in range(10):
                    popup = self.chromewebdriver._visible_popup(driver)
                    if popup is not None:
                        popup_visible = True
                        break
                    t.sleep(1)

                if not popup_visible:
                    try:
                        body_text = driver.find_element(By.TAG_NAME, 'body').text
                        daily_match = self.chromewebdriver._daily_limit_match(body_text)
                        if daily_match:
                            website_daily_limit_reached = True
                            website_limit_message = daily_match
                            print(f"Quiz '{quiz_name}': daily limit shown after claim ('{daily_match}'); moving to next quiz.")
                            self._record_daily_limit(user)
                            completed_quizes.add(quiz_name)
                            clear_failure(quiz_name)
                            continue
                    except Exception:
                        pass
                    reason = "no reward popup appeared after the claim control was clicked"
                    print(f"Quiz '{quiz_name}' was not counted: {reason}; moving to the next quiz.")
                    mark_failure(quiz_name, reason)
                    continue

                status = self.chromewebdriver.solveCaptcha(driver=driver)
                if status == "DAILY_LIMIT":
                    website_daily_limit_reached = True
                    website_limit_message = "Daily limit reached according to website response"
                    print(f"Quiz '{quiz_name}': daily limit message received from website; moving to next quiz.")
                    self._record_daily_limit(user)
                    completed_quizes.add(quiz_name)
                    clear_failure(quiz_name)
                    continue
                if status == "SUBMITTED_UNCONFIRMED":
                    submitted_quizes.append(quiz_name)
                    completed_quizes.add(quiz_name)
                    clear_failure(quiz_name)
                    print(f"Quiz '{quiz_name}' was submitted but unconfirmed; check the crown balance. Moving to the next quiz.")
                    continue
                if status in {"ACCOUNT_ACTION_REQUIRED", "CAPTCHA_ANCHOR_INACCESSIBLE", "CAPTCHA_UNAVAILABLE", "CAPTCHA_UNVERIFIED", "ERROR", "NO_SUBMIT", "NO_POPUP", "UNCONFIRMED"}:
                    reason = f"reward status was {status}"
                    print(f"Quiz '{quiz_name}' was not counted: {reason}; moving to the next quiz.")
                    mark_failure(quiz_name, reason)
                    continue
                if status == "SUCCESS":
                    quizzes_claimed += 1
                    progress["claimed"] = quizzes_claimed
                    clear_failure(quiz_name)
                    completed_quizes.add(quiz_name)
                    rem = getattr(self.chromewebdriver, "remaining_quizzes_today", None)
                    rem_msg = f" (Website: {rem} more quiz(zes) to earn Crowns today)" if rem is not None else ""
                    print(
                        f"Quiz '{quiz_name}' reward explicitly confirmed "
                        f"({quizzes_claimed} claimed in this session){rem_msg}."
                    )
                    if rem == 0:
                        website_daily_limit_reached = True
                        website_limit_message = "Website confirmed 0 more quizzes can earn crowns today"
                elif status == "ALREADY_CLAIMED":
                    completed_quizes.add(quiz_name)
                    already_completed_quizes.add(quiz_name)
                    clear_failure(quiz_name)
                    progress["already_completed"] = len(already_completed_quizes)
                    print(f"Quiz '{quiz_name}' was already claimed today on the website; moving to next quiz.")
                    continue
                else:
                    reason = f"reward status was {status}"
                    print(f"Quiz '{quiz_name}' was not counted as successful: {reason}; moving to the next quiz.")
                    mark_failure(quiz_name, reason)
                    continue

                t.sleep(2)

        if len(completed_quizes) == len(quizes):
            status = "COMPLETED"
            if website_daily_limit_reached:
                reason = f"all available quizzes completed ({quizzes_claimed} claimed, {len(already_completed_quizes)} already completed, daily limit confirmed: {website_limit_message or 'yes'})"
                print(
                    f"\n=========================================="
                    f"\nCompleted all {len(quizes)} available quizzes for {user}!"
                    f"\nRewards confirmed this session: {quizzes_claimed}"
                    f"\nAlready completed today: {len(already_completed_quizes)}"
                    f"\nDaily limit message: {website_limit_message or 'Observed on website'}"
                    f"\n=========================================="
                )
            elif quizzes_claimed == 0 and already_completed_quizes and not submitted_quizes:
                status = "ALREADY_COMPLETED"
                reason = "all quizzes were already completed on the website"
                print(f"\nAll quizzes were already completed today for {user}; no new rewards to claim.")
            else:
                reason = f"all available quizzes completed ({quizzes_claimed} claimed, {len(already_completed_quizes)} already completed today)"
                print(
                    f"\nCompleted all available quizzes for {user}: "
                    f"{quizzes_claimed} reward(s) confirmed, "
                    f"{len(already_completed_quizes)} already completed today."
                )
        elif website_daily_limit_reached and not failed_quizes:
            status = "DAILY_LIMIT"
            reason = f"Ran all available quizzes; daily limit confirmed: {website_limit_message or 'daily limit reached'}"
            print(
                f"\n=========================================="
                f"\n{user}: All quizzes attempted. Daily limit reached ({quizzes_claimed} claimed, {len(already_completed_quizes)} already completed)."
                f"\n=========================================="
            )
        elif failed_quizes:
            status = "INCOMPLETE"
            reason = "; ".join(f"{name}: {why}" for name, why in failed_quizes)
            print(
                f"\nFinished run for {user} with issues: {reason}. "
                f"Confirmed rewards: {quizzes_claimed}."
            )
        elif submitted_quizes:
            status = "SUBMITTED"
            reason = f"{len(submitted_quizes)} quiz(zes) submitted but unconfirmed; verify the crown balance"
            print(
                f"\n{user}: {quizzes_claimed} reward(s) confirmed; "
                f"{len(submitted_quizes)} submitted but unconfirmed. Check the crown balance."
            )
        else:
            status = "COMPLETED"
            reason = f"quiz run completed ({quizzes_claimed} claimed)"
            print(f"\nCompleted {user}: {quizzes_claimed} reward(s) confirmed.")

        progress["claimed"] = quizzes_claimed
        progress["already_completed"] = len(already_completed_quizes)
        progress["status"] = status
        progress["reason"] = reason
        driver.quit()
        return {
            "user": user,
            "status": status,
            "claimed": quizzes_claimed,
            "already_completed": len(already_completed_quizes),
            "submitted": submitted_quizes,
            "failed": failed_quizes,
            "reason": reason,
        }
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
    raise SystemExit(0 if at.setup() else 1)
