# kik-moderation-bot
On python 3.11 I get error:
`can't register atexit after shutdown`
so just use python 3.8, which works fine.

`pyenv install 3.8.10`
cd into repo folder
`pyenv local 3.8.10`
This will create a `.python-version` file. Now if you're cd'ed into the repo, if you run `python3 --version`, you should see `Python 3.8.10`
`python3 -m venv venv`
`source venv/bin/activate`
Clone the library repo and checkout branch "new"
`git clone -b new https://github.com/tomer8007/kik-bot-api-unofficial`
`pip install ./kik-bot-api-unofficial`
`python main.py`
