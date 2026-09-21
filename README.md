# Wizard101-Auto-Trivia

## STATUS UPDATE!!! (5/10/23)
**READ IF YOU WANT OR SCROLL BELOW TO VIEW PROJECT!** Hey, it's been 7 months and I'm finally updating this repository (school sure is busy). I've been updating this project slowly overtime and I think it's in a stable state now! It has recieved a massive overhaul from it's predecessor version. Sorry, for not reading DM's (I will look at them now) It should be a lot more useful now :)! I have some features in mind to add later on, feel free to give me some more ideas!
##

## Purpose
This is a Python program that will automatically answer Wizard101 trivia questions; it currently can solve all the Trivia that relate **specifically** to all Wizard101 and the Pirate101 Valencia quizes. It will earn up to 10 crowns per quiz solved, with a max of 100 crowns per day, per account!

## How does it Work/Features and Important Info
This Python program uses [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver) and the [Buster-extension](https://chrome.google.com/webstore/detail/buster-captcha-solver-for/mpbjkejclgfgadiemmefgebjfooflfhl) to stealthily navigate through the webpage and solve the captcha. Solving the captcha can take anywhere from 3 seconds to 5 minutes depending if chrome detects the bot or not. It is **HIGHLY** recommended that you use a vpn like [Planet-VPN](https://freevpnplanet.com/) (or any other really) to prevent a potential temp web IP ban form KI or chrome! The program will automatically refresh and continue if a page crashes or if a captcha was failed, and it records the total amount of crowns earned in the data.txt file in the text_files folder!

## Known 'Issues'
When a page crashes, the program should refresh and continue and if the program ever seems 'stuck' -- restart it (however, please note the program may take time to refresh and start back where it was). Additionally, when solving the captcha you may see a message pop up that says "your computer is sending automatic queries", you can ignore the message; it may take the bot several minutes to bypass chrome's detection. I plan to optimize the program and add some features if enough people use it.

## Quick Note!!!
There are some leftover modules and files from either scrapped ideas/features or no longer necessary files. You can obviously ignore these. I kept them incase I needed to revert something, or if I plan to add/finish a feature! 

> How do I use this?

* 1: Download [Python](https://www.python.org/) (Python 3.10+).
* 2: Set up a virtual environment and install requirements:
  - **macOS / Linux**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```
  - **Windows**:
    ```cmd
    python -m venv venv
    venv\Scripts\activate
    pip install -r requirements.txt
    ```
* 3: Go into the `text_files/` folder, copy `accounts.example.txt` to `accounts.txt`, and add your accounts (username then a space then a password, e.g. `Username Password`).
* 4: Make sure to run your VPN if you want to be cautious.
* 5: The Buster captcha solver extension is bundled in `extensions/buster` and will be loaded automatically into Chrome.
* 6: Run the "main.py" file, it will automatically open the browser, log in, solve the captcha, and loop through all 10 trivia quizzes.

> Will this automatically do all 10 quizes at once?

**Yes**. It will solve all of the questions automatically and move through each quiz, it's been made so you can "set-it-and-forget-it".

> How long does the program take to solve each question?

**5 seconds**. The program has to wait for each question to load, then it clicks the correct answer and goes to the next question.

> Can this program multi-thread?

**No**. Although, I did have a version that did that at one point I re-designed it to be single threaded because the website would get too many requests and ironically everything would be slower. Maybe in the future I will add an advance ip and proxy system, but for now it can only do one account at a time.

> Is this the same thing as the trivia extension that got people in trouble?

**No.** This program was made to seem human and uses stealthy modifications to avoid detection, you will be fine. However, if you're parnoid then only run this on alt accounts with a vpn.

## Credits
This project was made possible thanks to the following resources:
* [undetected-chromedriver](https://github.com/ultrafunkamsterdam/undetected-chromedriver)
* [Buster-extension](https://chrome.google.com/webstore/detail/buster-captcha-solver-for/mpbjkejclgfgadiemmefgebjfooflfhl)
* [Python](https://www.python.org/)
* [Planet-VPN](https://freevpnplanet.com/)

## Disclaimer
This project is intended for educational purposes only. The use of this program for cheating is not endorsed and is against the terms of service of Wizard101. The developer is not responsible for any consequences that may arise from the use of this program.

## License
This project is licensed under the MIT License - see the LICENSE.md file for details.

Thank you for checking out my project! Please feel free to contribute or leave feedback! I will take suggestions, message me on Discord (**Dizzy#9275**)
