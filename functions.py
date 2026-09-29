import time as t
import dill
import os
import re
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import *

class WebDriver():
    _RECAPTCHA_ANCHOR_SELECTOR = 'iframe[src*="recaptcha/api2/anchor"], iframe[src*="recaptcha/enterprise/anchor"]'
    _RECAPTCHA_BFRAME_SELECTOR = 'iframe[src*="recaptcha/api2/bframe"], iframe[src*="recaptcha/enterprise/bframe"]'
    _REWARD_SUBMIT_XPATH = (
        '//*[@id="submit"] | //input[@id="submit"] '
        '| //a[contains(concat(" ", normalize-space(@class), " "), " buttonsubmit ")] '
        '| //button[contains(translate(normalize-space(.), "abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "CLAIM YOUR REWARD")] '
        '| //a[contains(translate(normalize-space(.), "abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "CLAIM YOUR REWARD")] '
        '| //input[contains(translate(@value, "abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "CLAIM YOUR REWARD")]'
    )
    _CAPTCHA_UNAVAILABLE_PATTERNS = (
        r"\bexceeding recaptcha enterprise free quota\b",
        r"\brecaptcha enterprise free quota\b",
        r"\brecaptcha quota exceeded\b",
        r"\bsite is exceeding recaptcha\b",
    )
    _DAILY_LIMIT_PATTERNS = (
        r"\bexceeded the number of quizzes allowed today\b",
        r"\bmaximum crowns you can earn today\b",
        r"\balready earned your crowns for today\b",
        r"\balready earned 100 crowns\b",
        r"\bmaximum (?:amount|number) of quizzes (?:allowed )?for today\b",
        r"\b(?:exceeded|reached) (?:the |your )?daily (?:quiz|crown|reward) limit\b",
        r"\bdaily (?:quiz|crown|reward) limit (?:reached|exceeded)\b",
        r"\byou (?:have|has|'ve) reached (?:the |your )?daily\b",
        r"\b(?:completed|taken|finished|done) (?:all )?10 quizzes\b",
        r"\b10 quizzes (?:today|for today|per day) have been completed\b",
        r"\byou (?:have|has|'ve) already (?:earned|received|reached|gotten) (?:your |the )?(?:maximum|100 crowns|daily)\b",
        r"\b(?:reached|completed) (?:the )?maximum of 10 quizzes\b",
        r"\b(?:earned|reached) 100 crowns today\b",
        r"\bmaximum daily crowns reached\b",
        r"\bcome back tomorrow to earn\b",
    )

    def __init__(self): 
        self.crowns_earned = 0
        self.remaining_quizzes_today = None

    def dump(self, obj):
        '''
        Dumps the data to a file.
        '''
        os.makedirs("text_files", exist_ok=True)
        with open(os.path.join("text_files", "data.txt"), 'w', encoding='utf-8') as f:
            f.write(f'Local automation counter (not account balance): {obj}\n')
        with open('data.pkl', 'wb') as f:
            dill.dump(obj, f)

    @staticmethod
    def _normalized_text(value):
        return " ".join((value or "").lower().split())

    @staticmethod
    def _has_negation(value):
        text = (value or "").lower().replace("’", "'")
        return bool(
            re.search(
                r"(?:\b(?:not|never|no|cannot|unable|failed|failure|pending|unconfirmed)\b|n't\b)",
                text,
            )
        )

    @classmethod
    def _has_unnegated_match(cls, value, patterns):
        text = cls._normalized_text(value)
        for pattern in patterns:
            for match in re.finditer(pattern, text):
                start = max(0, match.start() - 60)
                end = min(len(text), match.end() + 60)
                if not cls._has_negation(text[start:end]):
                    return True
        return False

    @classmethod
    def _captcha_unavailable_match(cls, value):
        text = cls._normalized_text(value)
        if not text:
            return None
        for pattern in cls._CAPTCHA_UNAVAILABLE_PATTERNS:
            for match in re.finditer(pattern, text):
                start = max(0, match.start() - 80)
                end = min(len(text), match.end() + 80)
                return text[start:end]
        return None

    @classmethod
    def _daily_limit_match(cls, value):
        text = cls._normalized_text(value)
        if not text:
            return None
        for pattern in cls._DAILY_LIMIT_PATTERNS:
            for match in re.finditer(pattern, text):
                start = max(0, match.start() - 80)
                end = min(len(text), match.end() + 80)
                if not cls._has_negation(text[start:end]):
                    return text[start:end]
        if "come back tomorrow" in text and any(
            marker in text
            for marker in ("maximum", "exceeded", "daily", "quizzes allowed", "100 crowns", "crowns", "quiz", "earn")
        ):
            for match in re.finditer(r"\bcome back tomorrow\b", text):
                start = max(0, match.start() - 80)
                end = min(len(text), match.end() + 80)
                if not cls._has_negation(text[start:end]):
                    return text[start:end]
        return None

    @classmethod
    def _is_daily_limit(cls, value):
        return cls._daily_limit_match(value) is not None

    @classmethod
    def _is_account_action_required(cls, value):
        text = cls._normalized_text(value)
        if not text:
            return False
        patterns = (
            r"\bconfirm your account\b",
            r"\bverify your account\b",
            r"\bverify your email\b",
            r"\bcheck your email\b",
        )
        return cls._has_unnegated_match(text, patterns)

    @classmethod
    def _is_reward_confirmation(cls, value):
        text = cls._normalized_text(value)
        if not text:
            return False
        patterns = (
            r"\b(?:you(?:'ve| have)?|your account)\s+(?:(?:have|has|were|was)\s+)?(?:been\s+)?(?:earned|received|awarded|claimed|added)\s+(?:an?\s+)?10\s+crowns?\b",
            r"\b10\s+crowns?\s+(?:has|have|were|was|is|are)\s+(?:been\s+)?(?:added|credited|awarded|received)\b",
            r"\bcongratulations\b[^.!?\n]{0,120}\b(?:crowns?|quiz reward)\b",
            r"\bquiz reward\b[^.!?\n]{0,120}\b(?:approved|credited|claimed|earned)\b",
            r"\byou can take \d+ more quizzes to earn crowns today\b",
            r"\bmore quizzes to earn crowns today\b",
            r"\bto your account\b[^.!?\n]{0,120}\b(?:crowns|more quizzes)\b",
        )
        return cls._has_unnegated_match(text, patterns)

    @classmethod
    def _extract_remaining_quizzes(cls, value):
        text = cls._normalized_text(value)
        if not text:
            return None
        m = re.search(r"\byou can take (\d+) more quizzes to earn crowns today\b", text)
        if m:
            return int(m.group(1))
        m = re.search(r"(\d+)\s+more quizzes to earn crowns today", text)
        if m:
            return int(m.group(1))
        return None

    @classmethod
    def _is_already_claimed(cls, value):
        text = cls._normalized_text(value)
        if not text:
            return False
        patterns = (
            r"\b(?:reward|crowns?)\b[^.!?\n]{0,80}\b(?:already|previously)\b",
            r"\b(?:already|previously)\b[^.!?\n]{0,80}\b(?:reward|crowns?)\b",
            r"\b(?:reward|crowns?)\b[^.!?\n]{0,80}\b(?:claimed|credited|received)\b[^.!?\n]{0,40}\balready\b",
        )
        return cls._has_unnegated_match(text, patterns)

    @staticmethod
    def _visible_enabled(elements):
        visible = []
        for element in elements:
            try:
                if element.is_displayed() and element.is_enabled():
                    visible.append(element)
            except Exception:
                pass
        return visible

    @staticmethod
    def _visible_popup(driver):
        for popup in driver.find_elements(By.ID, "jPopFrame_content"):
            try:
                if popup.is_displayed():
                    return popup
            except Exception:
                pass
        return None

    @classmethod
    def _enter_popup(cls, driver):
        popup = cls._visible_popup(driver)
        if popup is None:
            return False
        driver.switch_to.frame(popup)
        return True

    def page_state_text(self, driver):
        parts = []
        try:
            components = driver.find_elements(By.ID, "quizFormComponent")
            for component in components:
                try:
                    if component.is_displayed() and component.text:
                        parts.append(component.text)
                except Exception:
                    pass
        except Exception:
            pass
        try:
            parts.append(driver.find_element(By.TAG_NAME, "body").text)
        except Exception:
            pass
        return "\n".join(part for part in parts if part)

    @classmethod
    def _frame_diagnostics(cls, frame):
        try:
            return (
                f"tag={frame.tag_name}, displayed={frame.is_displayed()}, "
                f"size={frame.size}, rect={frame.rect}, src={frame.get_attribute('src')}"
            )
        except Exception as e:
            return f"unavailable: {e}"

    @staticmethod
    def _anchor_frame_invisible(frame):
        try:
            return "size=invisible" in (frame.get_attribute("src") or "")
        except Exception:
            return False

    @classmethod
    def _visible_recaptcha_anchors(cls, driver):
        return cls._visible_enabled(
            driver.find_elements(By.CSS_SELECTOR, cls._RECAPTCHA_ANCHOR_SELECTOR)
        )

    @classmethod
    def _visible_recaptcha_bframes(cls, driver):
        return cls._visible_enabled(
            driver.find_elements(By.CSS_SELECTOR, cls._RECAPTCHA_BFRAME_SELECTOR)
        )

    @classmethod
    def _captcha_present(cls, driver):
        try:
            driver.switch_to.default_content()
            popup = cls._visible_popup(driver)
            if popup is None:
                return False
            driver.switch_to.frame(popup)
            present = bool(
                driver.find_elements(By.CSS_SELECTOR, cls._RECAPTCHA_ANCHOR_SELECTOR)
                or driver.find_elements(By.CSS_SELECTOR, cls._RECAPTCHA_BFRAME_SELECTOR)
            )
            driver.switch_to.default_content()
            return present
        except Exception:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
            return False

    @classmethod
    def _anchor_state(cls, driver):
        try:
            driver.switch_to.default_content()
            popup = cls._visible_popup(driver)
            if popup is None:
                return None
            driver.switch_to.frame(popup)
            anchors = cls._visible_recaptcha_anchors(driver)
            if not anchors:
                driver.switch_to.default_content()
                return None
            driver.switch_to.frame(anchors[0])
            anchor = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, "recaptcha-anchor"))
            )
            checked = anchor.get_attribute("aria-checked") == "true"
            driver.switch_to.default_content()
            return checked
        except Exception as e:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
            return None

    @classmethod
    def _click_anchor_once(cls, driver):
        try:
            driver.switch_to.default_content()
            popup = cls._visible_popup(driver)
            if popup is None:
                return None
            driver.switch_to.frame(popup)
            anchors = cls._visible_recaptcha_anchors(driver)
            if not anchors:
                driver.switch_to.default_content()
                return None
            driver.switch_to.frame(anchors[0])
            anchor = WebDriverWait(driver, 3).until(
                EC.element_to_be_clickable((By.ID, "recaptcha-anchor"))
            )
            checked = anchor.get_attribute("aria-checked") == "true"
            if not checked:
                anchor.click()
            driver.switch_to.default_content()
            return checked
        except Exception:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
            return None

    @classmethod
    def _recaptcha_token(cls, driver):
        try:
            driver.switch_to.default_content()
            popup = cls._visible_popup(driver)
            if popup is None:
                return ""
            driver.switch_to.frame(popup)
            try:
                token = driver.execute_script(
                    "return (window.grecaptcha && window.grecaptcha.getResponse) ? window.grecaptcha.getResponse() : '';"
                )
            except Exception:
                token = ""
            driver.switch_to.default_content()
            return token or ""
        except Exception:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
            return ""

    @classmethod
    def _buster_button(cls, driver):
        hosts = []
        direct_buttons = []
        shadow_buttons = []
        try:
            hosts = driver.find_elements(By.CSS_SELECTOR, ".help-button-holder")
        except Exception:
            pass
        for host in hosts:
            try:
                if not host.is_displayed() or not host.is_enabled():
                    continue
                shadow = host.shadow_root
                if shadow:
                    shadow_buttons.extend(
                        shadow.find_elements(By.CSS_SELECTOR, "#solver-button")
                    )
            except Exception:
                pass
        try:
            direct_buttons = driver.find_elements(
                By.CSS_SELECTOR,
                "#solver-button, button[id*='solver']",
            )
        except Exception:
            pass
        candidates = shadow_buttons + direct_buttons
        button = None
        for candidate in cls._visible_enabled(candidates):
            button = candidate
            break
        diagnostics = (
            f"hosts={len(hosts)}, shadow_buttons={len(shadow_buttons)}, "
            f"direct_buttons={len(direct_buttons)}"
        )
        return button, None, diagnostics

    @classmethod
    def _activate_buster(cls, driver):
        try:
            driver.switch_to.default_content()
            bframes = cls._visible_recaptcha_bframes(driver)
            if not bframes:
                popup = cls._visible_popup(driver)
                if popup is None:
                    return False, "popup missing"
                driver.switch_to.frame(popup)
                bframes = cls._visible_recaptcha_bframes(driver)
            if not bframes:
                driver.switch_to.default_content()
                return False, "bframe missing"
            driver.switch_to.frame(bframes[0])
            button, _, diagnostics = cls._buster_button(driver)
            if button is not None:
                button.click()
                driver.switch_to.default_content()
                return True, diagnostics
            driver.switch_to.default_content()
            return False, diagnostics
        except Exception as e:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
            return False, f"activation error: {e}"

    @classmethod
    def _click_popup_submit(cls, driver):
        try:
            driver.switch_to.default_content()
            popup = cls._visible_popup(driver)
            if popup is None:
                return False
            driver.switch_to.frame(popup)
            buttons = cls._visible_enabled(
                driver.find_elements(
                    By.XPATH,
                    cls._REWARD_SUBMIT_XPATH,
                )
            )
            if not buttons:
                driver.switch_to.default_content()
                return False
            button = buttons[-1]
            try:
                button.click()
            except Exception:
                driver.execute_script("arguments[0].click();", button)
            driver.switch_to.default_content()
            return True
        except Exception:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
            return False

    def _record_confirmed_reward(self, source):
        if os.path.exists('data.pkl') and os.stat('data.pkl').st_size != 0:
            try:
                with open('data.pkl', 'rb') as f:
                    saved_value = dill.load(f)
                if isinstance(saved_value, (int, float)):
                    self.crowns_earned = saved_value
            except Exception:
                pass
        self.crowns_earned += 10
        print(f"Reward confirmation observed ({source}); local counter: {self.crowns_earned}.")
        try:
            self.dump(self.crowns_earned)
        except Exception as e:
            print(f"Error saving local crown counter: {e}")
        return "SUCCESS"

    def reset_site_session(self, driver):
        session_cleared = False
        try:
            driver.execute_cdp_cmd("Network.clearBrowserCookies", {})
            session_cleared = True
        except Exception:
            try:
                driver.delete_all_cookies()
                session_cleared = True
            except Exception:
                pass
        for origin in (
            "https://www.wizard101.com",
            "https://wizard101.com",
            "https://www.kingsisle.com",
        ):
            try:
                driver.execute_cdp_cmd(
                    "Storage.clearDataForOrigin",
                    {"origin": origin, "storageTypes": "all"},
                )
            except Exception:
                pass
        try:
            driver.execute_script("localStorage.clear(); sessionStorage.clear();")
        except Exception:
            pass
        return session_cleared

    def account_identity(self, driver, expected_username):
        expected = self._normalized_text(expected_username)
        selectors = (
            '//*[contains(@class, "username") or contains(@class, "account-name") or contains(@id, "username") or contains(@id, "accountName")]',
            '//*[@data-username or @data-account or @data-user]',
        )
        for selector in selectors:
            for element in driver.find_elements(By.XPATH, selector):
                try:
                    if not element.is_displayed():
                        continue
                    values = (
                        element.text,
                        element.get_attribute("value"),
                        element.get_attribute("data-username"),
                        element.get_attribute("data-account"),
                        element.get_attribute("data-user"),
                        element.get_attribute("title"),
                    )
                    normalized_values = [self._normalized_text(value) for value in values if value]
                    if expected in normalized_values:
                        return True
                    identity_values = [
                        value
                        for value in normalized_values
                        if value not in {"account", "user", "username", "my account", "login"}
                        and re.fullmatch(r"[a-z0-9_.@+-]{2,}", value)
                    ]
                    if identity_values:
                        return False
                except Exception:
                    pass
        try:
            body_text = self._normalized_text(driver.find_element(By.TAG_NAME, "body").text)
            if expected in body_text:
                return True
        except Exception:
            pass
        return None

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
        print("Handling quiz completion reward popup & captcha...")
        t.sleep(2)
        popup = self._visible_popup(driver)
        if popup is None:
            return "NO_POPUP"

        try:
            driver.switch_to.frame(popup)

            try:
                body_text = driver.find_element(By.TAG_NAME, "body").text
            except Exception:
                body_text = ""
            initial_popup_text = body_text
            quota_match = self._captcha_unavailable_match(body_text)
            if quota_match:
                print(f"reCAPTCHA quota notice present; pressing Claim Your Reward once anyway. Matched text: {quota_match[:200]}")
            claim_buttons = self._visible_enabled(
                driver.find_elements(
                    By.XPATH,
                    '//*[@id="submit"] | //input[@id="submit"] | //a[contains(@class, "buttonsubmit")] | //input[@type="submit"] | //button[@type="submit"] | //a[contains(translate(normalize-space(.), "abcdefghijklmnopqrstuvwxyz", "ABCDEFGHIJKLMNOPQRSTUVWXYZ"), "CLAIM YOUR REWARD")]',
                )
            )
            has_captcha_anchor = bool(self._visible_recaptcha_anchors(driver))

            # Only bail out immediately if there are no submit buttons and no captcha anchors to attempt
            if not claim_buttons and not has_captcha_anchor:
                daily_match = self._daily_limit_match(body_text)
                if daily_match:
                    print(f"Daily quiz/crown limit detected in reward popup (no submit controls). Matched text: {daily_match[:200]}")
                    driver.switch_to.default_content()
                    return "DAILY_LIMIT"
                if self._is_already_claimed(body_text):
                    print("Reward popup says this quiz was already claimed.")
                    driver.switch_to.default_content()
                    return "ALREADY_CLAIMED"
            if self._is_account_action_required(body_text):
                print("Reward popup says the account needs manual confirmation before crowns can be issued.")
                driver.switch_to.default_content()
                return "ACCOUNT_ACTION_REQUIRED"

            try:
                c_btn = driver.find_elements(By.XPATH, '//button[contains(@id, "accept") or contains(@id, "onetrust")]')
                visible_cookie_buttons = self._visible_enabled(c_btn)
                if visible_cookie_buttons:
                    visible_cookie_buttons[0].click()
                    t.sleep(1)
            except Exception:
                pass

            challenge_required = False
            captcha_verified = False
            anchor_click_attempted = False
            invisible_challenge = False
            submit_clicked = False
            response_observed = False
            buster_clicked = False
            last_buster_diagnostics = "not checked"
            initial_deadline = t.time() + 10

            while t.time() < initial_deadline and not captcha_verified:
                try:
                    driver.switch_to.default_content()
                    popup = self._visible_popup(driver)
                    if popup is None:
                        break
                    driver.switch_to.frame(popup)
                    anchors = self._visible_recaptcha_anchors(driver)
                    if anchors:
                        anchor_frame = anchors[0]
                        anchor_diagnostics = (
                            f"count={len(anchors)}, first={self._frame_diagnostics(anchor_frame)}"
                        )
                        if self._anchor_frame_invisible(anchor_frame):
                            invisible_challenge = True
                            challenge_required = True
                            driver.switch_to.default_content()
                            print(
                                "Invisible reCAPTCHA detected; waiting for automatic verification or a challenge. "
                                f"Anchor: {anchor_diagnostics}"
                            )
                            break
                        try:
                            driver.switch_to.frame(anchor_frame)
                            anchor = WebDriverWait(driver, 3).until(
                                EC.element_to_be_clickable((By.ID, "recaptcha-anchor"))
                            )
                            captcha_verified = anchor.get_attribute("aria-checked") == "true"
                            if not captcha_verified and not anchor_click_attempted:
                                try:
                                    driver.execute_script(
                                        "arguments[0].scrollIntoView({block: 'center'});",
                                        anchor,
                                    )
                                except Exception as scroll_error:
                                    print(f"CAPTCHA button scroll failed: {scroll_error}")
                                anchor.click()
                                anchor_click_attempted = True
                                print(
                                    "Clicked reCAPTCHA checkbox once; waiting for the challenge to settle. "
                                    f"Anchor: {anchor_diagnostics}"
                                )
                        except Exception as anchor_error:
                            try:
                                driver.switch_to.default_content()
                            except Exception:
                                pass
                            print("CAPTCHA anchor is inaccessible; claim will not be submitted.")
                            print(
                                f"Popup: {self._frame_diagnostics(popup)}. "
                                f"Anchor: {anchor_diagnostics}. Error: {anchor_error}"
                            )
                            return "CAPTCHA_ANCHOR_INACCESSIBLE"
                        challenge_required = True
                    driver.switch_to.default_content()
                    if challenge_required:
                        break
                except Exception as e:
                    last_buster_diagnostics = f"anchor lookup error: {e}"
                    try:
                        driver.switch_to.default_content()
                    except Exception:
                        pass
                t.sleep(1)

            if not challenge_required:
                buster_clicked, last_buster_diagnostics = self._activate_buster(driver)
                if buster_clicked:
                    challenge_required = True
                    print("Buster activation requested before an anchor was found.")
                else:
                    print(f"No reCAPTCHA challenge detected ({last_buster_diagnostics}).")

            if invisible_challenge and not captcha_verified:
                submit_clicked = self._click_popup_submit(driver)
                if submit_clicked:
                    print("Reward submit clicked once to trigger invisible verification.")
                else:
                    print("No submit control available to trigger invisible verification.")

            if challenge_required and not captcha_verified:
                print("Waiting for captcha challenge to be solved without resetting it...")
                start_time = t.time()
                popup_closed_after_submit = False
                while t.time() - start_time < 120:
                    if self._visible_popup(driver) is None:
                        if submit_clicked:
                            popup_closed_after_submit = True
                            print("Reward popup closed after our submit; checking the page response...")
                            break
                        print("Reward popup closed before CAPTCHA verification completed.")
                        return "UNCONFIRMED"
                    anchor_state = self._anchor_state(driver)
                    if anchor_state is True:
                        captcha_verified = True
                        break
                    if invisible_challenge and self._recaptcha_token(driver):
                        captcha_verified = True
                        print("Invisible reCAPTCHA token observed.")
                        break
                    if invisible_challenge:
                        try:
                            driver.switch_to.default_content()
                            popup = self._visible_popup(driver)
                            observed = ""
                            if popup:
                                driver.switch_to.frame(popup)
                                observed = driver.find_element(By.TAG_NAME, "body").text
                            driver.switch_to.default_content()
                        except Exception:
                            observed = ""
                        quota_match = self._captcha_unavailable_match(observed)
                        if quota_match:
                            print(f"reCAPTCHA is unavailable during invisible verification. Matched text: {quota_match[:200]}")
                            return "CAPTCHA_UNAVAILABLE"
                        if self._is_daily_limit(observed):
                            print("Daily limit reached during invisible verification.")
                            return "DAILY_LIMIT"
                        if self._is_already_claimed(observed):
                            print("Reward was already claimed during invisible verification.")
                            return "ALREADY_CLAIMED"
                        if self._is_account_action_required(observed):
                            print("Account needs manual confirmation during invisible verification.")
                            return "ACCOUNT_ACTION_REQUIRED"
                        if (
                            self._is_reward_confirmation(observed)
                            and not self._is_reward_confirmation(initial_popup_text)
                            and self._normalized_text(observed)
                            != self._normalized_text(initial_popup_text)
                        ):
                            captcha_verified = True
                            response_observed = True
                            break
                    if not buster_clicked:
                        activated, diagnostics = self._activate_buster(driver)
                        last_buster_diagnostics = diagnostics
                        if activated:
                            buster_clicked = True
                            print(f"Buster activation requested ({diagnostics}).")
                    t.sleep(1.5)
                if not captcha_verified and not popup_closed_after_submit:
                    try:
                        driver.switch_to.default_content()
                    except Exception:
                        pass
                    print(
                        "Captcha was not verified; no claim button was clicked. "
                        f"Last Buster diagnostics: {last_buster_diagnostics}."
                    )
                    return "CAPTCHA_UNVERIFIED"

            if submit_clicked or response_observed:
                print("Reward submit was already clicked or a response appeared; checking the explicit response...")
            else:
                try:
                    driver.switch_to.default_content()
                except Exception:
                    pass
                popup = self._visible_popup(driver)
                if popup is None:
                    return "NO_POPUP"
                driver.switch_to.frame(popup)
                claim_btns = self._visible_enabled(
                    driver.find_elements(
                        By.XPATH,
                        self._REWARD_SUBMIT_XPATH,
                    )
                )
                if not claim_btns:
                    print("Reward popup did not contain an enabled submit button.")
                    return "NO_SUBMIT"
                claim_button = claim_btns[-1]
                clicked = False
                try:
                    driver.execute_script("arguments[0].click();", claim_button)
                    clicked = True
                except Exception:
                    try:
                        claim_button.click()
                        clicked = True
                    except Exception as e:
                        print(f"Could not click claim button: {e}")
                if not clicked:
                    return "NO_SUBMIT"
                submit_clicked = True
                print("Submit button clicked; waiting for an explicit reward response...")

            reward_confirmed = False
            confirmation_source = None
            for _ in range(10):
                t.sleep(1.2)
                try:
                    alert = driver.switch_to.alert
                    alert_text = alert.text
                    daily_match = self._daily_limit_match(alert_text)
                    if daily_match:
                        print(f"Daily limit reached according to alert. Matched text: {daily_match[:200]}")
                        alert.accept()
                        driver.switch_to.default_content()
                        return "DAILY_LIMIT"
                    if self._is_already_claimed(alert_text):
                        alert.accept()
                        driver.switch_to.default_content()
                        return "ALREADY_CLAIMED"
                    if self._is_reward_confirmation(alert_text):
                        reward_confirmed = True
                        confirmation_source = "alert"
                        rem = self._extract_remaining_quizzes(alert_text)
                        if rem is not None:
                            self.remaining_quizzes_today = rem
                            print(f"[Website Confirmation] You can take {rem} more quizzes to earn Crowns today!")
                        alert.accept()
                        break
                    alert.accept()
                except Exception:
                    pass

                try:
                    driver.switch_to.default_content()
                except Exception:
                    pass
                observed_text = ""
                popup = self._visible_popup(driver)
                if popup:
                    try:
                        driver.switch_to.frame(popup)
                        observed_text = driver.find_element(By.TAG_NAME, "body").text
                    except Exception:
                        observed_text = ""
                elif submit_clicked:
                    try:
                        observed_text = driver.find_element(By.TAG_NAME, "body").text
                    except Exception:
                        observed_text = ""

                quota_match = self._captcha_unavailable_match(observed_text)
                if quota_match:
                    try:
                        driver.switch_to.default_content()
                    except Exception:
                        pass
                    print(f"reCAPTCHA is unavailable in the reward response. Matched text: {quota_match[:200]}")
                    return "CAPTCHA_UNAVAILABLE"
                daily_match = self._daily_limit_match(observed_text)
                if daily_match:
                    try:
                        driver.switch_to.default_content()
                    except Exception:
                        pass
                    print(f"Daily limit reached according to the reward response. Matched text: {daily_match[:200]}")
                    return "DAILY_LIMIT"
                if self._is_already_claimed(observed_text):
                    try:
                        driver.switch_to.default_content()
                    except Exception:
                        pass
                    print("Reward response says the quiz was already claimed.")
                    return "ALREADY_CLAIMED"
                if self._is_account_action_required(observed_text):
                    try:
                        driver.switch_to.default_content()
                    except Exception:
                        pass
                    print("Reward response says the account needs manual confirmation before crowns can be issued.")
                    return "ACCOUNT_ACTION_REQUIRED"
                if (
                    self._is_reward_confirmation(observed_text)
                    and not self._is_reward_confirmation(initial_popup_text)
                    and self._normalized_text(observed_text)
                    != self._normalized_text(initial_popup_text)
                ):
                    reward_confirmed = True
                    confirmation_source = "reward popup" if popup else "page"
                    rem = self._extract_remaining_quizzes(observed_text)
                    if rem is not None:
                        self.remaining_quizzes_today = rem
                        print(f"[Website Confirmation] You can take {rem} more quizzes to earn Crowns today!")
                    break

            if reward_confirmed:
                return self._record_confirmed_reward(confirmation_source)
            if submit_clicked:
                print("Submit was clicked and the claim may have gone through; verify the crown balance.")
                return "SUBMITTED_UNCONFIRMED"
            print("Submit was clicked, but no explicit reward confirmation was found.")
            return "UNCONFIRMED"

        except Exception as e:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
            print(f"Quiz captcha step error: {e}")
            return "ERROR"

    def solveVerification(self, driver):
        t.sleep(2)
        popup = self._visible_popup(driver)
        if popup is None:
            return True

        print("Login verification popup detected!")
        verified = False
        try:
            try:
                driver.switch_to.frame(popup)
                login_popup_text = driver.find_element(By.TAG_NAME, "body").text
            except Exception:
                login_popup_text = ""
            driver.switch_to.default_content()
            quota_match = self._captcha_unavailable_match(login_popup_text)
            if quota_match:
                print(f"reCAPTCHA is unavailable during login verification. Matched text: {quota_match[:200]}")
                return False

            def wait_for_captcha():
                buster_clicked = False
                start_time = t.time()
                while t.time() - start_time < 120:
                    if self._anchor_state(driver) is True:
                        return True
                    if not buster_clicked:
                        activated, diagnostics = self._activate_buster(driver)
                        if activated:
                            buster_clicked = True
                            print(f"Login Buster activation requested ({diagnostics}).")
                    t.sleep(1.5)
                return False

            anchor_checked = self._click_anchor_once(driver)
            if anchor_checked is None:
                initial_deadline = t.time() + 10
                while t.time() < initial_deadline and not self._captcha_present(driver):
                    t.sleep(1)
                if self._captcha_present(driver):
                    anchor_checked = self._click_anchor_once(driver)

            if anchor_checked is True:
                verified = True
            elif anchor_checked is False:
                print("Waiting for login captcha challenge to be solved without resetting it...")
                if not wait_for_captcha():
                    print("Login captcha was not verified; no login button was clicked.")
                    return False
            else:
                activated, diagnostics = self._activate_buster(driver)
                if activated:
                    print(f"Login Buster activation requested ({diagnostics}).")
                    if not wait_for_captcha():
                        print("Login captcha was not verified; no login button was clicked.")
                        return False
                elif self._captcha_present(driver):
                    print(f"Login captcha is present but Buster could not be activated ({diagnostics}).")
                    return False
                else:
                    verified = True

            if not verified:
                return False
            driver.switch_to.default_content()
            popup = self._visible_popup(driver)
            if popup is None:
                return False
            driver.switch_to.frame(popup)
            login_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.ID, "bp_login"))
            )
            login_btn.click()
            driver.switch_to.default_content()
            t.sleep(4)
            print("Login verification completed.")
            return True
        except Exception as e:
            try:
                driver.switch_to.default_content()
            except Exception:
                pass
            print(f"Login verification failed: {e}")
            return False

    def clickCookies(self, driver):
        """Accepts cookies if the banner is present."""
        try:
            cookie_buttons = driver.find_elements(By.ID, "onetrust-accept-btn-handler")
            if cookie_buttons and cookie_buttons[0].is_displayed():
                cookie_buttons[0].click()
                t.sleep(1)
        except Exception:
            pass
